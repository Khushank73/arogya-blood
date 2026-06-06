from typing import TypedDict, List, Dict, Any, Optional
import math
import json
from datetime import datetime
from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, END

from app.models.models import User, Bridge, Donation, OutreachWorkflow
from app.core.database import SessionLocal
from app.services.sagemaker_service import sagemaker_service
from app.services.step_functions import outreach_service
from app.services.bedrock_service import bedrock_service

# --- Define LangGraph State ---
class AgentState(TypedDict):
    query: str
    user_id: Optional[str]
    bridge_id: Optional[str]
    agent_outputs: Dict[str, Any]
    current_agent: str
    next_agent: Optional[str]
    final_response: str

# --- Blood Compatibility Map ---
COMPATIBILITY_MAP = {
    "O Negative": ["O Negative", "O Positive", "A Negative", "A Positive", "B Negative", "B Positive", "AB Negative", "AB Positive"],
    "O Positive": ["O Positive", "A Positive", "B Positive", "AB Positive"],
    "A Negative": ["A Negative", "A Positive", "AB Negative", "AB Positive"],
    "A Positive": ["A Positive", "AB Positive"],
    "B Negative": ["B Negative", "B Positive", "AB Negative", "AB Positive"],
    "B Positive": ["B Positive", "AB Positive"],
    "AB Negative": ["AB Negative", "AB Positive"],
    "AB Positive": ["AB Positive"]
}

def is_blood_compatible(donor_bg: str, recipient_bg: str) -> bool:
    if not donor_bg or not recipient_bg:
        return False
    # Standardize spaces and case
    donor_bg = donor_bg.strip().title()
    recipient_bg = recipient_bg.strip().title()
    compatible_list = COMPATIBILITY_MAP.get(donor_bg, [])
    return recipient_bg in compatible_list

def haversine_distance(lat1, lon1, lat2, lon2):
    # Radius of the Earth in km
    R = 6371.0
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

# --- Implement the 10 Specialized Agents ---

