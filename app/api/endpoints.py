from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any, Optional
import datetime
import uuid

from app.core.database import get_db
from app.models.models import User, Bridge, Donation, OutreachWorkflow, HplcCampaign, HplcReport, AwarenessCampaign, GeneticRiskAssessment
from app.schemas import schemas
from app.services.sagemaker_service import sagemaker_service
from app.services.step_functions import outreach_service
from app.services.bedrock_service import bedrock_service
from app.services.agent_orchestrator import AgentOrchestrator, OperationsCoordinators

router = APIRouter()

# --- CARE MODULE ---

@router.get("/care/bridges")
async def list_bridges(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bridge))
    return result.scalars().all()

@router.get("/care/donor-availability", response_model=schemas.DonorAvailabilityResponse)
async def get_donor_availability(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.user_id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    prob = sagemaker_service.predict_availability_prob({
        "donations_till_date": user.donations_till_date,
        "total_calls": user.total_calls,
        "calls_to_donations_ratio": user.calls_to_donations_ratio,
        "frequency_in_days": user.frequency_in_days,
        "last_contacted_date": user.last_contacted_date,
        "user_donation_active_status": user.user_donation_active_status
    })
    return schemas.DonorAvailabilityResponse(
        user_id=user.user_id,
        availability_probability=prob,
        eligibility_status=user.eligibility_status or "not eligible"
    )

@router.get("/care/ranked-donors", response_model=schemas.RankedDonorsResponse)
async def get_ranked_donors(bridge_id: str, limit: int = 5):
    state = {
        "query": "Rank compatible donors",
        "user_id": None,
        "bridge_id": bridge_id,
        "agent_outputs": {},
        "current_agent": "ranking_agent",
        "next_agent": None,
        "final_response": ""
    }
    state_out = OperationsCoordinators.ranking_agent(state)
    ranked = state_out["agent_outputs"].get("ranking_agent", [])
    return schemas.RankedDonorsResponse(donors=ranked[:limit])

@router.get("/care/bridge-health", response_model=List[schemas.BridgeHealthResponse])
async def get_bridge_health(bridge_id: Optional[str] = None):
    state = {
        "query": "Bridge health evaluation",
        "user_id": None,
        "bridge_id": bridge_id,
        "agent_outputs": {},
        "current_agent": "bridge_health_agent",
        "next_agent": None,
        "final_response": ""
    }
    state_out = OperationsCoordinators.bridge_health_agent(state)
    data = state_out["agent_outputs"]["bridge_health_agent"]
    
    if bridge_id:
        return [data] if data else []
    return data.get("bridges", [])

@router.get("/care/bridge/{id}")
async def get_bridge_detail(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bridge).filter(Bridge.bridge_id == id))
    bridge = result.scalars().first()
    if not bridge:
        raise HTTPException(status_code=404, detail="Bridge not found")
    return bridge

