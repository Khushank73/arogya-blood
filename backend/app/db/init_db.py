import csv
import os
import random
import datetime
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import sync_engine, Base
from app.models.models import Donor, Patient, DonorPatientMatch, DonationHistory, OutreachLog, HplcCampaign, HplcReport, AwarenessCampaign

def clean_val(val):
    if not val:
        return None
    val = val.strip()
    if val.startswith("\\x"):
        return val[2:]
    if val.lower() == "nan" or val == "":
        return None
    return val

def init_db(db: Session, csv_path: str):
    print("Creating database tables...")
    Base.metadata.create_all(bind=sync_engine)
    
    # Check if database is already populated
    if db.query(Donor).count() > 0:
        print("Database already populated. Skipping ingestion.")
        return

    print(f"Reading dataset from {csv_path}...")
    if not os.path.exists(csv_path):
        # Resolve to workspace root if relative path doesn't exist immediately
        csv_path = os.path.join(settings.BASE_DIR, "..", "Dataset.csv")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(settings.BASE_DIR, "Dataset.csv")
            
    print(f"Final resolved CSV path: {csv_path}")

    donors_to_add = {}
    patients_to_add = {}
    
    # Sample names list to make mock data look realistic and professional
    first_names = ["Rahul", "Amit", "Priya", "Sneha", "Vikram", "Anjali", "Siddharth", "Neha", "Arjun", "Kiran", "Aditya", "Riya", "Manish", "Divya", "Sanjay", "Kavitha", "Rajesh", "Deepika", "Vijay", "Aishwarya", "Sunil", "Pooja", "Harish", "Swathi", "Ramesh"]
    last_names = ["Sharma", "Verma", "Rao", "Reddy", "Patel", "Nair", "Joshi", "Gupta", "Singh", "Kumar", "Choudhury", "Das", "Mehta", "Iyer", "Pillai", "Deshmukh", "Naidu", "Sen", "Bose", "Mishra", "Pandey", "Grover", "Kapoor", "Vance", "Reddy"]
    
    cities = ["Hyderabad", "Nizamabad", "Warangal", "Karimnagar", "Secunderabad", "Bachupally", "Gachibowli"]

    # Load all rows first to enable mapping
    all_rows = []
    with open(csv_path, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            all_rows.append(row)

    # 1. Store Patients (up to 30)
    patients_in_csv = [r for r in all_rows if clean_val(r.get("role")) == "Patient"]
    target_patients = patients_in_csv[:30]
    
    target_bridge_ids = set()
    for row in target_patients:
        b_id = clean_val(row.get("bridge_id"))
        if b_id:
            target_bridge_ids.add(b_id)

    # 2. Store Donors (prioritize bridge donors, then other active donors)
    bridge_donors = [r for r in all_rows if clean_val(r.get("role")) == "Bridge Donor" and clean_val(r.get("bridge_id")) in target_bridge_ids]
    other_donors = [r for r in all_rows if clean_val(r.get("role")) in ["Emergency Donor", "Volunteer"] and clean_val(r.get("user_donation_active_status")) == "Active"]
    
    # We want at least 120-150 total donors. Let's take all matching bridge donors + up to 80 other active donors
    selected_other_donors = other_donors[:80]
    donors_to_import = bridge_donors + selected_other_donors

    for row in donors_to_import:
        u_id = clean_val(row.get("user_id"))
        if not u_id or u_id in donors_to_add:
            continue
            
        role = clean_val(row.get("role"))
        bg = clean_val(row.get("blood_group")) or "O Positive"
        gender = clean_val(row.get("gender")) or "Male"
        
        lat_str = clean_val(row.get("latitude"))
        lon_str = clean_val(row.get("longitude"))
        lat = float(lat_str) if lat_str else 17.3922792
        lon = float(lon_str) if lon_str else 78.4602749
        
        don_till_date_str = clean_val(row.get("donations_till_date"))
        don_till_date = int(don_till_date_str) if don_till_date_str else 0
        
        active_str = clean_val(row.get("user_donation_active_status")) or "Active"
        active_status = "Active" if active_str.lower() == "active" else "Inactive"
        
        donor_type = clean_val(row.get("donor_type")) or "Regular"
        if donor_type == "None":
            donor_type = "Regular"
            
        last_don_date = clean_val(row.get("last_donation_date"))
        next_elig_date = clean_val(row.get("next_eligible_date"))
        
        # Identify city based on lat/lon
        city = "Hyderabad"
        if lat > 18.5:
            city = "Nizamabad"
        elif lon > 79.5:
            city = "Warangal"
        elif lat > 18.0:
            city = "Karimnagar"

        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        phone = f"+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}"
        email = f"{name.lower().replace(' ', '_')}@example.com"
        age = random.randint(18, 55)
        
        engagement_score = round(random.uniform(40.0, 95.0), 1)
        availability_score = round(random.uniform(0.3, 0.95), 2)
        churn_risk = round(random.uniform(0.05, 0.50), 2)
        
        donors_to_add[u_id] = Donor(
            id=u_id,
            name=name,
            phone=phone,
            email=email,
            blood_group=bg,
            city=city,
            latitude=lat,
            longitude=lon,
            age=age,
            gender=gender,
            donor_type=donor_type,
            donations_till_date=don_till_date,
            last_donation_date=last_don_date,
            next_eligible_date=next_elig_date,
            engagement_score=engagement_score,
            availability_score=availability_score,
            churn_risk=churn_risk,
            active_status=active_status,
            consent_given=True
        )

    for row in target_patients:
        u_id = clean_val(row.get("user_id"))
        if not u_id or u_id in patients_to_add:
            continue
            
        bg = clean_val(row.get("blood_group")) or "O Positive"
        qty_str = clean_val(row.get("quantity_required"))
        qty = float(qty_str) if qty_str else 1.5
        
        last_trans_date = clean_val(row.get("last_transfusion_date"))
        next_trans_date = clean_val(row.get("expected_next_transfusion_date"))
        
        risk = "LOW"
        if qty >= 2.0 or random.random() > 0.7:
            risk = "HIGH"
        elif qty >= 1.5:
            risk = "MEDIUM"

        lat_str = clean_val(row.get("latitude"))
        lon_str = clean_val(row.get("longitude"))
        lat = float(lat_str) if lat_str else 17.3922792
        lon = float(lon_str) if lon_str else 78.4602749

        # Identify city based on lat/lon
        city = "Hyderabad"
        if lat > 18.5:
            city = "Nizamabad"
        elif lon > 79.5:
            city = "Warangal"
        elif lat > 18.0:
            city = "Karimnagar"

        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        patients_to_add[u_id] = Patient(
            id=u_id,
            name=name,
            blood_group=bg,
            city=city,
            quantity_required=qty,
            last_transfusion_date=last_trans_date,
            expected_next_transfusion_date=next_trans_date,
            risk_level=risk
        )

    # Pad donors and patients if they are below target counts to ensure exact specifications
    while len(donors_to_add) < 110:
        d_id = f"donor-mock-{random.randint(10000, 99999)}"
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        phone = f"+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}"
        bg = random.choice(["O Positive", "A Positive", "B Positive", "AB Positive", "O Negative", "A Negative"])
        city = random.choice(cities)
        donors_to_add[d_id] = Donor(
            id=d_id,
            name=name,
            phone=phone,
            email=f"{name.lower().replace(' ', '_')}@example.com",
            blood_group=bg,
            city=city,
            latitude=17.39 + random.uniform(-0.1, 0.1),
            longitude=78.46 + random.uniform(-0.1, 0.1),
            age=random.randint(20, 50),
            gender=random.choice(["Male", "Female"]),
            donor_type=random.choice(["Regular", "One-Time"]),
            donations_till_date=random.randint(1, 10),
            last_donation_date="12-03-2026",
            next_eligible_date="12-06-2026",
            engagement_score=round(random.uniform(40.0, 90.0), 1),
            availability_score=round(random.uniform(0.3, 0.9), 2),
            churn_risk=round(random.uniform(0.1, 0.5), 2),
            active_status="Active",
            consent_given=True
        )

    while len(patients_to_add) < 26:
        p_id = f"patient-mock-{random.randint(10000, 99999)}"
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        bg = random.choice(["O Positive", "A Positive", "B Positive", "AB Positive", "O Negative"])
        city = random.choice(cities)
        patients_to_add[p_id] = Patient(
            id=p_id,
            name=name,
            blood_group=bg,
            city=city,
            quantity_required=round(random.uniform(1.0, 2.5), 1),
            last_transfusion_date="15-05-2026",
            expected_next_transfusion_date="05-06-2026",
            risk_level=random.choice(["LOW", "MEDIUM", "HIGH"])
        )

    print(f"Saving {len(donors_to_add)} donors to db...")
    db.add_all(list(donors_to_add.values()))
    db.commit()

    print(f"Saving {len(patients_to_add)} patients to db...")
    db.add_all(list(patients_to_add.values()))
    db.commit()

    # Seed mapped donor-patient relations
    print("Saving seeded Care Bridge matches to db...")
    bridge_matches = []
    for p_row in target_patients:
        p_id = clean_val(p_row.get("user_id"))
        p_bridge_id = clean_val(p_row.get("bridge_id"))
        if not p_id or not p_bridge_id or p_id not in patients_to_add:
            continue
        
        # Find all donors who match this bridge_id in donors_to_add
        for d_row in bridge_donors:
            d_id = clean_val(d_row.get("user_id"))
            d_bridge_id = clean_val(d_row.get("bridge_id"))
            if d_id and d_bridge_id == p_bridge_id and d_id in donors_to_add:
                bridge_matches.append(DonorPatientMatch(
                    patient_id=p_id,
                    donor_id=d_id,
                    match_score=0.95,
                    relationship_type="Bridge"
                ))
    db.add_all(bridge_matches)
    db.commit()
    print(f"Saved {len(bridge_matches)} Care Bridge donor-patient matches.")

    # Generate 500+ Donation History logs
    print("Generating 500+ donation records...")
    donors_list = list(donors_to_add.values())
    patients_list = list(patients_to_add.values())
    
    donations_history = []
    base_date = datetime.datetime(2025, 6, 6)
    
    for _ in range(520):
        donor = random.choice(donors_list)
        patient = random.choice(patients_list)
        
        # Simple date calculation over the past year
        days_ago = random.randint(1, 365)
        don_date = (base_date + datetime.timedelta(days=days_ago)).strftime("%d-%m-%Y")
        
        status = random.choice(["Completed", "Completed", "Completed", "Cancelled"])
        notes = "Successful donation" if status == "Completed" else "Donor unavailable"
        
        donations_history.append(DonationHistory(
            donor_id=donor.id,
            patient_id=patient.id,
            donation_date=don_date,
            status=status,
            notes=notes
        ))
        
    db.add_all(donations_history)
    db.commit()
    print(f"Saved {len(donations_history)} donation records.")

    # Generate initial outreach logs
    print("Generating initial outreach logs...")
    outreaches = []
    for _ in range(50):
        donor = random.choice(donors_list)
        status = random.choice(["Accepted", "Declined", "No Response"])
        outreaches.append(OutreachLog(
            donor_id=donor.id,
            message="Hi, emergency blood bridge requires your A Positive donation. Are you available?",
            response="Yes, I can donate" if status == "Accepted" else "Sorry, out of town" if status == "Declined" else None,
            response_status=status
        ))
    db.add_all(outreaches)
    db.commit()

    # --- Seed Prevention Layer Data (HPLC Campaigns and Reports) ---
    print("Seeding HPLC campaigns and reports...")
    campaigns = [
        HplcCampaign(title="Nizamabad Rural Screening Drive", type="Village", location="Nizamabad", date="12-04-2026", registrations_count=150, screened_count=142, carrier_count=8),
        HplcCampaign(title="VNR VJIET College Screening Camp", type="College", location="Bachupally, Hyderabad", date="02-05-2026", registrations_count=450, screened_count=435, carrier_count=21),
        HplcCampaign(title="Secunderabad High School Campaign", type="School", location="Secunderabad", date="18-05-2026", registrations_count=200, screened_count=195, carrier_count=6),
        HplcCampaign(title="Gachibowli Tech Park Corporate Campaign", type="Corporate", location="Gachibowli, Hyderabad", date="05-06-2026", registrations_count=320, screened_count=310, carrier_count=4)
    ]
    db.add_all(campaigns)
    db.commit()

    mock_reports = [
        HplcReport(hba=97.2, hba2=2.4, hbf=0.4, classification="Non-Carrier", recommendations="Patient is healthy and has normal Hb fractions. No further thalassemia testing needed."),
        HplcReport(hba=92.5, hba2=5.2, hbf=2.3, classification="Carrier", recommendations="Elevated HbA2 levels (>3.5%) indicate Beta-Thalassemia Trait/Carrier. Genetic counseling is highly recommended before marriage or planning a family."),
        HplcReport(hba=88.1, hba2=4.9, hbf=7.0, classification="Carrier", recommendations="High HbA2 and elevated HbF. Beta Thalassemia Trait. Ensure partner screening is completed."),
        HplcReport(hba=50.0, hba2=3.0, hbf=47.0, classification="Further Testing Needed", recommendations="Significant HbF elevation. Possible Thalassemia Intermedia or Major. Refer to hematologist immediately for advanced genetic profiling.")
    ]
    db.add_all(mock_reports)
    db.commit()

    awareness_camps = [
        AwarenessCampaign(title="Understand Thalassemia - Hyderabad Public School", type="School", date="14-03-2026", attendees_count=320, engagement_score=85, conversions_count=25),
        AwarenessCampaign(title="Pre-Marital Screening Campaign - Warangal Villages", type="Village", date="04-04-2026", attendees_count=180, engagement_score=92, conversions_count=45),
        AwarenessCampaign(title="Blood Donation Myths - IIT Hyderabad", type="College", date="28-04-2026", attendees_count=550, engagement_score=78, conversions_count=60),
        AwarenessCampaign(title="Corporate Health Awareness Program - Infosys", type="Corporate", date="20-05-2026", attendees_count=400, engagement_score=80, conversions_count=35)
    ]
    db.add_all(awareness_camps)
    db.commit()

    print("Data ingestion and mock seeding complete!")

if __name__ == "__main__":
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        init_db(db, "./Dataset.csv")
    finally:
        db.close()
