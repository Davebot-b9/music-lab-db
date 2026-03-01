import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    display_name = Column(String, nullable=True)
    avatar_url = Column(Text, nullable=True)   # base64 data URI or external URL
    created_at = Column(DateTime, default=datetime.utcnow)
