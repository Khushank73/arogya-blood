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
