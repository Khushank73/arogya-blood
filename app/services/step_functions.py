import asyncio
import datetime
import uuid
import logging
from sqlalchemy.orm import Session
from app.models.models import OutreachWorkflow, Bridge, User, Donation
from app.core.database import SessionLocal
from app.core.aws import get_aws_client

logger = logging.getLogger("app.step_functions")

# Production AWS Step Functions - Amazon States Language (ASL) Definition
OUTREACH_STATE_MACHINE_ASL = {
    "Comment": "Blood Warriors outreach automation workflow",
    "StartAt": "RankDonors",
    "States": {
        "RankDonors": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123456789012:function:rank_donors",
            "Next": "SendWhatsApp"
        },
        "SendWhatsApp": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123456789012:function:send_whatsapp",
            "Next": "WaitForWhatsAppResponse"
        },
        "WaitForWhatsAppResponse": {
            "Type": "Wait",
            "Seconds": 7200,  # Wait 2 hours
            "Next": "CheckWhatsAppResponse"
        },
        "CheckWhatsAppResponse": {
            "Type": "Choice",
            "Choices": [
                {
                    "Variable": "$.response_status",
                    "StringEquals": "COMPLETED",
                    "Next": "OutreachSuccess"
                }
            ],
            "Default": "SendSMS"
        },
        "SendSMS": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123456789012:function:send_sms",
            "Next": "WaitForSMSResponse"
        },
        "WaitForSMSResponse": {
            "Type": "Wait",
            "Seconds": 3600,  # Wait 1 hour
            "Next": "CheckSMSResponse"
        },
        "CheckSMSResponse": {
            "Type": "Choice",
            "Choices": [
                {
                    "Variable": "$.response_status",
                    "StringEquals": "COMPLETED",
                    "Next": "OutreachSuccess"
                }
            ],
            "Default": "SendVoiceCall"
        },
        "SendVoiceCall": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123456789012:function:send_voice",
            "Next": "WaitForVoiceResponse"
        },
        "WaitForVoiceResponse": {
            "Type": "Wait",
            "Seconds": 1800,  # Wait 30 mins
            "Next": "CheckVoiceResponse"
        },
        "CheckVoiceResponse": {
            "Type": "Choice",
            "Choices": [
                {
                    "Variable": "$.response_status",
                    "StringEquals": "COMPLETED",
                    "Next": "OutreachSuccess"
                }
            ],
            "Default": "EscalateToVolunteer"
        },
        "EscalateToVolunteer": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123456789012:function:notify_volunteer",
            "Next": "OutreachFailed"
        },
        "OutreachSuccess": {
            "Type": "Succeed"
        },
        "OutreachFailed": {
            "Type": "Fail",
            "Cause": "No response from donor after WhatsApp, SMS, and Voice escalations."
        }
    }
}

class OutreachStepFunctionService:
    def __init__(self):
        self.sfn_client = get_aws_client("stepfunctions")

    def trigger_outreach(self, bridge_id: str, donor_id: str) -> str:
        """
        Triggers outreach state machine. Local mock runs an asynchronous python worker.
        """
        session_id = f"outreach-{uuid.uuid4().hex[:8]}"
        
        # Save starting state to database
        db = SessionLocal()
        try:
            workflow = OutreachWorkflow(
                session_id=session_id,
                bridge_id=bridge_id,
                donor_id=donor_id,
                current_step="WhatsApp",
                status="In Progress"
            )
            db.add(workflow)
            db.commit()
            db.refresh(workflow)
        finally:
            db.close()

        # Trigger actual Step Function if not mocked
        if not hasattr(self.sfn_client, "mock_dir"):
            try:
                import json
                self.sfn_client.start_execution(
                    stateMachineArn="arn:aws:states:us-east-1:123456789012:stateMachine:BloodWarriorsOutreach",
                    name=session_id,
                    input=json.dumps({"bridge_id": bridge_id, "donor_id": donor_id})
                )
            except Exception as e:
                logger.error(f"Failed to start Step Function execution: {e}")

        # Start local async simulation in background
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.run_local_simulation(session_id, bridge_id, donor_id))
        except RuntimeError:
            pass
        
        return session_id

    async def run_local_simulation(self, session_id: str, bridge_id: str, donor_id: str):
        """
        Simulates state transitions with small sleep times for local testing.
        Steps: WhatsApp -> (wait 3s) -> SMS -> (wait 3s) -> Voice -> (wait 3s) -> Escalation
        """
        steps = ["WhatsApp", "SMS", "Voice", "Escalated", "Finished"]
        
        for i, step in enumerate(steps[:-1]):
            # Wait to simulate donor thinking/responding
            await asyncio.sleep(4)
            
            db = SessionLocal()
            try:
                workflow = db.query(OutreachWorkflow).filter(OutreachWorkflow.session_id == session_id).first()
                if not workflow:
                    db.close()
                    break
                
                # Check if donor responded in the meantime (status changed to Completed by external action)
                if workflow.status == "Completed":
                    logger.info(f"Local simulation completed successfully for session {session_id}")
                    db.close()
                    break
                
                # Transition to next step
                next_step = steps[i+1]
                workflow.current_step = next_step
                workflow.updated_at = datetime.datetime.utcnow()
                
                if next_step == "Finished":
                    workflow.status = "Completed"
                    logger.info(f"Outreach workflow {session_id} finished successfully.")
                elif next_step == "Escalated":
                    workflow.status = "Failed"
                    logger.warning(f"Outreach workflow {session_id} escalated to volunteers.")
                    # Trigger a mock notification to volunteers
                    self.notify_volunteer_mock(donor_id, bridge_id)
                else:
                    logger.info(f"Outreach workflow {session_id} transitioned to {next_step}")
                
                db.commit()
            except Exception as e:
                logger.error(f"Error in outreach simulation: {e}")
            finally:
                db.close()

            # Stop loop if finished or failed
            if next_step in ["Finished", "Escalated"]:
                break

    def notify_volunteer_mock(self, donor_id: str, bridge_id: str):
        logger.warning(f"[NOTIFICATION] Escalation Alert: Donor {donor_id} failed to respond for Bridge {bridge_id}. Volunteer notified!")

    def respond_to_outreach(self, session_id: str, accept: bool = True) -> bool:
        """
        Updates the workflow status when a donor replies.
        """
        db = SessionLocal()
        try:
            workflow = db.query(OutreachWorkflow).filter(OutreachWorkflow.session_id == session_id).first()
            if not workflow or workflow.status != "In Progress":
                return False
            
            if accept:
                workflow.status = "Completed"
                workflow.current_step = "Finished"
                # Record successful donation in donations history
                donation = Donation(
                    user_id=workflow.donor_id,
                    bridge_id=workflow.bridge_id,
                    donation_date=datetime.datetime.utcnow().strftime("%d-%m-%Y"),
                    status="Completed"
                )
                db.add(donation)
            else:
                # If they decline, escalate immediately to next step
                workflow.status = "Failed"
                workflow.current_step = "Escalated"
                self.notify_volunteer_mock(workflow.donor_id, workflow.bridge_id)
                
            workflow.updated_at = datetime.datetime.utcnow()
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error responding to outreach: {e}")
            return False
        finally:
            db.close()

outreach_service = OutreachStepFunctionService()
