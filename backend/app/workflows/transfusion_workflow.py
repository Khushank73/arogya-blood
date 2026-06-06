import os
import json
import uuid
import datetime
import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Donor, Patient, DonationHistory, OutreachLog, DonorPatientMatch, WorkflowState
from app.services.matching_service import MatchingService
from app.services.notification_service import NotificationService

logger = logging.getLogger("app.workflows.transfusion")

# --- Define State Structure ---
class TransfusionState(TypedDict):
    workflow_id: str
    patient_id: str
    quantity_units: float
    required_by_date: Optional[str]
    status: str  # Pending, Outreach Sent, Confirmed, Completed, Failed
    current_step: str
    ranked_donors: List[Dict[str, Any]]
    tried_donor_ids: List[str]
    assigned_donor_id: Optional[str]
    outreach_message: Optional[str]
    response_received: Optional[str]  # Accepted, Declined, None
    timeline: List[Dict[str, Any]]
    error: Optional[str]

# Persistent workflow directory (retained for backward compatibility and tests)
WORKFLOW_DIR = os.path.join(".", "app_data", "workflows")
os.makedirs(WORKFLOW_DIR, exist_ok=True)

def save_workflow_state(state: TransfusionState):
    db = SessionLocal()
    try:
        wf_state = db.query(WorkflowState).filter(WorkflowState.workflow_id == state["workflow_id"]).first()
        if wf_state:
            wf_state.state_data = json.dumps(state)
            wf_state.updated_at = datetime.datetime.utcnow()
        else:
            wf_state = WorkflowState(
                workflow_id=state["workflow_id"],
                state_data=json.dumps(state)
            )
            db.add(wf_state)
        db.commit()
        logger.info(f"Saved workflow state to database: {state['workflow_id']}")
    except Exception as e:
        logger.error(f"Failed to save workflow state {state['workflow_id']} to database: {e}")
        db.rollback()
    finally:
        db.close()

def load_workflow_state(workflow_id: str) -> Optional[TransfusionState]:
    db = SessionLocal()
    try:
        wf_state = db.query(WorkflowState).filter(WorkflowState.workflow_id == workflow_id).first()
        if wf_state:
            return json.loads(wf_state.state_data)
    except Exception as e:
        logger.error(f"Failed to load workflow state {workflow_id} from database: {e}")
    finally:
        db.close()
    return None

# --- Nodes Implementation ---