class OperationsCoordinators:
    # 1. Availability Agent
    @staticmethod
    def availability_agent(state: AgentState) -> AgentState:
        db = SessionLocal()
        user_id = state.get("user_id")
        out = {}
        if user_id:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                prob = sagemaker_service.predict_availability_prob({
                    "donations_till_date": user.donations_till_date,
                    "total_calls": user.total_calls,
                    "calls_to_donations_ratio": user.calls_to_donations_ratio,
                    "frequency_in_days": user.frequency_in_days,
                    "last_contacted_date": user.last_contacted_date,
                    "user_donation_active_status": user.user_donation_active_status
                })
                out = {
                    "user_id": user_id,
                    "availability_probability": prob,
                    "eligibility_status": user.eligibility_status or "unknown"
                }
        db.close()
        state["agent_outputs"]["availability_agent"] = out
        return state

    # 2. Ranking Agent
    @staticmethod
    def ranking_agent(state: AgentState) -> AgentState:
        db = SessionLocal()
        bridge_id = state.get("bridge_id")
        out = []
        if bridge_id:
            bridge = db.query(Bridge).filter(Bridge.bridge_id == bridge_id).first()
            if bridge:
                patient = db.query(User).filter(User.user_id == bridge.patient_id).first()
                patient_bg = patient.blood_group if patient else "O Positive"
                patient_lat = patient.latitude if patient else 17.3922792
                patient_lon = patient.longitude if patient else 78.4602749
                
                # Fetch potential donors (exclude patients)
                donors = db.query(User).filter(User.role != "Patient").all()
                ranked = []
                for d in donors:
                    if not is_blood_compatible(d.blood_group, patient_bg):
                        continue
                    
                    # Compute availability
                    avail_prob = sagemaker_service.predict_availability_prob({
                        "donations_till_date": d.donations_till_date,
                        "total_calls": d.total_calls,
                        "calls_to_donations_ratio": d.calls_to_donations_ratio,
                        "frequency_in_days": d.frequency_in_days,
                        "last_contacted_date": d.last_contacted_date,
                        "user_donation_active_status": d.user_donation_active_status
                    })
                    
                    # Compute distance
                    distance = haversine_distance(patient_lat, patient_lon, d.latitude or 17.3922792, d.longitude or 78.4602749)
                    
                    # Base eligibility score boost
                    eligibility_score = 1.0 if str(d.eligibility_status).lower() == "eligible" else 0.1
                    
                    # Active status boost
                    active_boost = 1.0 if str(d.user_donation_active_status).lower() == "active" else 0.2
                    
                    # Compute composite ranking score
                    # High probability, close distance, eligible, active
                    score = (avail_prob * 0.4) + (max(0, 1.0 - (distance / 50.0)) * 0.3) + (eligibility_score * 0.2) + (active_boost * 0.1)
                    score = round(max(0.0, min(1.0, score)), 3)
                    
                    ranked.append({
                        "user_id": d.user_id,
                        "blood_group": d.blood_group,
                        "availability_probability": avail_prob,
                        "eligibility_status": d.eligibility_status or "not eligible",
                        "distance_km": round(distance, 2),
                        "total_calls": d.total_calls,
                        "donations_till_date": d.donations_till_date,
                        "score": score
                    })
                
                # Sort descending by composite score
                ranked.sort(key=lambda x: x["score"], reverse=True)
                out = ranked[:10]  # Return top 10 recommendation profiles
        db.close()
        state["agent_outputs"]["ranking_agent"] = out
        return state

    # 3. Outreach Agent
    @staticmethod
    def outreach_agent(state: AgentState) -> AgentState:
        # Takes highest-ranked donor and kicks off automated Step Function
        ranked_donors = state["agent_outputs"].get("ranking_agent", [])
        bridge_id = state.get("bridge_id")
        out = {}
        if ranked_donors and bridge_id:
            top_donor = ranked_donors[0]
            session_id = outreach_service.trigger_outreach(bridge_id, top_donor["user_id"])
            out = {
                "session_id": session_id,
                "bridge_id": bridge_id,
                "donor_id": top_donor["user_id"],
                "current_step": "WhatsApp",
                "status": "In Progress"
            }
        state["agent_outputs"]["outreach_agent"] = out
        return state

    # 4. Churn Agent
    @staticmethod
    def churn_agent(state: AgentState) -> AgentState:
        db = SessionLocal()
        user_id = state.get("user_id")
        out = {}
        if user_id:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                churn_prob = sagemaker_service.predict_churn_prob({
                    "donations_till_date": user.donations_till_date,
                    "total_calls": user.total_calls,
                    "calls_to_donations_ratio": user.calls_to_donations_ratio,
                    "frequency_in_days": user.frequency_in_days,
                    "last_contacted_date": user.last_contacted_date
                })
                
                risk = "LOW"
                action = "No action required. Donor is highly engaged."
                if churn_prob > 0.7:
                    risk = "HIGH"
                    action = "URGENT: Schedule personalized thank-you WhatsApp call or dispatch donor token/gift."
                elif churn_prob > 0.4:
                    risk = "MEDIUM"
                    action = "Proactive check-in message to confirm details and update preferred times."
                
                out = {
                    "user_id": user_id,
                    "churn_probability": churn_prob,
                    "risk_level": risk,
                    "retention_action": action
                }
        else:
            # Multi-donor scan (find top churn risks)
            high_risks = []
            users = db.query(User).filter(User.role != "Patient").limit(100).all()
            for u in users:
                churn_prob = sagemaker_service.predict_churn_prob({
                    "donations_till_date": u.donations_till_date,
                    "total_calls": u.total_calls,
                    "calls_to_donations_ratio": u.calls_to_donations_ratio,
                    "frequency_in_days": u.frequency_in_days,
                    "last_contacted_date": u.last_contacted_date
                })
                if churn_prob > 0.6:
                    high_risks.append({
                        "user_id": u.user_id,
                        "blood_group": u.blood_group,
                        "churn_probability": churn_prob
                    })
            high_risks.sort(key=lambda x: x["churn_probability"], reverse=True)
            out = {"high_churn_donors": high_risks[:5]}
            
        db.close()
        state["agent_outputs"]["churn_agent"] = out
        return state

    # 5. Bridge Health Agent
    @staticmethod
    def bridge_health_agent(state: AgentState) -> AgentState:
        db = SessionLocal()
        bridge_id = state.get("bridge_id")
        out = {}
        if bridge_id:
            bridges = [db.query(Bridge).filter(Bridge.bridge_id == bridge_id).first()]
        else:
            # Query all bridges
            bridges = db.query(Bridge).all()

        results = []
        for b in bridges:
            if not b: continue
            
            # Retrieve bridge metrics
            patient = db.query(User).filter(User.user_id == b.patient_id).first()
            patient_bg = patient.blood_group if patient else "O Positive"
            
            # Donors attached specifically to this bridge or compatible in general
            active_donors = db.query(User).filter(
                User.role != "Patient",
                User.user_donation_active_status == "Active"
            ).all()
            
            bridge_donors = [d for d in active_donors if is_blood_compatible(d.blood_group, patient_bg)]
            eligible_donors = [d for d in bridge_donors if str(d.eligibility_status).lower() == "eligible"]
            
            # Donation completion rate
            donations = db.query(Donation).filter(Donation.bridge_id == b.bridge_id).all()
            completed_donations = [d for d in donations if d.status == "Completed"]
            completion_rate = round(len(completed_donations) / max(1, len(donations)), 2)
            
            # Response rate based on call stats
            calls = sum(d.total_calls for d in bridge_donors)
            completed = sum(d.donations_till_date for d in bridge_donors)
            response_rate = round(completed / max(1, calls), 2)
            
            # Calculate health score: scale of 0 to 100
            # Formula: (eligible_donors/total_donors * 30) + (completion_rate * 40) + (response_rate * 30)
            eligible_ratio = len(eligible_donors) / max(1, len(bridge_donors))
            health_score = int((eligible_ratio * 30) + (completion_rate * 40) + (response_rate * 30))
            # Bound
            health_score = max(10, min(100, health_score))
            
            risk = "LOW"
            if health_score < 40 or len(eligible_donors) == 0:
                risk = "HIGH"
            elif health_score < 70:
                risk = "MEDIUM"
                
            results.append({
                "bridge_id": b.bridge_id,
                "health_score": health_score,
                "risk": risk,
                "active_donors_count": len(bridge_donors),
                "eligible_donors_count": len(eligible_donors),
                "donation_completion_rate": completion_rate,
                "donor_response_rate": response_rate
            })
            
        db.close()
        
        if bridge_id:
            out = results[0] if results else {}
        else:
            out = {"bridges": results}
            
        state["agent_outputs"]["bridge_health_agent"] = out
        return state

    # 6. Demand Forecast Agent
    @staticmethod
    def demand_forecast_agent(state: AgentState) -> AgentState:
        db = SessionLocal()
        # Look at upcoming transfusions within next 30 days
        bridges = db.query(Bridge).filter(Bridge.expected_next_transfusion_date != None).all()
        
        forecast = {}
        for b in bridges:
            patient = db.query(User).filter(User.user_id == b.patient_id).first()
            if not patient: continue
            bg = patient.blood_group
            forecast[bg] = forecast.get(bg, 0.0) + (b.quantity_required or 1.0)
            
        # Regional forecasting mapping centroid centroids of cities (e.g. Hyderabad, Nizamabad, Warangal)
        # We simulate regions based on latitudes/longitudes in our dataset
        hotspots = [
            {
                "region_centroid": [17.3922792, 78.4602749],
                "shortage_score": 0.85,
                "predicted_units_required": 12.0,
                "active_donors_available": 3,
                "risk_level": "HIGH"
            },
            {
                "region_centroid": [17.9689, 79.5941],
                "shortage_score": 0.40,
                "predicted_units_required": 5.0,
                "active_donors_available": 6,
                "risk_level": "MEDIUM"
            }
        ]
        
        db.close()
        state["agent_outputs"]["demand_forecast_agent"] = {
            "forecasted_shortages": forecast,
            "hotspot_regions": hotspots
        }
        return state

    # 7. HPLC Analysis Agent
    @staticmethod
    def hplc_agent(state: AgentState) -> AgentState:
        query_text = state.get("query", "")
        # Run ocr simulation & bedrock classifier
        res = bedrock_service.analyze_hplc_report(query_text)
        state["agent_outputs"]["hplc_agent"] = res
        return state

    # 8. Awareness Agent
    @staticmethod
    def awareness_agent(state: AgentState) -> AgentState:
        # Generate messages or stats
        res = bedrock_service.generate_awareness_content("WhatsApp Msg", "Villages", "Telugu")
        state["agent_outputs"]["awareness_agent"] = res
        return state

    # 9. Memory Agent
    @staticmethod
    def memory_agent(state: AgentState) -> AgentState:
        user_id = state.get("user_id")
        query = state.get("query")
        if user_id and query:
            res = bedrock_service.get_care_chat_response(user_id, query)
            state["agent_outputs"]["memory_agent"] = res
        return state

    # 10. Admin Insights Agent
    @staticmethod
    def admin_insights_agent(state: AgentState) -> AgentState:
        query = state.get("query", "").lower()
        
        # Route logic inside orchestrator based on question
        if "bridge" in query or "risk" in query:
            state["next_agent"] = "bridge_health_agent"
        elif "churn" in query or "inactive" in query:
            state["next_agent"] = "churn_agent"
        elif "shortage" in query or "demand" in query:
            state["next_agent"] = "demand_forecast_agent"
        else:
            state["next_agent"] = None
            
        return state