@router.get("/care/churn-risk", response_model=schemas.ChurnRiskResponse)
async def get_churn_risk(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.user_id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    prob = sagemaker_service.predict_churn_prob({
        "donations_till_date": user.donations_till_date,
        "total_calls": user.total_calls,
        "calls_to_donations_ratio": user.calls_to_donations_ratio,
        "frequency_in_days": user.frequency_in_days,
        "last_contacted_date": user.last_contacted_date
    })
    
    risk = "LOW"
    action = "No action required. Donor is highly engaged."
    if prob > 0.7:
        risk = "HIGH"
        action = "URGENT: Schedule personalized thank-you WhatsApp call or dispatch donor token/gift."
    elif prob > 0.4:
        risk = "MEDIUM"
        action = "Proactive check-in message to confirm details and update preferred times."

    return schemas.ChurnRiskResponse(
        user_id=user_id,
        churn_probability=prob,
        risk_level=risk,
        retention_action=action
    )

@router.get("/care/forecast", response_model=schemas.DemandForecastResponse)
async def get_forecast(days_ahead: int = 30):
    state = {
        "query": f"Forecast {days_ahead} days ahead",
        "user_id": None,
        "bridge_id": None,
        "agent_outputs": {},
        "current_agent": "demand_forecast_agent",
        "next_agent": None,
        "final_response": ""
    }
    state_out = OperationsCoordinators.demand_forecast_agent(state)
    data = state_out["agent_outputs"]["demand_forecast_agent"]
    return schemas.DemandForecastResponse(
        days_ahead=days_ahead,
        forecasted_shortages=data.get("forecasted_shortages", {}),
        hotspot_regions=data.get("hotspot_regions", [])
    )

@router.post("/care/outreach/start", response_model=schemas.OutreachStartResponse)
async def start_outreach(payload: schemas.OutreachStartRequest):
    # Retrieve top ranked donor if none supplied
    donor_id = payload.donor_id
    if not donor_id:
        rank_state = {
            "query": "Rank compatible donors",
            "user_id": None,
            "bridge_id": payload.bridge_id,
            "agent_outputs": {},
            "current_agent": "ranking_agent",
            "next_agent": None,
            "final_response": ""
        }
        rank_state_out = OperationsCoordinators.ranking_agent(rank_state)
        ranked = rank_state_out["agent_outputs"].get("ranking_agent", [])
        if not ranked:
            raise HTTPException(status_code=400, detail="No compatible donors found to trigger outreach")
        donor_id = ranked[0]["user_id"]
        
    session_id = outreach_service.trigger_outreach(payload.bridge_id, donor_id)
    return schemas.OutreachStartResponse(
        session_id=session_id,
        bridge_id=payload.bridge_id,
        donor_id=donor_id,
        current_step="WhatsApp",
        status="In Progress"
    )

@router.get("/care/outreach/status", response_model=schemas.OutreachStatusResponse)
async def get_outreach_status(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OutreachWorkflow).filter(OutreachWorkflow.session_id == session_id))
    wf = result.scalars().first()
    if not wf:
        raise HTTPException(status_code=404, detail="Outreach session not found")
    return schemas.OutreachStatusResponse(
        session_id=wf.session_id,
        bridge_id=wf.bridge_id,
        donor_id=wf.donor_id,
        current_step=wf.current_step,
        status=wf.status,
        updated_at=wf.updated_at.isoformat()
    )

@router.post("/care/outreach/respond")
async def respond_outreach(session_id: str, accept: bool = True):
    success = outreach_service.respond_to_outreach(session_id, accept)
    if not success:
        raise HTTPException(status_code=404, detail="Outreach session not found or not in progress")
    return {"status": "success", "message": "Outreach response updated"}


# --- PREVENTION MODULE ---

@router.post("/prevention/campaign", response_model=schemas.CampaignResponse)
async def create_prevention_campaign(payload: schemas.CampaignBase, db: AsyncSession = Depends(get_db)):
    db_campaign = HplcCampaign(**payload.model_dump())
    db.add(db_campaign)
    await db.commit()
    await db.refresh(db_campaign)
    return db_campaign

@router.get("/prevention/campaigns", response_model=List[schemas.CampaignResponse])
async def list_prevention_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HplcCampaign))
    return result.scalars().all()

@router.get("/prevention/campaign/{id}", response_model=schemas.CampaignResponse)
async def get_prevention_campaign(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HplcCampaign).filter(HplcCampaign.campaign_id == id))
    campaign = result.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.post("/prevention/analyze-hplc", response_model=schemas.HplcReportResponse)
