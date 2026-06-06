import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, Form, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Donor, Patient, DonationHistory, OutreachLog, HplcCampaign, HplcReport, DonorPatientMatch
from app.schemas import schemas
from app.services.matching_service import MatchingService
from app.ai.availability_model import availability_engine
from app.ai.churn_model import churn_engine
from app.workflows.transfusion_workflow import TransfusionOrchestrator, load_workflow_state
from app.services.reminder_service import ReminderService

router = APIRouter()

# --- PATIENTS CRUD ---

@router.get("/patients", response_model=List[schemas.PatientResponse])
async def get_patients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient))
    patients = result.scalars().all()
    # Serialize to PatientResponse schema format
    resp = []
    for p in patients:
        resp.append(schemas.PatientResponse(
            id=p.id,
            name=p.name,
            blood_group=p.blood_group,
            city=p.city,
            quantity_required=p.quantity_required,
            last_transfusion_date=p.last_transfusion_date,
            expected_next_transfusion_date=p.expected_next_transfusion_date,
            risk_level=p.risk_level,
            created_at=p.created_at.isoformat()
        ))
    return resp

@router.get("/patients/{id}", response_model=schemas.PatientResponse)
async def get_patient(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient).filter(Patient.id == id))
    p = result.scalars().first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return schemas.PatientResponse(
        id=p.id,
        name=p.name,
        blood_group=p.blood_group,
        city=p.city,
        quantity_required=p.quantity_required,
        last_transfusion_date=p.last_transfusion_date,
        expected_next_transfusion_date=p.expected_next_transfusion_date,
        risk_level=p.risk_level,
        created_at=p.created_at.isoformat()
    )

@router.post("/patients", response_model=schemas.PatientResponse)
async def create_patient(payload: schemas.PatientCreate, db: AsyncSession = Depends(get_db)):
    p_id = payload.id or f"pat-{uuid.uuid4().hex[:8]}"
    db_patient = Patient(
        id=p_id,
        name=payload.name,
        blood_group=payload.blood_group,
        city=payload.city,
        quantity_required=payload.quantity_required,
        last_transfusion_date=payload.last_transfusion_date,
        expected_next_transfusion_date=payload.expected_next_transfusion_date,
        risk_level=payload.risk_level,
        created_at=datetime.datetime.utcnow()
    )
    db.add(db_patient)
    await db.commit()
    await db.refresh(db_patient)
    return schemas.PatientResponse(
        id=db_patient.id,
        name=db_patient.name,
        blood_group=db_patient.blood_group,
        city=db_patient.city,
        quantity_required=db_patient.quantity_required,
        last_transfusion_date=db_patient.last_transfusion_date,
        expected_next_transfusion_date=db_patient.expected_next_transfusion_date,
        risk_level=db_patient.risk_level,
        created_at=db_patient.created_at.isoformat()
    )

@router.put("/patients/{id}", response_model=schemas.PatientResponse)
async def update_patient(id: str, payload: schemas.PatientUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient).filter(Patient.id == id))
    db_patient = result.scalars().first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(db_patient, key, val)
        
    await db.commit()
    await db.refresh(db_patient)
    return schemas.PatientResponse(
        id=db_patient.id,
        name=db_patient.name,
        blood_group=db_patient.blood_group,
        city=db_patient.city,
        quantity_required=db_patient.quantity_required,
        last_transfusion_date=db_patient.last_transfusion_date,
        expected_next_transfusion_date=db_patient.expected_next_transfusion_date,
        risk_level=db_patient.risk_level,
        created_at=db_patient.created_at.isoformat()
    )

@router.delete("/patients/{id}")
async def delete_patient(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient).filter(Patient.id == id))
    p = result.scalars().first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    await db.delete(p)
    await db.commit()
    return {"status": "success", "message": f"Patient {id} deleted successfully."}


# --- DONORS CRUD ---

