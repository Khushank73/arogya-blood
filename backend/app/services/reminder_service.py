import datetime
import logging
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import DonationHistory, Donor, OutreachLog
from app.services.notification_service import NotificationService

logger = logging.getLogger("app.services.reminder")

class ReminderService:
    @staticmethod
    async def check_and_send_scheduled_reminders(db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Scans for donations scheduled exactly 15 days from today and triggers WhatsApp reminders.
        """
        # Calculate target date: exactly 15 days from today (stored in dd-mm-yyyy format)
        today = datetime.date.today()
        target_date = today + datetime.timedelta(days=15)
        target_date_str = target_date.strftime("%d-%m-%Y")
        
        logger.info(f"Scanning for donation reminders scheduled for: {target_date_str}")
        
        # Query scheduled donations with eager loading of donor profiles
        stmt = (
            select(DonationHistory)
            .filter(
                DonationHistory.status == "Scheduled",
                DonationHistory.donation_date == target_date_str
            )
            .options(selectinload(DonationHistory.donor))
        )
        
        result = await db.execute(stmt)
        scheduled_donations = result.scalars().all()
        
        sent_reminders = []
        
        for donation in scheduled_donations:
            donor = donation.donor
            if not donor:
                logger.warning(f"Donation record ID {donation.id} has no associated donor.")
                continue
            
            phone = donor.phone or "+91 99999 99999" # fallback placeholder phone
            custom_message = (
                f"Dear {donor.name}, this is a reminder from Blood Warriors that you have "
                f"a blood donation scheduled on {donation.donation_date} (in 15 days) "
                f"for Thalassemia support. Thank you for your support!"
            )
            
            # Send outreach message (SMS or WhatsApp)
            try:
                message_sid = NotificationService.send_outreach(phone, custom_message)
                
                # Create and persist outreach log
                outreach_log = OutreachLog(
                    donor_id=donor.id,
                    message=custom_message,
                    response=None,
                    response_status="Sent"
                )
                db.add(outreach_log)
                
                sent_reminders.append({
                    "donation_id": donation.id,
                    "donor_id": donor.id,
                    "donor_name": donor.name,
                    "phone": phone,
                    "message_sid": message_sid,
                    "date": target_date_str
                })
                
                logger.info(f"AWS SNS reminder queued successfully for donor {donor.name} ({phone})")
            except Exception as e:
                logger.error(f"Failed to queue AWS SNS reminder for donor {donor.name}: {str(e)}")
                
        if sent_reminders:
            await db.commit()
            logger.info(f"Dispatched {len(sent_reminders)} reminders successfully.")
        else:
            logger.info("No donations scheduled in 15 days. No reminders sent.")
            
        return sent_reminders

    @staticmethod
    async def check_upcoming_transfusions(db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Scans for patients whose next expected transfusion is in the 10-15 day window,
        and automatically initializes care bridge transfusion workflows for them if not already active.
        """
        import os
        import json
        import datetime
        from app.models.models import Patient, DonationHistory
        from app.workflows.transfusion_workflow import TransfusionOrchestrator, WORKFLOW_DIR
        
        today = datetime.date.today()
        start_date = today + datetime.timedelta(days=10)
        end_date = today + datetime.timedelta(days=15)
        
        logger.info(f"Scanning for upcoming transfusions in window {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}...")
        
        # Fetch all patients
        stmt = select(Patient)
        result = await db.execute(stmt)
        patients = result.scalars().all()
        
        triggered_workflows = []
        
        # Load active workflows to check for duplicate sessions
        active_wf_patients = set()
        if os.path.exists(WORKFLOW_DIR):
            for file_name in os.listdir(WORKFLOW_DIR):
                if file_name.endswith(".json"):
                    try:
                        with open(os.path.join(WORKFLOW_DIR, file_name), "r") as f:
                            wf_state = json.load(f)
                            if wf_state.get("status") not in ["Completed", "Failed"]:
                                active_wf_patients.add(wf_state.get("patient_id"))
                    except Exception as we:
                        logger.error(f"Error loading workflow file {file_name}: {we}")
        
        for patient in patients:
            if not patient.expected_next_transfusion_date:
                continue
                
            try:
                exp_date = datetime.datetime.strptime(patient.expected_next_transfusion_date.strip(), "%d-%m-%Y").date()
                logger.info(f"Patient {patient.name} ({patient.id}) exp_date parsed: {exp_date}, start: {start_date}, end: {end_date}, is_in_window: {start_date <= exp_date <= end_date}")
            except ValueError:
                logger.warning(f"Patient {patient.name} ({patient.id}) has invalid transfusion date: {patient.expected_next_transfusion_date}")
                continue
                
            if start_date <= exp_date <= end_date:
                # Patient needs transfusion in 10-15 days. Check if already coordinated.
                if patient.id in active_wf_patients:
                    logger.info(f"Active workflow session already exists for patient {patient.name} ({patient.id}). Skipping.")
                    continue
                    
                # Check for existing scheduled/completed donation history close to expected date
                history_stmt = (
                    select(DonationHistory)
                    .filter(
                        DonationHistory.patient_id == patient.id,
                        DonationHistory.status.in_(["Scheduled", "Completed"])
                    )
                )
                history_res = await db.execute(history_stmt)
                histories = history_res.scalars().all()
                
                already_scheduled = False
                for h in histories:
                    if h.donation_date:
                        try:
                            don_date = datetime.datetime.strptime(h.donation_date.strip(), "%d-%m-%Y").date()
                            if abs((don_date - exp_date).days) <= 5:
                                already_scheduled = True
                                break
                        except ValueError:
                            pass
                            
                if already_scheduled:
                    logger.info(f"Donation already scheduled/completed for patient {patient.name} near {patient.expected_next_transfusion_date}. Skipping.")
                    continue
                    
                # Trigger care bridge workflow automatically!
                logger.info(f"Auto-triggering Care Bridge coordination for patient {patient.name} (Transfusion Expected: {patient.expected_next_transfusion_date})")
                try:
                    wf = TransfusionOrchestrator.start_workflow(
                        patient_id=patient.id,
                        quantity_units=patient.quantity_required or 1.5,
                        required_by_date=patient.expected_next_transfusion_date
                    )
                    triggered_workflows.append({
                        "patient_id": patient.id,
                        "patient_name": patient.name,
                        "blood_group": patient.blood_group,
                        "expected_date": patient.expected_next_transfusion_date,
                        "workflow_id": wf["workflow_id"],
                        "assigned_donor_id": wf.get("assigned_donor_id"),
                        "status": wf["status"]
                    })
                except Exception as t_err:
                    logger.error(f"Failed to start workflow for patient {patient.name}: {t_err}")
                    
        return triggered_workflows