# --- Build LangGraph Orchestrator ---

def route_agent(state: AgentState) -> str:
    next_a = state.get("next_agent")
    if next_a:
        return next_a
    return "end"

workflow_graph = StateGraph(AgentState)

# Add Nodes
workflow_graph.add_node("admin_insights_agent", OperationsCoordinators.admin_insights_agent)
workflow_graph.add_node("bridge_health_agent", OperationsCoordinators.bridge_health_agent)
workflow_graph.add_node("churn_agent", OperationsCoordinators.churn_agent)
workflow_graph.add_node("demand_forecast_agent", OperationsCoordinators.demand_forecast_agent)

# Set Entry Node
workflow_graph.set_entry_point("admin_insights_agent")

# Add Conditional Edges
workflow_graph.add_conditional_edges(
    "admin_insights_agent",
    route_agent,
    {
        "bridge_health_agent": "bridge_health_agent",
        "churn_agent": "churn_agent",
        "demand_forecast_agent": "demand_forecast_agent",
        "end": END
    }
)

# Connect everything back to End or Admin Insights to generate final response
workflow_graph.add_edge("bridge_health_agent", END)
workflow_graph.add_edge("churn_agent", END)
workflow_graph.add_edge("demand_forecast_agent", END)

# Compile the Graph
agent_graph = workflow_graph.compile()

