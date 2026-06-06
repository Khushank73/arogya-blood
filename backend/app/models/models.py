import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class Donor(Base):
    __tablename__ = "donors"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    blood_group = Column(String, index=True)
    city = Column(String, index=True, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    donor_type = Column(String, nullable=True)  # One-Time, Regular, etc.
    donations_till_date = Column(Integer, default=0)
    last_donation_date = Column(String, nullable=True)
    next_eligible_date = Column(String, nullable=True)
    engagement_score = Column(Float, default=0.0)  # scale of 0 to 100 or 0 to 1
    availability_score = Column(Float, default=0.0)  # predicted probability
    churn_risk = Column(Float, default=0.0)  # predicted churn probability
    active_status = Column(String, default="Active")  # Active, Inactive
    consent_given = Column(Boolean, default=True)  # Consent for outreach
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    donations = relationship("DonationHistory", back_populates="donor")
    outreach_logs = relationship("OutreachLog", back_populates="donor")
    matches = relationship("DonorPatientMatch", back_populates="donor")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    blood_group = Column(String, index=True)
    city = Column(String, index=True, nullable=True)
    quantity_required = Column(Float, default=1.0)
    last_transfusion_date = Column(String, nullable=True)
    expected_next_transfusion_date = Column(String, nullable=True)
    risk_level = Column(String, default="LOW")  # LOW, MEDIUM, HIGH
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    matches = relationship("DonorPatientMatch", back_populates="patient")
    donations = relationship("DonationHistory", back_populates="patient")

class DonorPatientMatch(Base):
    __tablename__ = "donor_patient_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String, ForeignKey("patients.id"))
    donor_id = Column(String, ForeignKey("donors.id"))
    match_score = Column(Float, default=0.0)
    relationship_type = Column(String, nullable=True)  # e.g., Regular, Emergency, Backup
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="matches")
    donor = relationship("Donor", back_populates="matches")

class DonationHistory(Base):
    __tablename__ = "donation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    donor_id = Column(String, ForeignKey("donors.id"))
    patient_id = Column(String, ForeignKey("patients.id"), nullable=True)
    donation_date = Column(String, nullable=True)
    status = Column(String, default="Completed")  # Completed, Scheduled, Cancelled
    notes = Column(String, nullable=True)

    # Relationships
    donor = relationship("Donor", back_populates="donations")
    patient = relationship("Patient", back_populates="donations")

class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    donor_id = Column(String, ForeignKey("donors.id"))
    message = Column(String, nullable=True)
    response = Column(String, nullable=True)
    response_status = Column(String, default="Pending")  # Pending, Sent, Accepted, Declined, No Response
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    donor = relationship("Donor", back_populates="outreach_logs")


# --- Prevention Layer Tables from previous execution ---

class HplcCampaign(Base):
    __tablename__ = "hplc_campaigns"

    campaign_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, index=True)
    type = Column(String)  # Village, School, College, Corporate
    location = Column(String)
    date = Column(String)
    registrations_count = Column(Integer, default=0)
    screened_count = Column(Integer, default=0)
    carrier_count = Column(Integer, default=0)

class HplcReport(Base):
    __tablename__ = "hplc_reports"

    report_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("donors.id"), nullable=True)  # Links to donors table
    hba = Column(Float, nullable=True)
    hba2 = Column(Float, nullable=True)
    hbf = Column(Float, nullable=True)
    classification = Column(String)  # Carrier, Non-Carrier, Further Testing Needed
    raw_ocr_text = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)

class GeneticRiskAssessment(Base):
    __tablename__ = "genetic_risk_assessments"

    assessment_id = Column(Integer, primary_key=True, autoincrement=True)
    partner1_report_id = Column(Integer, ForeignKey("hplc_reports.report_id"))
    partner2_report_id = Column(Integer, ForeignKey("hplc_reports.report_id"))
    risk_category = Column(String)  # HIGH, LOW, NONE
    counseling_recommendations = Column(Text, nullable=True)
    awareness_material = Column(Text, nullable=True)

class AwarenessCampaign(Base):
    __tablename__ = "awareness_campaigns"

    campaign_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, index=True)
    type = Column(String)  # School, College, Village, Corporate
    date = Column(String)
    attendees_count = Column(Integer, default=0)
    engagement_score = Column(Integer, default=0)
    conversions_count = Column(Integer, default=0)

class WorkflowState(Base):
    __tablename__ = "workflow_states"

    workflow_id = Column(String, primary_key=True, index=True)
    state_data = Column(Text, nullable=False)  # JSON-serialized TransfusionState
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

