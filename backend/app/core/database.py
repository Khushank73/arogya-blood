from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Base class for SQLAlchemy models
Base = declarative_base()

# Configure Engine Arguments
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Async Setup
async_engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# Sync Setup (mainly used for seeding and simple operations)
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    connect_args=connect_args,
    echo=False
)
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)

# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