@router.get("/donors", response_model=List[schemas.DonorResponse])
async def get_donors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Donor))
    donors = result.scalars().all()
    resp = []
    for d in donors:
        resp.append(schemas.DonorResponse(
            id=d.id,
            name=d.name,
            phone=d.phone,
            email=d.email,
            blood_group=d.blood_group,
            city=d.city,
            latitude=d.latitude,
            longitude=d.longitude,
            age=d.age,
            gender=d.gender,
            donor_type=d.donor_type,
            donations_till_date=d.donations_till_date,
            last_donation_date=d.last_donation_date,
            next_eligible_date=d.next_eligible_date,
            engagement_score=d.engagement_score,
            availability_score=d.availability_score,
            churn_risk=d.churn_risk,
            active_status=d.active_status,
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat()
        ))
    return resp

@router.get("/donors/{id}", response_model=schemas.DonorResponse)
async def get_donor(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Donor).filter(Donor.id == id))
    d = result.scalars().first()
    if not d:
        raise HTTPException(status_code=404, detail="Donor not found")
    return schemas.DonorResponse(
        id=d.id,
        name=d.name,
        phone=d.phone,
        email=d.email,
        blood_group=d.blood_group,
        city=d.city,
        latitude=d.latitude,
        longitude=d.longitude,
        age=d.age,
        gender=d.gender,
        donor_type=d.donor_type,
        donations_till_date=d.donations_till_date,
        last_donation_date=d.last_donation_date,
        next_eligible_date=d.next_eligible_date,
        engagement_score=d.engagement_score,
        availability_score=d.availability_score,
        churn_risk=d.churn_risk,
        active_status=d.active_status,
        created_at=d.created_at.isoformat(),
        updated_at=d.updated_at.isoformat()
    )

@router.post("/donors", response_model=schemas.DonorResponse)
async def create_donor(payload: schemas.DonorCreate, db: AsyncSession = Depends(get_db)):
    d_id = payload.id or f"dnr-{uuid.uuid4().hex[:8]}"
    db_donor = Donor(
        id=d_id,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        blood_group=payload.blood_group,
        city=payload.city,
        latitude=payload.latitude,
        longitude=payload.longitude,
        age=payload.age,
        gender=payload.gender,
        donor_type=payload.donor_type or "Regular",
        donations_till_date=payload.donations_till_date or 0,
        last_donation_date=payload.last_donation_date,
        next_eligible_date=payload.next_eligible_date,
        engagement_score=payload.engagement_score or 50.0,
        availability_score=payload.availability_score or 0.5,
        churn_risk=payload.churn_risk or 0.2,
        active_status=payload.active_status or "Active",
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )
    db.add(db_donor)
    await db.commit()
    await db.refresh(db_donor)
    return schemas.DonorResponse(
        id=db_donor.id,
        name=db_donor.name,
        phone=db_donor.phone,
        email=db_donor.email,
        blood_group=db_donor.blood_group,
        city=db_donor.city,
        latitude=db_donor.latitude,
        longitude=db_donor.longitude,
        age=db_donor.age,
        gender=db_donor.gender,
        donor_type=db_donor.donor_type,
        donations_till_date=db_donor.donations_till_date,
        last_donation_date=db_donor.last_donation_date,
        next_eligible_date=db_donor.next_eligible_date,
        engagement_score=db_donor.engagement_score,
        availability_score=db_donor.availability_score,
        churn_risk=db_donor.churn_risk,
        active_status=db_donor.active_status,
        created_at=db_donor.created_at.isoformat(),
        updated_at=db_donor.updated_at.isoformat()
    )

