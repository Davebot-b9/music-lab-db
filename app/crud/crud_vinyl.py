from sqlalchemy.orm import Session
from app.models.vinyl import Vinyl
from app.schemas.vinyl import VinylCreate, VinylUpdate

def get_vinyl(db: Session, vinyl_id: str):
    return db.query(Vinyl).filter(Vinyl.id == vinyl_id).first()

from sqlalchemy import or_, desc, asc

def get_vinyls(db: Session, skip: int = 0, limit: int = 100, status: str = None, genre: str = None, search: str = None, sort_by: str = "newest"):
    query = db.query(Vinyl)
    
    if status:
        query = query.filter(Vinyl.status == status)
    if genre and genre != 'all':
        query = query.filter(Vinyl.genre == genre)
        
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(Vinyl.title.ilike(search_term), Vinyl.artist.ilike(search_term)))
        
    # Sorting
    if sort_by == 'oldest':
        query = query.order_by(asc(Vinyl.addedAt))
    elif sort_by == 'titleAsc':
        query = query.order_by(asc(Vinyl.title))
    elif sort_by == 'titleDesc':
        query = query.order_by(desc(Vinyl.title))
    elif sort_by == 'artistAsc':
        query = query.order_by(asc(Vinyl.artist))
    elif sort_by == 'yearDesc':
        query = query.order_by(desc(Vinyl.year))
    elif sort_by == 'yearAsc':
        query = query.order_by(asc(Vinyl.year))
    elif sort_by == 'priceDesc':
        query = query.order_by(desc(Vinyl.price))
    elif sort_by == 'priceAsc':
        query = query.order_by(asc(Vinyl.price))
    else: # newest
        query = query.order_by(desc(Vinyl.addedAt))
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return items, total

def create_vinyl(db: Session, vinyl: VinylCreate):
    db_vinyl = Vinyl(**vinyl.model_dump())
    db.add(db_vinyl)
    db.commit()
    db.refresh(db_vinyl)
    return db_vinyl

def update_vinyl(db: Session, db_vinyl: Vinyl, vinyl_in: VinylUpdate):
    update_data = vinyl_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_vinyl, field, value)
    db.add(db_vinyl)
    db.commit()
    db.refresh(db_vinyl)
    return db_vinyl

def update_vinyl_status(db: Session, db_vinyl: Vinyl, status: str):
    db_vinyl.status = status
    db.add(db_vinyl)
    db.commit()
    db.refresh(db_vinyl)
    return db_vinyl

def delete_vinyl(db: Session, db_vinyl: Vinyl):
    db.delete(db_vinyl)
    db.commit()
    return db_vinyl

from sqlalchemy.sql import func

def get_stats(db: Session):
    total_owned = db.query(Vinyl).filter(Vinyl.status == 'owned').count()
    total_wishlist = db.query(Vinyl).filter(Vinyl.status == 'wishlist').count()
    val = db.query(func.sum(Vinyl.price)).filter(Vinyl.status == 'owned').scalar()
    total_value = float(val) if val else 0.0

    latest_vinyl = db.query(Vinyl).filter(Vinyl.status == 'owned').order_by(desc(Vinyl.addedAt)).first()
    latest_title = latest_vinyl.title if latest_vinyl else "Ninguno"

    return {
        "total_owned": total_owned,
        "total_wishlist": total_wishlist,
        "total_value": total_value,
        "latest_addition": latest_title
    }

def get_breakdown(db: Session):
    """Returns genre, format and decade distribution for owned vinyls."""
    owned = db.query(Vinyl).filter(Vinyl.status == 'owned').all()

    genre_map: dict[str, int] = {}
    format_map: dict[str, int] = {}
    decade_map: dict[str, int] = {}

    for v in owned:
        # Genre
        g = v.genre or "Desconocido"
        genre_map[g] = genre_map.get(g, 0) + 1
        # Format
        f = v.format or "LP"
        format_map[f] = format_map.get(f, 0) + 1
        # Decade
        if v.year:
            decade = f"{(v.year // 10) * 10}s"
            decade_map[decade] = decade_map.get(decade, 0) + 1

    def to_sorted(d: dict):
        return sorted([{"label": k, "count": v} for k, v in d.items()], key=lambda x: -x["count"])

    return {
        "by_genre": to_sorted(genre_map),
        "by_format": to_sorted(format_map),
        "by_decade": sorted(
            [{"label": k, "count": v} for k, v in decade_map.items()],
            key=lambda x: x["label"]
        ),
    }

def get_vinyls_without_cover(db: Session):
    """Returns vinyls that have no cover URL and are in the owned collection."""
    return db.query(Vinyl).filter(
        Vinyl.status == 'owned',
        (Vinyl.coverUrl == None) | (Vinyl.coverUrl == '')
    ).all()

def update_vinyl_cover(db: Session, vinyl_id: str, cover_url: str):
    vinyl = db.query(Vinyl).filter(Vinyl.id == vinyl_id).first()
    if vinyl:
        vinyl.coverUrl = cover_url
        db.commit()
