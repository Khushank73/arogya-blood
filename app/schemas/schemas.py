from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# --- Base Models ---
class UserBase(BaseModel):
    user_id: str
    role: str
    blood_group: Optional[str] = None
    gender: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    donations_till_date: int = 0
    eligibility_status: Optional[str] = None
    total_calls: int = 0
    frequency_in_days: int = 0
    calls_to_donations_ratio: float = 0.0
    user_donation_active_status: Optional[str] = "Active"

# --- Care Schemas ---
class DonorAvailabilityResponse(BaseModel):
    user_id: str
    availability_probability: float
    eligibility_status: str

class DonorRankResponse(BaseModel):
    user_id: str
    blood_group: str
    availability_probability: float
    eligibility_status: str
    distance_km: float
    total_calls: int
    donations_till_date: int
    score: float

class RankedDonorsResponse(BaseModel):
    donors: List[DonorRankResponse]

class BridgeHealthResponse(BaseModel):
    bridge_id: str
    health_score: int
    risk: str
    active_donors_count: int
    eligible_donors_count: int
    donation_completion_rate: float
    donor_response_rate: float

class ChurnRiskResponse(BaseModel):
    user_id: str
    churn_probability: float
    risk_level: str
    retention_action: str

class DemandForecastRegion(BaseModel):
    region_centroid: List[float]
    shortage_score: float
    predicted_units_required: float
    active_donors_available: int
    risk_level: str

class DemandForecastResponse(BaseModel):
    days_ahead: int
    forecasted_shortages: Dict[str, float]
    hotspot_regions: List[DemandForecastRegion]

class OutreachStartRequest(BaseModel):
    bridge_id: str
    donor_id: Optional[str] = None

class OutreachStartResponse(BaseModel):
    session_id: str
    bridge_id: str
    donor_id: str
    current_step: str
    status: str

class OutreachStatusResponse(BaseModel):
    session_id: str
    bridge_id: str
    donor_id: str
    current_step: str
    status: str
    updated_at: str

# --- Prevention Schemas ---
class CampaignBase(BaseModel):
    title: str
    type: str  # Village, School, College, Corporate
    location: str
    date: str
    registrations_count: int = 0
    screened_count: int = 0
    carrier_count: int = 0

class CampaignResponse(CampaignBase):
    campaign_id: int
    class Config:
        from_attributes = True

class HplcReportResponse(BaseModel):
    report_id: int
    user_id: Optional[str] = None
    hba: Optional[float] = None
    hba2: Optional[float] = None
    hbf: Optional[float] = None
    classification: str
    recommendations: Optional[str] = None
    class Config:
        from_attributes = True

class GeneticRiskRequest(BaseModel):
    partner1_report_id: int
    partner2_report_id: int

class GeneticRiskResponse(BaseModel):
    risk_category: str
    counseling_recommendations: str
    awareness_material: str

class HeatmapRegion(BaseModel):
    district: str
    latitude: float
    longitude: float
    risk_score: float
    carrier_density: float
    screening_coverage: float

class HeatmapResponse(BaseModel):
    regions: List[HeatmapRegion]

# --- Awareness Schemas ---
class GenerateContentRequest(BaseModel):
    type: str  # WhatsApp, Poster, Social Media
    audience: str
    language: str

class GenerateContentResponse(BaseModel):
    content_text: str
    suggested_visuals: str
    campaign_type: str
    language: str

class AwarenessAnalyticsResponse(BaseModel):
    reach: int
    engagement_rate: float
    screening_conversions: int
    volunteer_signups: int

# --- Copilot Schemas ---
class CopilotChatRequest(BaseModel):
    user_id: str
    message: str

class CopilotChatResponse(BaseModel):
    user_id: str
    response: str
    language: str
    preferred_channel: str

# --- Admin Command Center ---
class AdminAlert(BaseModel):
    alert_id: str
    type: str  # Bridge Health, Churn, Shortage
    source_id: str
    message: str
    severity: str

class AdminAlertsResponse(BaseModel):
    alerts: List[AdminAlert]

class AdminRecommendationsResponse(BaseModel):
    recommendations: List[str]

# --- Dashboard Schemas ---
class DashboardOverviewResponse(BaseModel):
    active_patients: int
    active_donors: int
    active_bridges: int
    people_screened: int
    awareness_reach: int
    upcoming_donations: int

class DashboardCareResponse(BaseModel):
    bridges: List[Dict[str, Any]]
    demand_trends: Dict[str, List[float]]

class DashboardPreventionResponse(BaseModel):
    screenings_count: int
    carrier_rate: float
    district_coverage: Dict[str, float]

class DashboardAwarenessResponse(BaseModel):
    events_count: int
    attendees: int
    conversion_rate: float

class DashboardPredictionsResponse(BaseModel):
    predicted_shortages: Dict[str, float]
    donor_retention_risk: float