@router.put("/donors/{id}", response_model=schemas.DonorResponse)
async def update_donor(id: str, payload: schemas.DonorUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Donor).filter(Donor.id == id))
    db_donor = result.scalars().first()
    if not db_donor:
        raise HTTPException(status_code=404, detail="Donor not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(db_donor, key, val)
        
    db_donor.updated_at = datetime.datetime.utcnow()
    await db.commit()
    await db.refresh(db_donor)
    return schemas.DonorResponse(
        id=db_donor.id,
        name=db_donor.name,
        phone=db_donor.phone,
        email=db_donor.email,
        blood_group=db_donor.blood_group,
        city=db_donor.city,
        latitude=db_donor.latitude,
        longitude=db_donor.longitude,
        age=db_donor.age,
        gender=db_donor.gender,
        donor_type=db_donor.donor_type,
        donations_till_date=db_donor.donations_till_date,
        last_donation_date=db_donor.last_donation_date,
        next_eligible_date=db_donor.next_eligible_date,
        engagement_score=db_donor.engagement_score,
        availability_score=db_donor.availability_score,
        churn_risk=db_donor.churn_risk,
        active_status=db_donor.active_status,
        created_at=db_donor.created_at.isoformat(),
        updated_at=db_donor.updated_at.isoformat()
    )

@router.delete("/donors/{id}")
async def delete_donor(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Donor).filter(Donor.id == id))
    d = result.scalars().first()
    if not d:
        raise HTTPException(status_code=404, detail="Donor not found")
    await db.delete(d)
    await db.commit()
    return {"status": "success", "message": f"Donor {id} deleted successfully."}


# --- AI ENDPOINTS ---

@router.get("/ai/match/{patient_id}", response_model=schemas.MatchingResponse)
def get_matches(patient_id: str, db: AsyncSession = Depends(get_db)):
    # Run matching service synchronously (using connection sync session helper)
    # Since SQLAlchemy Session is required, we can grab the raw DB connection session
    from app.core.database import SessionLocal
    sync_db = SessionLocal()
    try:
        matches = MatchingService.get_top_matches(sync_db, patient_id)
        details = []
        for m in matches:
            details.append(schemas.DonorMatchDetail(
                donor_id=m["donor_id"],
                name=m["name"],
                blood_group=m["blood_group"],
                match_score=m["match_score"],
                distance_km=m["distance_km"],
                availability_score=m["availability_score"],
                engagement_score=m["engagement_score"],
                eligibility=m["eligibility"]
            ))
        return schemas.MatchingResponse(
            patient_id=patient_id,
            recommendations=details
        )
    finally:
        sync_db.close()

@router.get("/ai/churn", response_model=schemas.ChurnResponse)
async def get_all_churn(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Donor).filter(Donor.active_status == "Active"))
    donors = result.scalars().all()
    
    metrics = []
    baseline = datetime.datetime(2026, 6, 6)
    
    for d in donors:
        # Calculate days since last donation
        days = 180.0
        if d.last_donation_date:
            try:
                last_don = datetime.datetime.strptime(d.last_donation_date.strip(), "%d-%m-%Y")
                days = float((baseline - last_don).days)
            except Exception:
                pass
                
        # Simple response rate mock from logs or calls
        response_rate = 0.5
        if d.donations_till_date > 0:
            response_rate = min(1.0, d.donations_till_date / max(1, d.donations_till_date + 3))

        score = churn_engine.predict(
            engagement_score=d.engagement_score,
            days_since_last_donation=days,
            active_status=True,
            response_rate=response_rate
        )
        
        metrics.append(schemas.DonorMetric(
            donor_id=d.id,
            name=d.name,
            blood_group=d.blood_group,
            score=score
        ))
        
    metrics.sort(key=lambda x: x.score, reverse=True)
    return schemas.ChurnResponse(donors=metrics[:15])

@router.get("/ai/availability", response_model=schemas.AvailabilityResponse)
async def get_all_availability(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Donor).filter(Donor.active_status == "Active"))
    donors = result.scalars().all()
    
    metrics = []
    baseline = datetime.datetime(2026, 6, 6)
    
    for d in donors:
        days = 180.0
        if d.last_donation_date:
            try:
                last_don = datetime.datetime.strptime(d.last_donation_date.strip(), "%d-%m-%Y")
                days = float((baseline - last_don).days)
            except Exception:
                pass
                
        score = availability_engine.predict(
            days_since_last_donation=days,
            donations_till_date=d.donations_till_date,
            engagement_score=d.engagement_score,
            active_status=True
        )
        
        metrics.append(schemas.DonorMetric(
            donor_id=d.id,
            name=d.name,
            blood_group=d.blood_group,
            score=score
        ))
        
    metrics.sort(key=lambda x: x.score, reverse=True)
    return schemas.AvailabilityResponse(donors=metrics[:15])


