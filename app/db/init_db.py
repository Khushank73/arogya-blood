import csv
import os
import math
import random
from sqlalchemy.orm import Session
from app.core.database import sync_engine, SessionLocal, Base
from app.models.models import User, Bridge, Donation, HplcCampaign, HplcReport, AwarenessCampaign

def clean_val(val):
    if not val:
        return None
    val = val.strip()
    # Clean PostgreSQL hex representation from string if present
    if val.startswith("\\x"):
        return val[2:]
    if val.lower() == "nan" or val == "":
        return None
    return val

def init_db(db: Session, csv_path: str):
    print("Creating database tables...")
    Base.metadata.create_all(bind=sync_engine)
    
    # Check if database is already populated
    if db.query(User).count() > 0:
        print("Database already populated. Skipping ingestion.")
        return

    print(f"Reading dataset from {csv_path}...")
    if not os.path.exists(csv_path):
        print(f"Dataset not found at {csv_path}. Creating a dummy dataset for testing.")
        # Create a dummy CSV if it's missing (for isolation or tests)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "user_id", "bridge_id", "role", "role_status", "bridge_status", 
                "blood_group", "gender", "latitude", "longitude", "bridge_gender", 
                "bridge_blood_group", "quantity_required", "last_transfusion_date", 
                "expected_next_transfusion_date", "registration_date", "donor_type", 
                "last_contacted_date", "last_donation_date", "next_eligible_date", 
                "donations_till_date", "eligibility_status", "cycle_of_donations", 
                "total_calls", "frequency_in_days", "status_of_bridge", "status", 
                "donated_earlier", "last_bridge_donation_date", "calls_to_donations_ratio", 
                "user_donation_active_status", "inactive_trigger_comment"
            ])
            writer.writerow([
                "user_1", "bridge_1", "Patient", "TRUE", "TRUE", "A Positive", "Male", 
                "17.3922", "78.4602", "Male", "A Positive", "2", "01-05-2026", "01-06-2026", 
                "01-01-2026", "None", "", "", "", "0", "not eligible", "30", "0", "30", "TRUE", 
                "active", "FALSE", "", "0", "Active", ""
            ])
            writer.writerow([
                "user_2", "bridge_1", "Bridge Donor", "TRUE", "TRUE", "A Positive", "Male", 
                "17.3950", "78.4610", "Male", "A Positive", "1", "", "", "01-01-2026", 
                "Regular Donor", "15-05-2026", "15-05-2026", "15-08-2026", "5", "eligible", 
                "90", "1", "90", "TRUE", "active", "TRUE", "15-05-2026", "0.2", "Active", ""
            ])

    users_to_add = {}
    bridges_to_add = {}
    donations_to_add = []

    with open(csv_path, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            u_id = clean_val(row.get("user_id"))
            b_id = clean_val(row.get("bridge_id"))
            
            if not u_id:
                continue

            role = clean_val(row.get("role"))
            bg = clean_val(row.get("blood_group"))
            gender = clean_val(row.get("gender"))
            
            lat_str = clean_val(row.get("latitude"))
            lon_str = clean_val(row.get("longitude"))
            lat = float(lat_str) if lat_str else 17.3922792
            lon = float(lon_str) if lon_str else 78.4602749
            
            don_till_date_str = clean_val(row.get("donations_till_date"))
            don_till_date = int(don_till_date_str) if don_till_date_str else 0
            
            tot_calls_str = clean_val(row.get("total_calls"))
            tot_calls = int(tot_calls_str) if tot_calls_str else 0
            
            freq_days_str = clean_val(row.get("frequency_in_days"))
            freq_days = int(freq_days_str) if freq_days_str else 0
            
            ratio_str = clean_val(row.get("calls_to_donations_ratio"))
            ratio = float(ratio_str) if ratio_str else 0.0
            
            cycle_str = clean_val(row.get("cycle_of_donations"))
            cycle = int(cycle_str) if cycle_str else 0

            # Store user in dict (deduplicate if same user appears in multiple rows)
            if u_id not in users_to_add:
                users_to_add[u_id] = User(
                    user_id=u_id,
                    role=role,
                    role_status=clean_val(row.get("role_status")),
                    blood_group=bg,
                    gender=gender,
                    latitude=lat,
                    longitude=lon,
                    registration_date=clean_val(row.get("registration_date")),
                    donor_type=clean_val(row.get("donor_type")),
                    last_contacted_date=clean_val(row.get("last_contacted_date")),
                    last_donation_date=clean_val(row.get("last_donation_date")),
                    next_eligible_date=clean_val(row.get("next_eligible_date")),
                    donations_till_date=don_till_date,
                    eligibility_status=clean_val(row.get("eligibility_status")),
                    cycle_of_donations=cycle,
                    total_calls=tot_calls,
                    frequency_in_days=freq_days,
                    donated_earlier=clean_val(row.get("donated_earlier")),
                    calls_to_donations_ratio=ratio,
                    user_donation_active_status=clean_val(row.get("user_donation_active_status")) or "Active",
                    inactive_trigger_comment=clean_val(row.get("inactive_trigger_comment"))
                )

            # If user is patient, we capture the bridge properties
            if role == "Patient" and b_id:
                qty_str = clean_val(row.get("quantity_required"))
                qty = float(qty_str) if qty_str else 2.0
                
                bridges_to_add[b_id] = Bridge(
                    bridge_id=b_id,
                    patient_id=u_id,
                    status_of_bridge=clean_val(row.get("status_of_bridge")) or "TRUE",
                    quantity_required=qty,
                    last_transfusion_date=clean_val(row.get("last_transfusion_date")),
                    expected_next_transfusion_date=clean_val(row.get("expected_next_transfusion_date")),
                    frequency_in_days=freq_days
                )
            # If donor is linked to a bridge, check if bridge needs creation
            elif b_id and b_id not in bridges_to_add:
                # Placeholder bridge details (will get filled if patient row exists, or kept as is)
                bridges_to_add[b_id] = Bridge(
                    bridge_id=b_id,
                    patient_id=None,
                    status_of_bridge="TRUE",
                    quantity_required=1.0,
                    last_transfusion_date=clean_val(row.get("last_transfusion_date")),
                    expected_next_transfusion_date=clean_val(row.get("expected_next_transfusion_date")),
                    frequency_in_days=freq_days
                )

            # If user has a last_donation_date, record it as a donation event
            last_don_date = clean_val(row.get("last_donation_date"))
            if last_don_date and role in ["Bridge Donor", "Emergency Donor", "Volunteer"]:
                donations_to_add.append((u_id, b_id, last_don_date))

    print(f"Saving {len(users_to_add)} unique users...")
    db.add_all(list(users_to_add.values()))
    db.commit()

    print(f"Saving {len(bridges_to_add)} unique bridges...")
    db.add_all(list(bridges_to_add.values()))
    db.commit()

    print(f"Saving {len(donations_to_add)} donations...")
    db_donations = []
    for u_id, b_id, don_date in donations_to_add:
        # Validate that the bridge exists in the db first
        actual_bridge_id = b_id if (b_id and b_id in bridges_to_add) else None
        db_donations.append(Donation(
            user_id=u_id,
            bridge_id=actual_bridge_id,
            donation_date=don_date,
            status="Completed"
        ))
    db.add_all(db_donations)
    db.commit()

    # --- Seed Prevention Layer Data (HPLC Campaigns and Reports) ---
    print("Seeding HPLC campaign and report templates...")
    campaigns = [
        HplcCampaign(title="Nizamabad Rural Screening Drive", type="Village", location="Nizamabad", date="12-04-2026", registrations_count=150, screened_count=142, carrier_count=8),
        HplcCampaign(title="VNR VJIET College Screening Camp", type="College", location="Bachupally, Hyderabad", date="02-05-2026", registrations_count=450, screened_count=435, carrier_count=21),
        HplcCampaign(title="Secunderabad High School Campaign", type="School", location="Secunderabad", date="18-05-2026", registrations_count=200, screened_count=195, carrier_count=6),
        HplcCampaign(title="Gachibowli Tech Park Corporate Campaign", type="Corporate", location="Gachibowli, Hyderabad", date="05-06-2026", registrations_count=320, screened_count=310, carrier_count=4)
    ]
    db.add_all(campaigns)
    db.commit()

    # Seed mock HPLC reports for testing analysis & risk features
    # Standard reports
    mock_reports = [
        HplcReport(hba=97.2, hba2=2.4, hbf=0.4, classification="Non-Carrier", recommendations="Patient is healthy and has normal Hb fractions. No further thalassemia testing needed."),
        HplcReport(hba=92.5, hba2=5.2, hbf=2.3, classification="Carrier", recommendations="Elevated HbA2 levels (>3.5%) indicate Beta-Thalassemia Trait/Carrier. Genetic counseling is highly recommended before marriage or planning a family."),
        HplcReport(hba=88.1, hba2=4.9, hbf=7.0, classification="Carrier", recommendations="High HbA2 and elevated HbF. Beta Thalassemia Trait. Ensure partner screening is completed."),
        HplcReport(hba=50.0, hba2=3.0, hbf=47.0, classification="Further Testing Needed", recommendations="Significant HbF elevation. Possible Thalassemia Intermedia or Major. Refer to hematologist immediately for advanced genetic profiling.")
    ]
    db.add_all(mock_reports)
    db.commit()

    # --- Seed Awareness Layer Data (Awareness Campaigns) ---
    print("Seeding awareness campaign statistics...")
    awareness_camps = [
        AwarenessCampaign(title="Understand Thalassemia - Hyderabad Public School", type="School", date="14-03-2026", attendees_count=320, engagement_score=85, conversions_count=25),
        AwarenessCampaign(title="Pre-Marital Screening Campaign - Warangal Villages", type="Village", date="04-04-2026", attendees_count=180, engagement_score=92, conversions_count=45),
        AwarenessCampaign(title="Blood Donation Myths - IIT Hyderabad", type="College", date="28-04-2026", attendees_count=550, engagement_score=78, conversions_count=60),
        AwarenessCampaign(title="Corporate Health Awareness Program - Infosys", type="Corporate", date="20-05-2026", attendees_count=400, engagement_score=80, conversions_count=35)
    ]
    db.add_all(awareness_camps)
    db.commit()

    print("Data ingestion complete!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_db(db, "./Dataset.csv")
    finally:
        db.close()
