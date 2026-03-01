import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime
from app.db.database import Base

class Vinyl(Base):
    __tablename__ = "vinyls"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    genre = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    coverUrl = Column(String, nullable=True)
    format = Column(String, nullable=False, default="LP")
    condition = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="owned") # enum: 'owned', 'wishlist'
    notes = Column(String, nullable=True)
    addedAt = Column(DateTime, default=datetime.utcnow)
    
    # New Collector Fields
    pressing_country = Column(String, nullable=True)
    color_variant = Column(String, nullable=True)
    catalog_number = Column(String, nullable=True)
    rating = Column(Integer, nullable=True, default=0)