def patient_request_node(state: TransfusionState) -> TransfusionState:
    state["current_step"] = "Request Created"
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == state["patient_id"]).first()
        if not patient:
            state["status"] = "Failed"
            state["error"] = "Patient not found"
            state["timeline"].append({
                "step": "Request Created",
                "status": "Failed",
                "message": f"Patient ID {state['patient_id']} does not exist.",
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
            return state
        
        state["timeline"].append({
            "step": "Request Created",
            "status": "Success",
            "message": f"Transfusion request registered for patient {patient.name} ({patient.blood_group}), quantity needed: {state['quantity_units']} units.",
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
    finally:
        db.close()
    return state

def find_donors_node(state: TransfusionState) -> TransfusionState:
    state["current_step"] = "Find Donors"
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == state["patient_id"]).first()
        # Find compatible donors
        donors = db.query(Donor).filter(Donor.active_status == "Active").all()
        # We can just count them
        compatible_count = sum(1 for d in donors if d.blood_group == patient.blood_group)
        state["timeline"].append({
            "step": "Find Donors",
            "status": "Success",
            "message": f"Found {compatible_count} active donors matching blood group {patient.blood_group}.",
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
    finally:
        db.close()
    return state

def rank_donors_node(state: TransfusionState) -> TransfusionState:
    state["current_step"] = "Rank Donors"
    db = SessionLocal()
    try:
        # Get matching candidates from matching service
        matches = MatchingService.get_top_matches(db, state["patient_id"], limit=30)
        
        # Prioritize Care Bridge pool donors over global Emergency/Backup donors
        bridge_donors = [m for m in matches if m.get("relationship_type") == "Bridge"]
        emergency_donors = [m for m in matches if m.get("relationship_type") != "Bridge"]
        combined_matches = bridge_donors + emergency_donors
        
        state["ranked_donors"] = combined_matches[:10]
        
        if not combined_matches:
            state["status"] = "Failed"
            state["error"] = "No compatible donors found"
            state["timeline"].append({
                "step": "Rank Donors",
                "status": "Failed",
                "message": "Smart Matching Engine yielded 0 eligible, compatible donors.",
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
        else:
            top_donor = combined_matches[0]
            type_str = "Care Bridge" if top_donor.get("relationship_type") == "Bridge" else "Emergency Backup"
            state["timeline"].append({
                "step": "Rank Donors",
                "status": "Success",
                "message": f"Successfully ranked donors. Top donor: {top_donor['name']} ({type_str}, Match Score: {int(top_donor['match_score']*100)}%).",
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
    finally:
        db.close()
    return state

def generate_outreach_node(state: TransfusionState) -> TransfusionState:
    state["current_step"] = "Generate Outreach"
    
    # If we already have an assigned donor and are waiting to process a response, skip generation
    if state["assigned_donor_id"] and state["response_received"] is not None:
        return state
        
    # Get all untried donors from the ranked list
    available_donors = [d for d in state["ranked_donors"] if d["donor_id"] not in state["tried_donor_ids"]]
    if not available_donors:
        state["status"] = "Failed"
        state["error"] = "All ranked donors exhausted"
        state["timeline"].append({
            "step": "Outreach Sent",
            "status": "Failed",
            "message": "All recommended donors have been contacted and either declined or did not respond. Escalated to administrator.",
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        return state

    # Send outreach to the top 10 recommended candidates simultaneously
    donors_to_contact = available_donors[:10]
    
    db = SessionLocal()
    try:
        for donor in donors_to_contact:
            state["tried_donor_ids"].append(donor["donor_id"])
            
            msg = f"Dear {donor['name']}, we have an urgent blood requirement for a Thalassemia patient ({donor['blood_group']}). Your match score is {int(donor['match_score']*100)}%. Can you donate?"
            
            db_donor = db.query(Donor).filter(Donor.id == donor["donor_id"]).first()
            phone = db_donor.phone if db_donor else "+91 99999 99999"
            
            try:
                NotificationService.send_outreach(phone, msg)
                logger.info(f"Outreach notification sent successfully to {donor['name']}")
            except Exception as ne:
                logger.error(f"Failed to send outreach to {donor['name']}: {str(ne)}")
                
            log = OutreachLog(
                donor_id=donor["donor_id"],
                message=msg,
                response_status="Sent"
            )
            db.add(log)
        db.commit()
    finally:
        db.close()

    # Assign to top match in this batch as primary placeholder
    top_donor = donors_to_contact[0]
    state["assigned_donor_id"] = top_donor["donor_id"]
    state["outreach_message"] = f"Sent broadcast outreach to {len(donors_to_contact)} matching donors."
    state["status"] = "Outreach Sent"
    
    names_list = ", ".join([d["name"] for d in donors_to_contact])
    state["timeline"].append({
        "step": "Outreach Sent",
        "status": "In Progress",
        "message": f"Broadcast outreach sent to top {len(donors_to_contact)} matching donors: {names_list}. Awaiting confirmation.",
        "timestamp": datetime.datetime.utcnow().isoformat()
    })
    return state

def process_response_node(state: TransfusionState) -> TransfusionState:
    state["current_step"] = "Process Response"
    # This node is triggered when we get a response
    resp = state["response_received"]
    donor_id = state["assigned_donor_id"]
    
    db = SessionLocal()
    try:
        donor = db.query(Donor).filter(Donor.id == donor_id).first()
        donor_name = donor.name if donor else "Donor"
        
        # Update database outreach log
        log = db.query(OutreachLog).filter(OutreachLog.donor_id == donor_id).order_by(OutreachLog.created_at.desc()).first()
        if log:
            log.response = resp
            log.response_status = resp
            db.commit()

        if resp == "Accepted":
            state["status"] = "Confirmed"
            state["timeline"].append({
                "step": "Process Response",
                "status": "Success",
                "message": f"Donor {donor_name} accepted the donation request! Proceeding to scheduling.",
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
        else:
            # Failure Learning: reduce donor engagement score and update availability metrics
            if donor:
                donor.engagement_score = max(0.0, float(donor.engagement_score) - 5.0)
                
                # Recalculate avail score
                from app.ai.availability_model import availability_engine
                days_since = 180.0
                baseline = datetime.datetime(2026, 6, 6)
                if donor.last_donation_date:
                    try:
                        last_don = datetime.datetime.strptime(donor.last_donation_date.strip(), "%d-%m-%Y")
                        days_since = float((baseline - last_don).days)
                    except:
                        pass
                
                donor.availability_score = availability_engine.predict(
                    days_since_last_donation=days_since,
                    donations_till_date=donor.donations_till_date,
                    engagement_score=donor.engagement_score,
                    active_status=True
                )
                db.commit()
                logger.info(f"Failure Learning: Reduced engagement score for donor {donor_name} to {donor.engagement_score} due to decline/no-response.")

            state["timeline"].append({
                "step": "Process Response",
                "status": "Declined",
                "message": f"Donor {donor_name} declined the request ({resp or 'No Response'}). Re-routing to next candidate in the pool.",
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
            # Reset response and assigned donor so generate_outreach can run again
            state["response_received"] = None
            state["assigned_donor_id"] = None
    finally:
        db.close()
        
    return state

def schedule_donation_node(state: TransfusionState) -> TransfusionState:
    state["current_step"] = "Schedule Donation"
    
    db = SessionLocal()
    try:
        donor = db.query(Donor).filter(Donor.id == state["assigned_donor_id"]).first()
        patient = db.query(Patient).filter(Patient.id == state["patient_id"]).first()
        
        # Add to Donation History
        donation_date_str = datetime.datetime.utcnow().strftime("%d-%m-%Y")
        donation = DonationHistory(
            donor_id=state["assigned_donor_id"],
            patient_id=state["patient_id"],
            donation_date=donation_date_str,
            status="Scheduled",
            notes=f"Scheduled via Workflow {state['workflow_id']}"
        )
        db.add(donation)
        
        # Update Donor eligibility dates and scores (Success reinforcement!)
        if donor:
            donor.last_donation_date = donation_date_str
            # Set next eligibility 90 days from now (enforces 3 months periodic rotation)
            next_elig = datetime.datetime.utcnow() + datetime.timedelta(days=90)
            donor.next_eligible_date = next_elig.strftime("%d-%m-%Y")
            donor.donations_till_date += 1
            
            # Increase engagement score
            donor.engagement_score = min(100.0, float(donor.engagement_score) + 5.0)
            
            # Recalculate predictions
            from app.ai.availability_model import availability_engine
            from app.ai.churn_model import churn_engine
            
            donor.availability_score = availability_engine.predict(
                days_since_last_donation=0.0,  # just donated
                donations_till_date=donor.donations_till_date,
                engagement_score=donor.engagement_score,
                active_status=True
            )
            
            response_rate = min(1.0, donor.donations_till_date / max(1, donor.donations_till_date + 3))
            donor.churn_risk = churn_engine.predict(
                engagement_score=donor.engagement_score,
                days_since_last_donation=0.0,
                active_status=True,
                response_rate=response_rate
            )
            
        # Update Patient transfusion schedules
        if patient:
            patient.last_transfusion_date = donation_date_str
            next_trans = datetime.datetime.utcnow() + datetime.timedelta(days=21) # regular 3 weeks cycle
            patient.expected_next_transfusion_date = next_trans.strftime("%d-%m-%Y")
            
        db.commit()
        
        state["status"] = "Completed"
        state["timeline"].append({
            "step": "Schedule Donation",
            "status": "Success",
            "message": f"Donation scheduled successfully. Appointment confirmed for donor {donor.name} on {donation_date_str}.",
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
    finally:
        db.close()
        
    return state

# --- Build LangGraph StateGraph ---

workflow_builder = StateGraph(TransfusionState)

# Add Nodes
workflow_builder.add_node("patient_request", patient_request_node)
workflow_builder.add_node("find_donors", find_donors_node)
workflow_builder.add_node("rank_donors", rank_donors_node)
workflow_builder.add_node("generate_outreach", generate_outreach_node)
workflow_builder.add_node("process_response", process_response_node)
workflow_builder.add_node("schedule_donation", schedule_donation_node)

# Set Entry Point
workflow_builder.set_entry_point("patient_request")

# Connect static transitions
workflow_builder.add_edge("patient_request", "find_donors")
workflow_builder.add_edge("find_donors", "rank_donors")
workflow_builder.add_edge("rank_donors", "generate_outreach")

# Conditional Routing from Outreach/Response
def check_outreach_result(state: TransfusionState) -> str:
    if state["status"] == "Failed":
        return "end"
    if state["response_received"] is None:
        return "end"  # PAUSE graph execution, wait for response!
    return "process_response"

workflow_builder.add_conditional_edges(
    "generate_outreach",
    check_outreach_result,
    {
        "process_response": "process_response",
        "end": END
    }
)

def check_response_result(state: TransfusionState) -> str:
    if state["status"] == "Confirmed":
        return "schedule_donation"
    # If declined, loop back to generate outreach for the next donor
    return "generate_outreach"

workflow_builder.add_conditional_edges(
    "process_response",
    check_response_result,
    {
        "schedule_donation": "schedule_donation",
        "generate_outreach": "generate_outreach"
    }
)

workflow_builder.add_edge("schedule_donation", END)

# Compile Graph
compiled_graph = workflow_builder.compile()

class TransfusionOrchestrator:
    @staticmethod
    def start_workflow(patient_id: str, quantity_units: float = 1.0, required_by_date: Optional[str] = None) -> Dict[str, Any]:
        workflow_id = f"tx-{uuid.uuid4().hex[:8]}"
        initial_state: TransfusionState = {
            "workflow_id": workflow_id,
            "patient_id": patient_id,
            "quantity_units": quantity_units,
            "required_by_date": required_by_date,
            "status": "Pending",
            "current_step": "patient_request",
            "ranked_donors": [],
            "tried_donor_ids": [],
            "assigned_donor_id": None,
            "outreach_message": None,
            "response_received": None,
            "timeline": [],
            "error": None
        }
        
        # Run workflow up to the first waiting step (generate_outreach)
        # Note: In production, the workflow runs up to generate_outreach node, sends message, and pauses.
        final_state = compiled_graph.invoke(initial_state)
        save_workflow_state(final_state)
        return final_state

    @staticmethod
    def submit_response(workflow_id: str, response: str) -> Dict[str, Any]:
        """
        Resume the paused workflow with a donor's response: 'Accepted' or 'Declined'.
        """
        state = load_workflow_state(workflow_id)
        if not state:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        state["response_received"] = response
        
        # Continue execution from process_response
        # We invoke starting from the state loaded
        final_state = compiled_graph.invoke(state)
        save_workflow_state(final_state)
        return final_state