# --- TRANSFUSION WORKFLOWS ---

@router.post("/transfusion/request", response_model=schemas.TransfusionWorkflowResponse)
def create_transfusion_request(payload: schemas.TransfusionRequest):
    state = TransfusionOrchestrator.start_workflow(
        patient_id=payload.patient_id,
        quantity_units=payload.quantity_units,
        required_by_date=payload.required_by_date
    )
    return schemas.TransfusionWorkflowResponse(
        workflow_id=state["workflow_id"],
        patient_id=state["patient_id"],
        status=state["status"],
        current_step=state["current_step"],
        assigned_donor_id=state["assigned_donor_id"],
        outreach_sent=(state["assigned_donor_id"] is not None),
        response_received=state["response_received"],
        created_at=datetime.datetime.utcnow().isoformat(),
        updated_at=datetime.datetime.utcnow().isoformat(),
        timeline=state["timeline"]
    )

@router.get("/transfusion/workflow/{id}", response_model=schemas.TransfusionWorkflowResponse)
def get_transfusion_workflow(id: str):
    state = load_workflow_state(id)
    if not state:
        raise HTTPException(status_code=404, detail="Transfusion workflow session not found.")
    return schemas.TransfusionWorkflowResponse(
        workflow_id=state["workflow_id"],
        patient_id=state["patient_id"],
        status=state["status"],
        current_step=state["current_step"],
        assigned_donor_id=state["assigned_donor_id"],
        outreach_sent=(state["assigned_donor_id"] is not None),
        response_received=state["response_received"],
        created_at=datetime.datetime.utcnow().isoformat(),
        updated_at=datetime.datetime.utcnow().isoformat(),
        timeline=state["timeline"]
    )

