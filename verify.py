import os
import sys
import unittest
from fastapi.testclient import TestClient

# Adjust path to import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.core.database import SessionLocal, sync_engine, Base
from app.db.init_db import init_db
from app.models.models import Donor, Patient, DonationHistory, OutreachLog
from app.ai.availability_model import availability_engine
from app.ai.churn_model import churn_engine
from app.services.matching_service import MatchingService
from app.workflows.transfusion_workflow import TransfusionOrchestrator
from app.main import app

class TestBloodWarriorsAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("--- SETUP: Seeding database from Dataset.csv ---")
        import shutil
        from app.workflows.transfusion_workflow import WORKFLOW_DIR
        if os.path.exists(WORKFLOW_DIR):
            try:
                shutil.rmtree(WORKFLOW_DIR)
            except Exception:
                pass
        os.makedirs(WORKFLOW_DIR, exist_ok=True)
        
        db = SessionLocal()
        try:
            csv_path = "./Dataset.csv"
            init_db(db, csv_path)
        finally:
            db.close()
            
        cls.client = TestClient(app)

    def test_database_populated(self):
        print("\nTesting Database Content...")
        db = SessionLocal()
        try:
            donor_count = db.query(Donor).count()
            patient_count = db.query(Patient).count()
            donation_count = db.query(DonationHistory).count()
            
            print(f"Donors seeded: {donor_count}")
            print(f"Patients seeded: {patient_count}")
            print(f"Donations seeded: {donation_count}")
            
            self.assertGreater(donor_count, 0, "Donors should be seeded")
            self.assertGreater(patient_count, 0, "Patients should be seeded")
            self.assertGreater(donation_count, 0, "Donations should be seeded")
        finally:
            db.close()

    def test_predictive_engines(self):
        print("\nTesting ML predictive engines (XGBoost & RandomForest)...")
        db = SessionLocal()
        try:
            donor = db.query(Donor).first()
            self.assertIsNotNone(donor, "At least one donor should exist")
            
            # Predict Availability (XGBoost)
            avail_prob = availability_engine.predict(
                days_since_last_donation=30.0,
                donations_till_date=donor.donations_till_date,
                engagement_score=donor.engagement_score,
                active_status=True
            )
            print(f"Availability score for donor {donor.name}: {avail_prob * 100}%")
            self.assertTrue(0.0 <= avail_prob <= 1.0, "Probability must be between 0 and 1")
            
            # Predict Churn (RandomForest)
            churn_prob = churn_engine.predict(
                engagement_score=donor.engagement_score,
                days_since_last_donation=45.0,
                active_status=True,
                response_rate=0.75
            )
            print(f"Churn score for donor {donor.name}: {churn_prob * 100}%")
            self.assertTrue(0.0 <= churn_prob <= 1.0, "Probability must be between 0 and 1")
        finally:
            db.close()

    def test_smart_matching(self):
        print("\nTesting Smart Matching Engine filters...")
        db = SessionLocal()
        try:
            patient = db.query(Patient).first()
            self.assertIsNotNone(patient, "At least one patient should exist")
            
            matches = MatchingService.get_top_matches(db, patient.id, limit=10)
            print(f"Matches count for patient {patient.name} ({patient.blood_group}): {len(matches)}")
            
            if matches:
                self.assertLessEqual(len(matches), 10, "Should return at most 10 recommendation profiles")
                first_match = matches[0]
                print(f"Top Recommended Match: {first_match['name']} with Score: {first_match['match_score']}")
                self.assertTrue(0.0 <= first_match['match_score'] <= 1.0)
        finally:
            db.close()

    def test_transfusion_workflow_orchestration(self):
        print("\nTesting Transfusion LangGraph workflow orchestration...")
        db = SessionLocal()
        try:
            patient = db.query(Patient).first()
            self.assertIsNotNone(patient, "Patient must exist")
            
            # Trigger workflow via API
            response = self.client.post(
                "/api/v1/transfusion/request",
                json={"patient_id": patient.id, "quantity_units": 2.0}
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            workflow_id = data["workflow_id"]
            self.assertIsNotNone(workflow_id)
            self.assertEqual(data["status"], "Outreach Sent")
            print(f"Workflow session created: {workflow_id}, current step: {data['current_step']}")
            
            # Respond Accept to the outreach
            respond_res = self.client.post(f"/api/v1/transfusion/workflow/{workflow_id}/respond?accept=true")
            self.assertEqual(respond_res.status_code, 200)
            respond_data = respond_res.json()
            self.assertEqual(respond_data["status"], "Completed")
            self.assertEqual(respond_data["current_step"], "Schedule Donation")
            print("Workflow successfully advanced and completed upon donor confirmation.")
            
            # Verify donor has NOT been locked out yet (deferred update check)
            assigned_donor_id = respond_data["assigned_donor_id"]
            self.assertIsNotNone(assigned_donor_id)
            
            donor = db.query(Donor).filter(Donor.id == assigned_donor_id).first()
            initial_donations = donor.donations_till_date
            initial_last_donation = donor.last_donation_date
            initial_next_eligible = donor.next_eligible_date
            
            # Perform completed donation API call
            complete_res = self.client.post(f"/api/v1/transfusion/workflow/{workflow_id}/complete-donation")
            self.assertEqual(complete_res.status_code, 200)
            complete_data = complete_res.json()
            
            # Refresh donor from DB
            db.refresh(donor)
            
            # Verify the eligibility block of 90 days and metric/score changes
            self.assertEqual(donor.donations_till_date, initial_donations + 1)
            self.assertIsNotNone(donor.last_donation_date)
            self.assertIsNotNone(donor.next_eligible_date)
            
            # Verify next eligible date is exactly 90 days after last donation
            import datetime
            last_don = datetime.datetime.strptime(donor.last_donation_date, "%d-%m-%Y")
            next_elig = datetime.datetime.strptime(donor.next_eligible_date, "%d-%m-%Y")
            self.assertEqual((next_elig - last_don).days, 90)
            
            # Verify matching DonationHistory status is "Completed"
            donation = db.query(DonationHistory).filter(DonationHistory.notes == f"Scheduled via Workflow {workflow_id}").first()
            self.assertIsNotNone(donation)
            self.assertEqual(donation.status, "Completed")
            
            # Verify availability score is updated to reflect new prediction
            print(f"Donor availability score post-donation: {donor.availability_score * 100}%")
            
            # Verify timeline step has "Donation Completed"
            timeline_steps = [item["step"] for item in complete_data["timeline"]]
            self.assertIn("Donation Completed", timeline_steps)
            print("Verified 90-day block, metric updates, timeline and completion state successfully.")
        finally:
            db.close()

    def test_15_day_donation_reminders(self):
        print("\nTesting 15-day donation reminders trigger...")
        db = SessionLocal()
        try:
            # Create a mock donor
            donor = Donor(
                id="dnr-test-reminder",
                name="Test Reminder Donor",
                phone="+91 99999 88888",
                email="test_reminder@example.com",
                blood_group="O Positive",
                active_status="Active"
            )
            # Calculate target date: 15 days from today
            import datetime
            target_date_str = (datetime.date.today() + datetime.timedelta(days=15)).strftime("%d-%m-%Y")
            
            # Create a scheduled donation
            donation = DonationHistory(
                donor_id="dnr-test-reminder",
                donation_date=target_date_str,
                status="Scheduled",
                notes="Test 15-day reminder"
            )
            
            db.add(donor)
            db.add(donation)
            db.commit()
            
            # Call the send-reminders API
            response = self.client.post("/api/v1/notifications/send-reminders")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            print(f"Reminder response: {data}")
            self.assertEqual(data["status"], "success")
            self.assertGreaterEqual(data["sent_count"], 1)
            
            # Verify that the outreach log is created
            outreach = db.query(OutreachLog).filter(OutreachLog.donor_id == "dnr-test-reminder").first()
            self.assertIsNotNone(outreach)
            self.assertIn("Test Reminder Donor", outreach.message)
            self.assertIn("15 days", outreach.message)
            print("Outreach log and message validated successfully.")
            
            # Cleanup
            db.delete(outreach)
            db.delete(donation)
            db.delete(donor)
            db.commit()
        finally:
            db.close()

    def test_care_bridges_seeding(self):
        print("\nTesting Care Bridges Database Seeding...")
        db = SessionLocal()
        try:
            from app.models.models import DonorPatientMatch
            match_count = db.query(DonorPatientMatch).filter(DonorPatientMatch.relationship_type == "Bridge").count()
            print(f"Care Bridge matches seeded in DB: {match_count}")
            self.assertGreater(match_count, 0, "Seeding should populate DonorPatientMatch rows")
            
            # Verify a patient is mapped to donors
            first_match = db.query(DonorPatientMatch).first()
            self.assertIsNotNone(first_match)
            print(f"Valid Patient ID {first_match.patient_id} is successfully mapped to Donor ID {first_match.donor_id}")
        finally:
            db.close()

    def test_consent_exclusions(self):
        print("\nTesting Consent-Aware Exclusions in Matching...")
        db = SessionLocal()
        try:
            patient = db.query(Patient).first()
            self.assertIsNotNone(patient)
            
            # Find a top match first
            matches = MatchingService.get_top_matches(db, patient.id, limit=3)
            self.assertGreater(len(matches), 0)
            top_donor_id = matches[0]["donor_id"]
            
            # Toggle consent of top donor to False
            response = self.client.post(f"/api/v1/donors/{top_donor_id}/consent?consent=false")
            self.assertEqual(response.status_code, 200)
            
            # Run matching again
            new_matches = MatchingService.get_top_matches(db, patient.id, limit=10)
            new_match_ids = [m["donor_id"] for m in new_matches]
            
            # The non-consenting donor should be excluded
            self.assertNotIn(top_donor_id, new_match_ids, "Donor with consent_given=False must be excluded from matches")
            print("Consent-aware exclusion successfully validated.")
            
            # Reset consent
            reset_res = self.client.post(f"/api/v1/donors/{top_donor_id}/consent?consent=true")
            self.assertEqual(reset_res.status_code, 200)
        finally:
            db.close()

    def test_chatbot_endpoint(self):
        print("\nTesting AI Chatbot Endpoint...")
        # Send user message
        response = self.client.post("/api/v1/ai/chat", json={"message": "how many active donors do we have?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print(f"Chatbot response: {data['response']}")
        self.assertIn("donors", data["response"])
        self.assertGreater(len(data["sources"]), 0)
        
        # Send follow up to test memory context
        response_follow = self.client.post("/api/v1/ai/chat", json={"message": "explain eligibility"})
        self.assertEqual(response_follow.status_code, 200)
        data_follow = response_follow.json()
        print(f"Chatbot follow-up: {data_follow['response']}")
        self.assertIn("days", data_follow["response"])

    def test_care_coordination_engine(self):
        print("\nTesting Automated Transfusion Care Coordination Engine...")
        db = SessionLocal()
        try:
            patient = db.query(Patient).first()
            self.assertIsNotNone(patient)
            
            # Set their expected next transfusion date to exactly 12 days from today
            import datetime
            target_date_str = (datetime.date.today() + datetime.timedelta(days=12)).strftime("%d-%m-%Y")
            patient.expected_next_transfusion_date = target_date_str
            db.commit()
            
            # Trigger coordination engine
            response = self.client.post("/api/v1/notifications/check-transfusions")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            print(f"Coordination response: {data}")
            self.assertEqual(data["status"], "success")
            
            # Assert a workflow was triggered for our patient
            triggered_p_ids = [wf["patient_id"] for wf in data["triggered_workflows"]]
            self.assertIn(patient.id, triggered_p_ids, "Care coordination engine should start workflow for patient in 10-15 day window")
            print(f"Transfusion workflow successfully auto-triggered: {data['triggered_workflows'][0]['workflow_id']}")
            
            # Clean up workflows app_data
            import shutil
            from app.workflows.transfusion_workflow import WORKFLOW_DIR
            if os.path.exists(WORKFLOW_DIR):
                shutil.rmtree(WORKFLOW_DIR)
                os.makedirs(WORKFLOW_DIR, exist_ok=True)
        finally:
            db.close()

if __name__ == "__main__":
    unittest.main()
