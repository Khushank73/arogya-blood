import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.ai.availability_model import availability_engine
from app.ai.churn_model import churn_engine
from app.api.endpoints import router as api_router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Blood Warriors AI - Care Coordination & Thalassemia Support Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    logger.info("Starting up Blood Warriors AI Backend...")
    
    # 1. Ingest Database data
    db = SessionLocal()
    csv_path = os.path.join(settings.BASE_DIR, "..", "Dataset.csv")
    if not os.path.exists(csv_path):
        csv_path = os.path.join(settings.BASE_DIR, "Dataset.csv")
    try:
        init_db(db, csv_path)
    except Exception as e:
        logger.error(f"Failed to seed database on startup: {e}")
    finally:
        db.close()

    # 2. Train predictive engines if not already cached
    try:
        if not availability_engine.load_model():
            availability_engine.train(csv_path)
            availability_engine.load_model()
            
        if not churn_engine.load_model():
            churn_engine.train(csv_path)
            churn_engine.load_model()
    except Exception as e:
        logger.error(f"Error training predictive models on startup: {e}")

    # 3. Dynamic alignment of ADMIN_PHONE_NUMBER to the top compatible donor for demo purposes
    db = SessionLocal()
    try:
        from app.models.models import Donor, Patient
        from app.services.matching_service import MatchingService
        from app.services.notification_service import NotificationService
        
        admin_phone = os.getenv("ADMIN_PHONE_NUMBER")
        if admin_phone and "99999" not in admin_phone:
            cleaned_phone = NotificationService._clean_phone(admin_phone)
            
            # Find a patient first to run matching
            patient = db.query(Patient).first()
            if patient:
                matches = MatchingService.get_top_matches(db, patient.id, limit=3)
                if matches:
                    top_donor_id = matches[0]["donor_id"]
                    top_donor = db.query(Donor).filter(Donor.id == top_donor_id).first()
                    if top_donor:
                        top_donor.phone = cleaned_phone
                        db.commit()
                        logger.info(f"DEMO ALIGNMENT: Mapped ADMIN_PHONE_NUMBER '{cleaned_phone}' to top donor '{top_donor.name}' (ID: {top_donor.id}) to show in demo.")
    except Exception as de:
        logger.error(f"Failed to align demo phone number on startup: {de}")
    finally:
        db.close()

# Register API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "api_docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
