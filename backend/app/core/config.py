import os
from typing import Optional

class Settings:
    PROJECT_NAME: str = "Blood Warriors AI"
    API_V1_STR: str = "/api/v1"
    
    # CORS Configuration
    CORS_ORIGINS: list = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",") if origin.strip()]
    
    # Database Configuration (supports absolute paths to avoid working directory errors)
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_PATH: str = os.path.join(BASE_DIR, "blood_warriors.db")
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite+aiosqlite:///{DB_PATH}"
    )
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL", 
        f"sqlite:///{DB_PATH}"
    )
    
    # AWS Settings (with local mock fallbacks)
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID", None)
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY", None)
    AWS_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    USE_LOCAL_MOCKS: bool = os.getenv("USE_LOCAL_MOCKS", "TRUE").upper() == "TRUE"
    
    # Bedrock Specific Settings
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "amazon.titan-text-express-v1")
    
    # OpenAI Settings (for vector embeddings or assistant models if preferred)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)

    class Config:
        case_sensitive = True

settings = Settings()