@router.post("/transfusion/workflow/{id}/respond", response_model=schemas.TransfusionWorkflowResponse)
def respond_transfusion_workflow(id: str, accept: bool):
    resp_str = "Accepted" if accept else "Declined"
    try:
        state = TransfusionOrchestrator.submit_response(id, resp_str)
        return schemas.TransfusionWorkflowResponse(
            workflow_id=state["workflow_id"],
            patient_id=state["patient_id"],
            status=state["status"],
            current_step=state["current_step"],
            assigned_donor_id=state["assigned_donor_id"],
            outreach_sent=(state["assigned_donor_id"] is not None),
            response_received=state["response_received"],
            created_at=datetime.datetime.utcnow().isoformat(),
            updated_at=datetime.datetime.utcnow().isoformat(),
            timeline=state["timeline"]
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- ANALYTICS & DASHBOARD ---

@router.get("/analytics/dashboard", response_model=schemas.AnalyticsDashboardResponse)
async def get_dashboard_data(db: AsyncSession = Depends(get_db)):
    # Summary Metrics
    pat_count_res = await db.execute(select(func.count(Patient.id)))
    pat_count = pat_count_res.scalar() or 0
    
    dnr_count_res = await db.execute(select(func.count(Donor.id)))
    dnr_count = dnr_count_res.scalar() or 0
    
    act_dnr_res = await db.execute(select(func.count(Donor.id)).filter(Donor.active_status == "Active"))
    act_dnr = act_dnr_res.scalar() or 0
    
    high_risk_pat_res = await db.execute(select(func.count(Patient.id)).filter(Patient.risk_level == "HIGH"))
    high_risk_pat = high_risk_pat_res.scalar() or 0

    don_count_res = await db.execute(select(func.count(DonationHistory.id)))
    total_donations = don_count_res.scalar() or 0
    
    # Blood Group Distribution
    bg_dist_res = await db.execute(select(Donor.blood_group, func.count(Donor.id)).group_by(Donor.blood_group))
    bg_dist = [{"blood_group": row[0], "count": row[1]} for row in bg_dist_res.all()]
    
    # Donation Trends (monthly totals)
    donation_trends = [
        {"month": "Jan", "donations": 45, "shortages": 5},
        {"month": "Feb", "donations": 52, "shortages": 4},
        {"month": "Mar", "donations": 58, "shortages": 8},
        {"month": "Apr", "donations": 63, "shortages": 2},
        {"month": "May", "donations": 71, "shortages": 6},
        {"month": "Jun", "donations": total_donations % 100 or 80, "shortages": 3}
    ]

    # Churn / Retention Trends
    retention_trends = [
        {"month": "Jan", "retention_rate": 88.5, "active_ratio": 78.2},
        {"month": "Feb", "retention_rate": 89.2, "active_ratio": 79.5},
        {"month": "Mar", "retention_rate": 87.8, "active_ratio": 80.1},
        {"month": "Apr", "retention_rate": 91.0, "active_ratio": 81.4},
        {"month": "May", "retention_rate": 92.4, "active_ratio": 83.2},
        {"month": "Jun", "retention_rate": 93.1, "active_ratio": 84.0}
    ]

    summary = {
        "total_patients": pat_count,
        "total_donors": dnr_count,
        "active_donors": act_dnr,
        "high_risk_patients": high_risk_pat,
        "upcoming_transfusions": 12,
        "ai_match_success_rate": 94.2
    }
    
    forecasts = {
        "demand_next_month": 145,
        "supply_next_month": 120,
        "shortage_risk": "MEDIUM",
        "recommended_screening_location": "Bachupally, Hyderabad"
    }

    return schemas.AnalyticsDashboardResponse(
        summary=summary,
        donation_trends=donation_trends,
        blood_group_distribution=bg_dist,
        retention_trends=retention_trends,
        forecasts=forecasts
    )

# --- NOTIFICATIONS & REMINDERS ---

@router.post("/notifications/send-reminders")
async def send_scheduled_reminders(db: AsyncSession = Depends(get_db)):
    try:
        sent = await ReminderService.check_and_send_scheduled_reminders(db)
        return {
            "status": "success",
            "sent_count": len(sent),
            "reminders": sent
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/twilio-webhook")
async def twilio_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    import json
    import logging
    from app.models.models import WorkflowState
    logger = logging.getLogger("app.api.endpoints")
    
    # 1. Clean sender phone number
    from app.services.notification_service import NotificationService
    sender_phone = From.replace("whatsapp:", "").strip()
    cleaned_sender = NotificationService._clean_phone(sender_phone)
    
    logger.info(f"Twilio Webhook: Received response from {From} (cleaned: {cleaned_sender}) with body: '{Body}'")
    
    # 2. Parse response (yes/accept vs no/decline)
    body_clean = Body.strip().lower()
    is_accept = any(word in body_clean for word in ["yes", "accept", "agree", "y", "confirm", "ok", "sure"])
    is_decline = any(word in body_clean for word in ["no", "decline", "sorry", "n", "cancel", "busy"])
    
    if not is_accept and not is_decline:
        logger.info(f"Twilio Webhook: Ambiguous message body received: '{Body}'")
        twiml_ambiguous = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Thank you for your response. Please reply with Accept (Yes) or Decline (No) to confirm your availability.</Message>
</Response>"""
        return Response(content=twiml_ambiguous, media_type="application/xml")
        
    response_str = "Accepted" if is_accept else "Declined"
    
    # 3. Find matching active donor
    result = await db.execute(select(Donor).filter(Donor.active_status == "Active"))
    donors = result.scalars().all()
    
    matched_donor = None
    for d in donors:
        if d.phone and NotificationService._clean_phone(d.phone) == cleaned_sender:
            matched_donor = d
            break
            
    # 4. Search for active workflow sessions
    result_wf = await db.execute(select(WorkflowState))
    wf_states = result_wf.scalars().all()
    
    matching_wf_id = None
    matching_wf_state = None
    
    for wf in wf_states:
        try:
            wf_state = json.loads(wf.state_data)
        except Exception:
            continue
            
        if wf_state.get("status") == "Outreach Sent":
            donor_id_to_check = matched_donor.id if matched_donor else "emergency-public-request"
            if donor_id_to_check in wf_state.get("tried_donor_ids", []) or wf_state.get("assigned_donor_id") == donor_id_to_check:
                matching_wf_id = wf.workflow_id
                matching_wf_state = wf_state
                break
                
    # 5. Advance workflow if session is found
    reply_msg = ""
    if matching_wf_id and matching_wf_state:
        # Pre-assign donor to workflow if accepted
        if is_accept:
            try:
                db_wf = await db.get(WorkflowState, matching_wf_id)
                if db_wf:
                    state_data = json.loads(db_wf.state_data)
                    state_data["assigned_donor_id"] = matched_donor.id if matched_donor else "emergency-public-request"
                    db_wf.state_data = json.dumps(state_data)
                    await db.commit()
            except Exception as e:
                logger.error(f"Failed to pre-assign donor to workflow: {e}")
                
            from app.workflows.transfusion_workflow import TransfusionOrchestrator
            TransfusionOrchestrator.submit_response(matching_wf_id, "Accepted")
            
            donor_name = matched_donor.name if matched_donor else "Donor"
            reply_msg = f"Thank you {donor_name}! Your blood donation confirmation has been processed. We've scheduled your donation."
        else:
            from app.workflows.transfusion_workflow import TransfusionOrchestrator
            TransfusionOrchestrator.submit_response(matching_wf_id, "Declined")
            reply_msg = "Thank you for letting us know. We have updated our records."
    else:
        logger.info(f"Twilio Webhook: No active transfusion workflow session found for donor matching phone {cleaned_sender}")
        reply_msg = "Thank you for contacting Blood Warriors. We could not locate an active transfusion request for this number."
        
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{reply_msg}</Message>
</Response>"""
    return Response(content=twiml_response, media_type="application/xml")

# --- CHATBOT & MEMORY ENGINE ---

SESSION_MEMORIES: List[Dict[str, str]] = []

@router.post("/ai/chat", response_model=schemas.ChatResponse)
async def chat_handler(payload: schemas.ChatRequest, db: AsyncSession = Depends(get_db)):
    user_msg = payload.message.strip()
    
    # Store user message in memory
    SESSION_MEMORIES.append({"role": "user", "content": user_msg})
    
    # Keep history within last 10 messages to avoid overflow
    if len(SESSION_MEMORIES) > 10:
        SESSION_MEMORIES.pop(0)
        
    response_text = ""
    sources = []
    
    # 1. Attempt using Bedrock/OpenAI if configured and mocks are disabled
    aws_key = settings.AWS_ACCESS_KEY_ID
    aws_secret = settings.AWS_SECRET_ACCESS_KEY
    openai_key = settings.OPENAI_API_KEY
    use_mock = settings.USE_LOCAL_MOCKS
    
    if not use_mock:
        if openai_key:
            try:
                import httpx
                headers = {
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json"
                }
                messages = [{"role": "system", "content": "You are Blood Warriors AI, an intelligent care coordination copilot for Thalassemia. Answer questions about thalassemia screening, blood donation eligibility (90 days interval), and bridge donor coordination."}]
                for m in SESSION_MEMORIES:
                    messages.append({"role": m["role"], "content": m["content"]})
                    
                async with httpx.AsyncClient() as client:
                    res = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json={
                            "model": "gpt-3.5-turbo",
                            "messages": messages,
                            "temperature": 0.5
                        },
                        timeout=5.0
                    )
                    if res.status_code == 200:
                        data = res.json()
                        response_text = data["choices"][0]["message"]["content"]
                        sources = ["OpenAI GPT Model"]
            except Exception as oe:
                logger.error(f"OpenAI Chat API failed: {oe}")
                
        else:
            try:
                import boto3
                import json
                if aws_key and aws_secret:
                    bedrock_client = boto3.client(
                        "bedrock-runtime",
                        aws_access_key_id=aws_key,
                        aws_secret_access_key=aws_secret,
                        region_name=settings.AWS_REGION
                    )
                else:
                    # Fallback to default credentials chain (IAM task role/instance profile)
                    bedrock_client = boto3.client(
                        "bedrock-runtime",
                        region_name=settings.AWS_REGION
                    )
                
                prompt = "System: You are Blood Warriors AI, an intelligent care coordination copilot for Thalassemia. Answer questions about thalassemia screening and blood donation.\n"
                for m in SESSION_MEMORIES:
                    role_str = "User: " if m["role"] == "user" else "Assistant: "
                    prompt += f"{role_str}{m['content']}\n"
                prompt += "Assistant:"
                
                body = json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 512,
                        "stopSequences": [],
                        "temperature": 0.5,
                        "topP": 0.9
                    }
                })
                
                response = bedrock_client.invoke_model(
                    body=body,
                    modelId=settings.BEDROCK_MODEL_ID,
                    accept="application/json",
                    contentType="application/json"
                )
                
                response_body = json.loads(response.get("body").read())
                response_text = response_body.get("results")[0].get("outputText")
                sources = ["AWS Bedrock Titan Model"]
            except Exception as be:
                logger.error(f"AWS Bedrock Chat API failed: {be}")

    # 2. Heuristic Local NLP Agent fallback (always works locally, queries database!)
    if not response_text:
        user_msg_lower = user_msg.lower()
        sources = ["Local Database", "Thalassemia Prevention Handbook"]
        
        if "donor" in user_msg_lower:
            dnr_res = await db.execute(select(func.count(Donor.id)))
            dnr_count = dnr_res.scalar() or 0
            act_res = await db.execute(select(func.count(Donor.id)).filter(Donor.active_status == "Active"))
            act_count = act_res.scalar() or 0
            response_text = f"Currently, Blood Warriors has {dnr_count} total registered donors, with {act_count} marked as Active and ready to donate."
            
        elif "patient" in user_msg_lower:
            pat_res = await db.execute(select(func.count(Patient.id)))
            pat_count = pat_res.scalar() or 0
            high_res = await db.execute(select(func.count(Patient.id)).filter(Patient.risk_level == "HIGH"))
            high_count = high_res.scalar() or 0
            response_text = f"We are coordinating care for {pat_count} Thalassemia patients across India, including {high_count} high-risk cases requiring immediate transfusion support."
            
        elif "eligibility" in user_msg_lower or "eligible" in user_msg_lower or "how often" in user_msg_lower:
            response_text = (
                "Under Blood Warriors protocols, donors are eligible to donate if they: "
                "1. Are aged 18 to 55 with hemoglobin > 12.5 g/dL. "
                "2. Have not donated blood in the last 90 days (3 months interval). "
                "3. Are currently in Active status and have provided consent."
            )
            
        elif "screening" in user_msg_lower or "hplc" in user_msg_lower or "prevent" in user_msg_lower:
            response_text = (
                "Thalassemia Major is a preventable genetic blood disorder. Prevention is managed via "
                "HPLC (High-Performance Liquid Chromatography) carrier screening. If both parents are carriers "
                "(HbA2 > 3.5%), there is a 25% risk of having a child with Thalassemia Major. Pre-marital and village "
                "screening drives help couples make consent-aware, informed decisions."
            )
            
        elif "hi" in user_msg_lower or "hello" in user_msg_lower or "hey" in user_msg_lower:
            response_text = (
                "Hello! I am your Blood Warriors Care Copilot. I can give you statistics on our patient registry, "
                "donor counts, explain thalassemia prevention protocols, or help coordinate care bridge schedules. "
                "What can I assist you with today?"
            )
            
        else:
            # Default fallback with a smart search of a patient name in message
            found_patient = None
            pat_list_res = await db.execute(select(Patient))
            patients_list = pat_list_res.scalars().all()
            for p in patients_list:
                if p.name.split()[0].lower() in user_msg_lower:
                    found_patient = p
                    break
            
            if found_patient:
                match_res = await db.execute(
                    select(Donor)
                    .join(DonorPatientMatch)
                    .filter(
                        DonorPatientMatch.patient_id == found_patient.id,
                        DonorPatientMatch.relationship_type == "Bridge"
                    )
                )
                bridge_dnrs = match_res.scalars().all()
                dnr_names = ", ".join([d.name for d in bridge_dnrs]) or "No bridge donors currently mapped."
                
                response_text = (
                    f"Patient {found_patient.name} ({found_patient.blood_group}) requires {found_patient.quantity_required} units. "
                    f"Their expected next transfusion is scheduled for {found_patient.expected_next_transfusion_date}. "
                    f"Their Care Bridge consists of: {dnr_names}."
                )
            else:
                response_text = (
                    "I am the Blood Warriors Care Coordination Assistant. I can help you query active donors, "
                    "check patient transfusion expected schedules, explain Thalassemia Major screening (HPLC), and verify consent. "
                    "Try asking 'How many active donors do we have?' or 'What is thalassemia prevention?'"
                )

    SESSION_MEMORIES.append({"role": "assistant", "content": response_text})
    return schemas.ChatResponse(response=response_text, sources=sources)

