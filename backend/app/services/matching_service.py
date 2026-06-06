import math
import datetime
import logging
from sqlalchemy.orm import Session
from app.models.models import Donor, Patient
from app.ai.availability_model import availability_engine

logger = logging.getLogger("app.services.matching")

# --- Blood Compatibility Map ---
# Key: Donor blood group, Value: List of recipient blood groups they can donate to.
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
    donor_bg = donor_bg.strip().title()
    recipient_bg = recipient_bg.strip().title()
    return recipient_bg in COMPATIBILITY_MAP.get(donor_bg, [])

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Radius of Earth in kilometers
    R = 6371.0
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

class MatchingService:
    @staticmethod
    def get_top_matches(db: Session, patient_id: str, limit: int = 10):
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            logger.warning(f"Patient {patient_id} not found in database for matching.")
            return []

        patient_bg = patient.blood_group
        patient_lat = patient.latitude if hasattr(patient, "latitude") and patient.latitude else 17.3922792
        patient_lon = patient.longitude if hasattr(patient, "longitude") and patient.longitude else 78.4602749
        
        # 1. Fetch potential donors
        all_donors = db.query(Donor).filter(Donor.active_status == "Active").all()
        matched_profiles = []

        baseline = datetime.datetime(2026, 6, 6)

        for d in all_donors:
            # Step 0: Check consent
            if hasattr(d, "consent_given") and d.consent_given is False:
                continue

            # Step 1: Filter blood-compatible donors
            if not is_blood_compatible(d.blood_group, patient_bg):
                continue

            # Step 2: Remove ineligible donors
            # If next_eligible_date is in the future, they are ineligible.
            is_eligible = True
            days_since_last_donation = 180.0
            if d.next_eligible_date:
                try:
                    next_elig = datetime.datetime.strptime(d.next_eligible_date.strip(), "%d-%m-%Y")
                    if next_elig > baseline:
                        is_eligible = False
                except Exception:
                    pass
            
            if d.last_donation_date:
                try:
                    last_don = datetime.datetime.strptime(d.last_donation_date.strip(), "%d-%m-%Y")
                    days_since_last_donation = float(max(0, (baseline - last_don).days))
                except Exception:
                    pass

            if not is_eligible:
                continue

            # Step 3: Calculate distance score
            d_lat = d.latitude if d.latitude else 17.3922792
            d_lon = d.longitude if d.longitude else 78.4602749
            dist_km = haversine_distance(patient_lat, patient_lon, d_lat, d_lon)
            # Normalize distance score: 1.0 at 0km, 0.0 at 50km or further
            distance_score = max(0.0, 1.0 - (dist_km / 50.0))

            # Step 4: Calculate availability score
            # We predict availability score on-the-fly using our model
            avail_score = availability_engine.predict(
                days_since_last_donation=days_since_last_donation,
                donations_till_date=d.donations_till_date,
                engagement_score=d.engagement_score,
                active_status=(d.active_status == "Active")
            )

            # Step 5: Calculate engagement score
            engagement_score = float(d.engagement_score / 100.0)

            # Compatibility score (all compatible donors get 1.0)
            compatibility_score = 1.0
            # Eligibility score (all eligible donors get 1.0)
            eligibility_score = 1.0

            # Check if this donor is mapped as a Care Bridge for this patient
            from app.models.models import DonorPatientMatch
            bridge_match = db.query(DonorPatientMatch).filter(
                DonorPatientMatch.patient_id == patient_id,
                DonorPatientMatch.donor_id == d.id
            ).first()
            
            relationship_type = "Emergency"
            if bridge_match:
                relationship_type = bridge_match.relationship_type or "Bridge"

            # Composite match score:
            # 40% compatibility + 20% eligibility + 20% availability + 10% engagement + 10% distance
            match_score = (
                (compatibility_score * 0.40) +
                (eligibility_score * 0.20) +
                (avail_score * 0.20) +
                (engagement_score * 0.10) +
                (distance_score * 0.10)
            )
            
            # Boost score if they are a dedicated bridge donor to prioritize them
            if relationship_type == "Bridge":
                match_score += 0.05

            match_score = round(max(0.0, min(1.0, match_score)), 3)

            matched_profiles.append({
                "donor_id": d.id,
                "name": d.name,
                "blood_group": d.blood_group,
                "match_score": match_score,
                "distance_km": round(dist_km, 2),
                "availability_score": avail_score,
                "engagement_score": round(engagement_score * 100.0, 1),
                "eligibility": "eligible",
                "relationship_type": relationship_type
            })

        # Sort matches by score descending, then by distance ascending
        matched_profiles.sort(key=lambda x: (-x["match_score"], x["distance_km"]))
        
        # Save matches to db or just return them
        return matched_profiles[:limit]