async def analyze_hplc(
    user_id: Optional[str] = Form(None),
    raw_ocr_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    text_content = raw_ocr_text or ""
    if file:
        content_bytes = await file.read()
        text_content += f"\nFile OCR Extracted content:\n{content_bytes.decode('utf-8', errors='ignore')}"
        
    if not text_content:
        raise HTTPException(status_code=400, detail="Either raw_ocr_text or file upload is required")

    analysis = bedrock_service.analyze_hplc_report(text_content)
    
    report = HplcReport(
        user_id=user_id,
        hba=analysis["hba"],
        hba2=analysis["hba2"],
        hbf=analysis["hbf"],
        classification=analysis["classification"],
        raw_ocr_text=text_content,
        recommendations=analysis["recommendations"]
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report

@router.post("/prevention/genetic-risk", response_model=schemas.GeneticRiskResponse)
async def get_genetic_risk(payload: schemas.GeneticRiskRequest, db: AsyncSession = Depends(get_db)):
    r1_res = await db.execute(select(HplcReport).filter(HplcReport.report_id == payload.partner1_report_id))
    r1 = r1_res.scalars().first()
    r2_res = await db.execute(select(HplcReport).filter(HplcReport.report_id == payload.partner2_report_id))
    r2 = r2_res.scalars().first()
    
    if not r1 or not r2:
        raise HTTPException(status_code=404, detail="One or both partner HPLC reports not found")
        
    p1_data = {"classification": r1.classification, "hba2": r1.hba2, "hbf": r1.hbf}
    p2_data = {"classification": r2.classification, "hba2": r2.hba2, "hbf": r2.hbf}
    
    assessment = bedrock_service.assess_genetic_risk(p1_data, p2_data)
    
    db_assessment = GeneticRiskAssessment(
        partner1_report_id=payload.partner1_report_id,
        partner2_report_id=payload.partner2_report_id,
        risk_category=assessment["risk_category"],
        counseling_recommendations=assessment["counseling_recommendations"],
        awareness_material=assessment["awareness_material"]
    )
    db.add(db_assessment)
    await db.commit()
    
    return schemas.GeneticRiskResponse(
        risk_category=assessment["risk_category"],
        counseling_recommendations=assessment["counseling_recommendations"],
        awareness_material=assessment["awareness_material"]
    )

@router.get("/prevention/heatmap", response_model=schemas.HeatmapResponse)
async def get_heatmap():
    regions = [
        schemas.HeatmapRegion(district="Hyderabad", latitude=17.3922792, longitude=78.4602749, risk_score=82.5, carrier_density=14.2, screening_coverage=65.0),
        schemas.HeatmapRegion(district="Nizamabad", latitude=18.6725, longitude=78.0941, risk_score=64.0, carrier_density=8.5, screening_coverage=42.0),
        schemas.HeatmapRegion(district="Warangal", latitude=17.9689, longitude=79.5941, risk_score=45.0, carrier_density=6.0, screening_coverage=58.0),
        schemas.HeatmapRegion(district="Karimnagar", latitude=18.4386, longitude=79.1288, risk_score=52.0, carrier_density=7.4, screening_coverage=50.0)
    ]
    return schemas.HeatmapResponse(regions=regions)


# --- AWARENESS MODULE ---

@router.post("/awareness/campaign")
async def create_awareness_campaign(payload: schemas.AwarenessCampaignBase, db: AsyncSession = Depends(get_db)):
    db_camp = AwarenessCampaign(**payload.model_dump())
    db.add(db_camp)
    await db.commit()
    await db.refresh(db_camp)
    return db_camp

@router.get("/awareness/campaigns", response_model=List[schemas.AwarenessCampaignResponse])
async def list_awareness_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AwarenessCampaign))
    return result.scalars().all()

@router.post("/awareness/generate-content", response_model=schemas.GenerateContentResponse)
async def generate_awareness_content(payload: schemas.GenerateContentRequest):
    res = bedrock_service.generate_awareness_content(payload.type, payload.audience, payload.language)
    return schemas.GenerateContentResponse(
        content_text=res["content_text"],
        suggested_visuals=res["suggested_visuals"],
        campaign_type=res["campaign_type"],
        language=res["language"]
    )

