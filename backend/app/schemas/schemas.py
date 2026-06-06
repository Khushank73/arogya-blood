from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any

# --- Patient Schemas ---
class PatientBase(BaseModel):
    name: str
    blood_group: str
    city: Optional[str] = None
    quantity_required: Optional[float] = 1.0
    last_transfusion_date: Optional[str] = None
    expected_next_transfusion_date: Optional[str] = None
    risk_level: Optional[str] = "LOW"

class PatientCreate(PatientBase):
    id: Optional[str] = None  # Auto-generated if not provided

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    blood_group: Optional[str] = None
    city: Optional[str] = None
    quantity_required: Optional[float] = None
    last_transfusion_date: Optional[str] = None
    expected_next_transfusion_date: Optional[str] = None
    risk_level: Optional[str] = None

class PatientResponse(PatientBase):
    id: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)

# --- Donor Schemas ---
class DonorBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    blood_group: str
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    donor_type: Optional[str] = "Regular"
    donations_till_date: Optional[int] = 0
    last_donation_date: Optional[str] = None
    next_eligible_date: Optional[str] = None
    engagement_score: Optional[float] = 0.0
    availability_score: Optional[float] = 0.0
    churn_risk: Optional[float] = 0.0
    active_status: Optional[str] = "Active"

class DonorCreate(DonorBase):
    id: Optional[str] = None

class DonorUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    blood_group: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    donor_type: Optional[str] = None
    donations_till_date: Optional[int] = None
    last_donation_date: Optional[str] = None
    next_eligible_date: Optional[str] = None
    engagement_score: Optional[float] = None
    availability_score: Optional[float] = None
    churn_risk: Optional[float] = None
    active_status: Optional[str] = None

class DonorResponse(DonorBase):
    id: str
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)

# --- Matching Schemas ---
class DonorMatchDetail(BaseModel):
    donor_id: str
    name: str
    blood_group: str
    match_score: float
    distance_km: float
    availability_score: float
    engagement_score: float
    eligibility: str
    relationship_type: Optional[str] = "Emergency"

class MatchingResponse(BaseModel):
    patient_id: str
    recommendations: List[DonorMatchDetail]

# --- Churn & Availability Prediction Schemas ---
class DonorMetric(BaseModel):
    donor_id: str
    name: str
    blood_group: str
    score: float

class ChurnResponse(BaseModel):
    donors: List[DonorMetric]

class AvailabilityResponse(BaseModel):
    donors: List[DonorMetric]

# --- Chatbot Schemas ---
class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[str]

# --- Transfusion Workflow Schemas ---
class TransfusionRequest(BaseModel):
    patient_id: str
    quantity_units: float = 1.0
    required_by_date: Optional[str] = None

class TransfusionWorkflowResponse(BaseModel):
    workflow_id: str
    patient_id: str
    status: str
    current_step: str
    assigned_donor_id: Optional[str] = None
    outreach_sent: bool = False
    response_received: Optional[str] = None
    created_at: str
    updated_at: str
    timeline: List[Dict[str, Any]]

# --- Dashboard & Analytics Schemas ---
class AnalyticsDashboardResponse(BaseModel):
    summary: Dict[str, Any]
    donation_trends: List[Dict[str, Any]]
    blood_group_distribution: List[Dict[str, Any]]
    retention_trends: List[Dict[str, Any]]
    forecasts: Dict[str, Any]
