import os
from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./users.db")

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

Base.metadata.create_all(bind=engine)

# Manual migration for existing databases
from sqlalchemy import text
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN google_client_id VARCHAR;"))
        conn.execute(text("ALTER TABLE users ADD COLUMN google_client_secret VARCHAR;"))
        conn.commit()
except Exception:
    pass  # Columns already exist

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