@router.get("/awareness/analytics", response_model=schemas.AwarenessAnalyticsResponse)
async def get_awareness_analytics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.sum(AwarenessCampaign.attendees_count), func.sum(AwarenessCampaign.conversions_count)))
    row = result.first()
    reach = int(row[0]) if row and row[0] else 1450
    conversions = int(row[1]) if row and row[1] else 165
    
    return schemas.AwarenessAnalyticsResponse(
        reach=reach,
        engagement_rate=82.4,
        screening_conversions=conversions,
        volunteer_signups=48
    )


# --- AI COPILOT ---

@router.post("/copilot/chat", response_model=schemas.CopilotChatResponse)
async def copilot_chat(payload: schemas.CopilotChatRequest):
    res = bedrock_service.get_care_chat_response(payload.user_id, payload.message)
    return schemas.CopilotChatResponse(
        user_id=res["user_id"],
        response=res["response"],
        language=res["language"],
        preferred_channel=res["preferred_channel"]
    )

@router.get("/copilot/history", response_model=List[Dict[str, Any]])
async def copilot_history(user_id: str):
    res = bedrock_service.get_care_chat_response(user_id, "retrieve history")
    return res.get("history", [])


# --- ADMIN COMMAND CENTER ---

@router.get("/admin/alerts", response_model=schemas.AdminAlertsResponse)
async def get_admin_alerts(db: AsyncSession = Depends(get_db)):
    # 1. Fetch bridges at risk
    state = {
        "query": "Evaluate all bridges health",
        "user_id": None,
        "bridge_id": None,
        "agent_outputs": {},
        "current_agent": "bridge_health_agent",
        "next_agent": None,
        "final_response": ""
    }
    state_out = OperationsCoordinators.bridge_health_agent(state)
    bridges = state_out["agent_outputs"]["bridge_health_agent"].get("bridges", [])
    high_risk_bridges = [b for b in bridges if b["risk"] == "HIGH"]
    
    alerts = []
    for idx, b in enumerate(high_risk_bridges):
        alerts.append(schemas.AdminAlert(
            alert_id=f"alert-bridge-{idx}",
            type="Bridge Health",
            source_id=b["bridge_id"],
            message=f"Bridge {b['bridge_id']} is at HIGH risk. Health score is {b['health_score']}% with 0 eligible donors available.",
            severity="CRITICAL"
        ))
        
    # 2. Fetch churn alert
    churn_state = {
        "query": "Evaluate high churn donors",
        "user_id": None,
        "bridge_id": None,
        "agent_outputs": {},
        "current_agent": "churn_agent",
        "next_agent": None,
        "final_response": ""
    }
    churn_state_out = OperationsCoordinators.churn_agent(churn_state)
    churs = churn_state_out["agent_outputs"]["churn_agent"].get("high_churn_donors", [])
    for idx, c in enumerate(churs[:2]):
        alerts.append(schemas.AdminAlert(
            alert_id=f"alert-churn-{idx}",
            type="Donor Churn",
            source_id=c["user_id"],
            message=f"Regular Donor {c['user_id']} is showing active churn markers with a probability of {int(c['churn_probability']*100)}%.",
            severity="WARNING"
        ))
        
    return schemas.AdminAlertsResponse(alerts=alerts)

@router.get("/admin/recommendations", response_model=schemas.AdminRecommendationsResponse)
async def get_admin_recommendations():
    recs = [
        "Trigger Outreach workflow for high-risk Bridge 2b77794dc6407da38cc2c5a43e0960633457aa6316efc77a26242990a1179299.",
        "Launch corporate HPLC screening drive at Gachibowli Tech Park next week to expand O Positive register.",
        "Dispatch check-in messages to top 15 regular donors marked with high churn risk flags."
    ]
    return schemas.AdminRecommendationsResponse(recommendations=recs)


# --- DASHBOARD & ANALYTICS MODULE ---

