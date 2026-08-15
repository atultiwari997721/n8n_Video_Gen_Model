import os
from sqlalchemy import create_engine, Column, String, Integer, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./users.db")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    gemini_key = Column(String, nullable=True)
    github_pat = Column(String, nullable=True)
    youtube_token = Column(Text, nullable=True)
    google_client_id = Column(String, nullable=True)
    google_client_secret = Column(String, nullable=True)
    youtube_enabled = Column(Boolean, default=False)
    youtube_hour = Column(Integer, default=12)
    github_enabled = Column(Boolean, default=False)
    github_hour = Column(Integer, default=12)

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    service = Column(String) # 'youtube' or 'github'
    status = Column(String)  # 'success' or 'error'
    message = Column(String)
    link = Column(String, nullable=True)
    timestamp = Column(String) # Stored as string ISO format for simplicity

Base.metadata.create_all(bind=engine)

# Manual migration for existing databases
from sqlalchemy import text
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN google_client_id VARCHAR;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN google_client_secret VARCHAR;"))
        conn.commit()
except Exception:
    pass

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN youtube_enabled BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN youtube_hour INTEGER DEFAULT 12;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN github_enabled BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN github_hour INTEGER DEFAULT 12;"))
        conn.commit()
except Exception:
    pass  # Columns already exist

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
