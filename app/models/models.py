from sqlalchemy import Column, String, Integer, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    role = Column(String, index=True)  # Patient, Bridge Donor, Emergency Donor, Volunteer, Guest
    role_status = Column(String, nullable=True)
    blood_group = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    registration_date = Column(String, nullable=True)
    donor_type = Column(String, nullable=True)  # One-Time Donor, Regular Donor, etc.
    last_contacted_date = Column(String, nullable=True)
    last_donation_date = Column(String, nullable=True)
    next_eligible_date = Column(String, nullable=True)
    donations_till_date = Column(Integer, default=0)
    eligibility_status = Column(String, nullable=True)  # eligible, not eligible
    cycle_of_donations = Column(Integer, default=0)
    total_calls = Column(Integer, default=0)
    frequency_in_days = Column(Integer, default=0)
    donated_earlier = Column(String, nullable=True)
    calls_to_donations_ratio = Column(Float, default=0.0)
    user_donation_active_status = Column(String, default="Active")  # Active, Inactive
    inactive_trigger_comment = Column(String, nullable=True)
    
    # Relationships
    donations = relationship("Donation", back_populates="user")
    hplc_reports = relationship("HplcReport", back_populates="user")

class Bridge(Base):
    __tablename__ = "bridges"

    bridge_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("users.user_id"), nullable=True)
    status_of_bridge = Column(String, nullable=True)  # TRUE, FALSE
    quantity_required = Column(Float, default=0.0)
    last_transfusion_date = Column(String, nullable=True)
    expected_next_transfusion_date = Column(String, nullable=True)
    frequency_in_days = Column(Integer, default=0)

    # Relationships
    patient = relationship("User", foreign_keys=[patient_id])
    donations = relationship("Donation", back_populates="bridge")
    outreach_sessions = relationship("OutreachWorkflow", back_populates="bridge")

class Donation(Base):
    __tablename__ = "donations"

    donation_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    bridge_id = Column(String, ForeignKey("bridges.bridge_id"), nullable=True)
    donation_date = Column(String, nullable=True)
    status = Column(String, default="Completed")  # Completed, Scheduled, Cancelled

    # Relationships
    user = relationship("User", back_populates="donations")
    bridge = relationship("Bridge", back_populates="donations")

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
    user_id = Column(String, ForeignKey("users.user_id"), nullable=True)
    hba = Column(Float, nullable=True)
    hba2 = Column(Float, nullable=True)
    hbf = Column(Float, nullable=True)
    classification = Column(String)  # Carrier, Non-Carrier, Further Testing Needed
    raw_ocr_text = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="hplc_reports")

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
    engagement_score = Column(Integer, default=0)  # scale of 1-100
    conversions_count = Column(Integer, default=0)  # converted to HPLC screenings

class OutreachWorkflow(Base):
    __tablename__ = "outreach_workflows"

    session_id = Column(String, primary_key=True, index=True)
    bridge_id = Column(String, ForeignKey("bridges.bridge_id"))
    donor_id = Column(String, ForeignKey("users.user_id"))
    current_step = Column(String, default="WhatsApp")  # WhatsApp, SMS, Voice, Escalated, Finished
    status = Column(String, default="In Progress")  # In Progress, Completed, Failed
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    bridge = relationship("Bridge", back_populates="outreach_sessions")
    donor = relationship("User", foreign_keys=[donor_id])
