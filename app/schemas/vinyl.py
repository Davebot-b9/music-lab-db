from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VinylBase(BaseModel):
    title: str
    artist: str
    genre: str
    year: int
    coverUrl: Optional[str] = None
    format: str = "LP"
    condition: Optional[str] = None
    price: Optional[float] = None
    status: str = "owned"
    notes: Optional[str] = None
    
    # New Collector Fields
    pressing_country: Optional[str] = None
    color_variant: Optional[str] = None
    catalog_number: Optional[str] = None
    rating: Optional[int] = 0

class VinylCreate(VinylBase):
    pass

class VinylUpdate(VinylBase):
    pass

class VinylStatusUpdate(BaseModel):
    status: str

class VinylResponse(VinylBase):
    id: str
    addedAt: datetime

    class Config:
        from_attributes = True # Allow Pydantic to read data from SQLAlchemy ORM models

class PaginatedVinylResponse(BaseModel):
    items: list[VinylResponse]
    total: int
    skip: int
    limit: int

class VinylStats(BaseModel):
    total_owned: int
    total_wishlist: int
    total_value: float
    latest_addition: str = None
