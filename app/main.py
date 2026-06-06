import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import SessionLocal
from app.db.init_db import init_db
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
    description="AI Operating System for Blood Warriors - Care, Prevention, Awareness",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Set CORS middleware rules
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Event
@app.on_event("startup")
def startup_event():
    logger.info("Initializing Blood Warriors AIOS...")
    
    # Auto-run DB Seeding
    db = SessionLocal()
    try:
        csv_path = "./Dataset.csv"
        # Seed the database from CSV if not already seeded
        init_db(db, csv_path)
    except Exception as e:
        logger.error(f"Error seeding database on startup: {e}")
    finally:
        db.close()

# Register Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "pillars": ["Care", "Prevention", "Awareness"],
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    # Local run helper
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