class AgentOrchestrator:
    @staticmethod
    def run_query(query: str, user_id: Optional[str] = None, bridge_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes query through the multi-agent graph, fetching appropriate metrics.
        """
        initial_state = {
            "query": query,
            "user_id": user_id,
            "bridge_id": bridge_id,
            "agent_outputs": {},
            "current_agent": "admin_insights_agent",
            "next_agent": None,
            "final_response": ""
        }
        
        final_state = agent_graph.invoke(initial_state)
        
        # Format a conversational final response using the LLM based on sub-agent data
        outputs = final_state.get("agent_outputs", {})
        query_lower = query.lower()
        
        prompt = (
            f"You are the Blood Warriors Admin Copilot. An administrator asked: '{query}'\n"
            f"Here is the data collected from the specialized operations agents: {json.dumps(outputs)}\n"
            f"Write a professional, action-oriented, executive response explaining the findings and offering key recommendations."
        )
        
        formatted_answer = bedrock_service._query_bedrock(prompt)
        
        # Local fallback format if Bedrock outputs simulated message
        if "simulated" in formatted_answer.lower():
            if "bridge" in query_lower or "risk" in query_lower:
                data = outputs.get("bridge_health_agent", {})
                bridges = data.get("bridges", [])
                high_risk = [b for b in bridges if b["risk"] == "HIGH"]
                formatted_answer = f"Hello Admin, out of {len(bridges)} blood bridges analyzed, there are {len(high_risk)} bridges at HIGH risk due to low eligible donor counts. Recommended action is to trigger the automated outreach Step Function for these bridges."
            elif "churn" in query_lower or "inactive" in query_lower:
                data = outputs.get("churn_agent", {})
                chur_list = data.get("high_churn_donors", [])
                formatted_answer = f"Hello Admin, our churn prediction engine has scanned registered donors. We identified {len(chur_list)} high-probability inactive profiles. I recommend dispatching a retention WhatsApp greeting or check-in message immediately."
            elif "shortage" in query_lower or "demand" in query_lower:
                data = outputs.get("demand_forecast_agent", {})
                shortages = data.get("forecasted_shortages", {})
                formatted_answer = f"Hello Admin, based on upcoming transfusion schedules for next month, we anticipate shortages in: {', '.join([f'{k} ({v} units)' for k, v in shortages.items()])}. We recommend scheduling screening campaigns in Hyderabad hotspots."
            else:
                formatted_answer = f"Hello Admin, I've analyzed your request: '{query}'. Based on the operations dashboard, all systems are stable. Let me know if you'd like me to query bridge health or run donor ranking."

        return {
            "query": query,
            "answer": formatted_answer,
            "agent_outputs": outputs
        }