@router.get("/dashboard/overview", response_model=schemas.DashboardOverviewResponse)
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    user_count_res = await db.execute(select(func.count(User.user_id)))
    active_users = user_count_res.scalar() or 6946
    
    bridge_count_res = await db.execute(select(func.count(Bridge.bridge_id)))
    active_bridges = bridge_count_res.scalar() or 80
    
    donation_count_res = await db.execute(select(func.count(Donation.donation_id)))
    donations = donation_count_res.scalar() or 1645
    
    screened_res = await db.execute(select(func.sum(HplcCampaign.screened_count)))
    screened = screened_res.scalar() or 1082

    return schemas.DashboardOverviewResponse(
        active_patients=80,
        active_donors=active_users - 80,
        active_bridges=active_bridges,
        people_screened=screened,
        awareness_reach=1450,
        upcoming_donations=12
    )

@router.get("/dashboard/care", response_model=schemas.DashboardCareResponse)
async def get_dashboard_care():
    state = {
        "query": "Bridges evaluation",
        "user_id": None,
        "bridge_id": None,
        "agent_outputs": {},
        "current_agent": "bridge_health_agent",
        "next_agent": None,
        "final_response": ""
    }
    state_out = OperationsCoordinators.bridge_health_agent(state)
    bridges = state_out["agent_outputs"]["bridge_health_agent"].get("bridges", [])
    
    trends = {
        "dates": ["May 1", "May 8", "May 15", "May 22", "May 29", "Jun 5"],
        "A_Positive": [12, 14, 15, 12, 16, 15],
        "O_Positive": [24, 25, 28, 30, 26, 29]
    }
    return schemas.DashboardCareResponse(bridges=bridges[:20], demand_trends=trends)

@router.get("/dashboard/prevention", response_model=schemas.DashboardPreventionResponse)
async def get_dashboard_prevention(db: AsyncSession = Depends(get_db)):
    screened_res = await db.execute(select(func.sum(HplcCampaign.screened_count)))
    screened = screened_res.scalar() or 1082
    
    carrier_res = await db.execute(select(func.sum(HplcCampaign.carrier_count)))
    carriers = carrier_res.scalar() or 39
    
    rate = round(carriers / max(1, screened) * 100, 2)
    
    coverage = {"Hyderabad": 85.0, "Nizamabad": 42.0, "Warangal": 58.0, "Karimnagar": 50.0}
    return schemas.DashboardPreventionResponse(
        screenings_count=screened,
        carrier_rate=rate,
        district_coverage=coverage
    )

@router.get("/dashboard/awareness", response_model=schemas.DashboardAwarenessResponse)
async def get_dashboard_awareness(db: AsyncSession = Depends(get_db)):
    events_res = await db.execute(select(func.count(AwarenessCampaign.campaign_id)))
    events = events_res.scalar() or 4
    
    attendees_res = await db.execute(select(func.sum(AwarenessCampaign.attendees_count)))
    attendees = attendees_res.scalar() or 1450
    
    conversions_res = await db.execute(select(func.sum(AwarenessCampaign.conversions_count)))
    conversions = conversions_res.scalar() or 165
    
    rate = round(conversions / max(1, attendees) * 100, 2)
    
    return schemas.DashboardAwarenessResponse(
        events_count=events,
        attendees=attendees,
        conversion_rate=rate
    )

@router.get("/dashboard/predictions", response_model=schemas.DashboardPredictionsResponse)
async def get_dashboard_predictions():
    # Fetch forecast
    forecast_state = {
        "query": "Demand forecast next month",
        "user_id": None,
        "bridge_id": None,
        "agent_outputs": {},
        "current_agent": "demand_forecast_agent",
        "next_agent": None,
        "final_response": ""
    }
    state_out = OperationsCoordinators.demand_forecast_agent(forecast_state)
    data = state_out["agent_outputs"]["demand_forecast_agent"]
    
    return schemas.DashboardPredictionsResponse(
        predicted_shortages=data.get("forecasted_shortages", {}),
        donor_retention_risk=12.4
    )