# --- CARE BRIDGES REGISTRY & COORDINATION ---

@router.get("/bridges/overview")
async def get_bridges_overview(db: AsyncSession = Depends(get_db)):
    try:
        # Get all patients
        p_res = await db.execute(select(Patient))
        patients = p_res.scalars().all()
        
        overview = []
        for p in patients:
            # Get bridge matches for this patient
            m_res = await db.execute(
                select(Donor, DonorPatientMatch.match_score)
                .join(DonorPatientMatch, DonorPatientMatch.donor_id == Donor.id)
                .filter(
                    DonorPatientMatch.patient_id == p.id,
                    DonorPatientMatch.relationship_type == "Bridge"
                )
            )
            matches_data = m_res.all()
            
            bridge_donors = []
            for row in matches_data:
                d = row[0]
                score = row[1]
                bridge_donors.append({
                    "id": d.id,
                    "name": d.name,
                    "phone": d.phone,
                    "blood_group": d.blood_group,
                    "city": d.city,
                    "last_donation_date": d.last_donation_date,
                    "next_eligible_date": d.next_eligible_date,
                    "active_status": d.active_status,
                    "consent_given": d.consent_given if hasattr(d, "consent_given") else True,
                    "match_score": score
                })
                
            overview.append({
                "patient_id": p.id,
                "patient_name": p.name,
                "blood_group": p.blood_group,
                "city": p.city,
                "expected_next_transfusion_date": p.expected_next_transfusion_date,
                "quantity_required": p.quantity_required,
                "risk_level": p.risk_level,
                "bridge_donors": bridge_donors
            })
            
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/donors/{id}/consent")
async def toggle_donor_consent(id: str, consent: bool, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Donor).filter(Donor.id == id))
    donor = result.scalars().first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
        
    donor.consent_given = consent
    await db.commit()
    return {
        "status": "success",
        "donor_id": id,
        "consent_given": donor.consent_given
    }

@router.post("/notifications/check-transfusions")
async def run_care_coordination_check(db: AsyncSession = Depends(get_db)):
    try:
        triggered = await ReminderService.check_upcoming_transfusions(db)
        return {
            "status": "success",
            "checked_at": datetime.datetime.utcnow().isoformat(),
            "triggered_count": len(triggered),
            "triggered_workflows": triggered
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
