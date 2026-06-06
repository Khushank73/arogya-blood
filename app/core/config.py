import os
from typing import Optional

class Settings:
    PROJECT_NAME: str = "BLOOD WARRIORS AIOS"
    API_V1_STR: str = "/api/v1"
    
    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite+aiosqlite:///./blood_warriors.db"
    )
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL", 
        "sqlite:///./blood_warriors.db"
    )
    
    # AWS Settings (with local mock fallbacks)
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID", None)
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    AWS_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    USE_LOCAL_MOCKS: bool = os.getenv("USE_LOCAL_MOCKS", "TRUE").upper() == "TRUE"
    
    # Bedrock Specific Mocks
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "amazon.titan-text-express-v1")
    
    class Config:
        case_sensitive = True

settings = Settings()
