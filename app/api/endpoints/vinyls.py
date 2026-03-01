from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io

from app.crud import crud_vinyl
from app.schemas.vinyl import VinylResponse, VinylCreate, VinylUpdate, VinylStatusUpdate, PaginatedVinylResponse
from app.db.database import get_db
from app.core.security import get_current_user

router = APIRouter()

@router.get("/export")
def export_vinyls_csv(
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_user)
):
    """Exporta toda la colección de vinilos como un archivo CSV descargable."""
    items, _ = crud_vinyl.get_vinyls(db, skip=0, limit=100000, sort_by="newest")
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = [
        "ID", "Title", "Artist", "Genre", "Year", "Format", "Condition", 
        "Price", "Status", "Notes", "Catalog Number", "Pressing Country", 
        "Color Variant", "Rating", "Added At"
    ]
    writer.writerow(headers)
    
    for v in items:
        writer.writerow([
            v.id, v.title, v.artist, v.genre, v.year, v.format,
            v.condition or "", v.price or "", v.status, v.notes or "",
            v.catalog_number or "", v.pressing_country or "",
            v.color_variant or "", v.rating or 0,
            v.addedAt.isoformat() if v.addedAt else ""
        ])
        
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=vinyl_collection_backup.csv"}
    )


@router.get("/stats", response_model=Any)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_user)
) -> Any:
    """Retorna las estadísticas globales de la colección para el Dashboard."""
    from app.schemas.vinyl import VinylStats
    stats = crud_vinyl.get_stats(db)
    return VinylStats(**stats)

@router.get("/breakdown", response_model=Any)
def get_collection_breakdown(
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_user)
) -> Any:
    """Retorna distribución por género, formato y década para los charts del Dashboard."""
    return crud_vinyl.get_breakdown(db)

@router.post("/fetch-covers", response_model=Any)
async def fetch_missing_covers(
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_user)
) -> Any:
    """Busca portadas en Discogs para todos los vinilos sin coverUrl y las guarda en la BD."""
    import httpx, os
    DISCOGS_KEY = os.getenv("DISCOGS_CONSUMER_KEY")
    DISCOGS_SECRET = os.getenv("DISCOGS_CONSUMER_SECRET")

    vinyls_without_cover = crud_vinyl.get_vinyls_without_cover(db)
    updated = 0
    failed = 0

    async with httpx.AsyncClient(timeout=10) as client:
        for vinyl in vinyls_without_cover:
            try:
                resp = await client.get(
                    "https://api.discogs.com/database/search",
                    headers={"User-Agent": "VinylDashboardApp/1.0"},
                    params={
                        "release_title": vinyl.title,
                        "artist": vinyl.artist,
                        "type": "release",
                        "format": "Vinyl",
                        "key": DISCOGS_KEY,
                        "secret": DISCOGS_SECRET,
                        "per_page": 1
                    }
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])
                if results and results[0].get("cover_image"):
                    crud_vinyl.update_vinyl_cover(db, vinyl.id, results[0]["cover_image"])
                    updated += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

    return {"updated": updated, "failed": failed, "total": len(vinyls_without_cover)}

@router.get("", response_model=PaginatedVinylResponse)
def read_vinyls(
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    status: str = Query(None, description="Filtrar por 'owned' o 'wishlist'"),
    genre: str = Query(None, description="Filtrar por género"),
    search: str = Query(None, description="Búsqueda de texto en título o artista"),
    sort_by: str = Query("newest", description="Atributo de ordenamiento")
) -> Any:
    """Respuesta con la lista de vinilos, con filtros opcionales."""
    items, total = crud_vinyl.get_vinyls(db, skip=skip, limit=limit, status=status, genre=genre, search=search, sort_by=sort_by)
    return PaginatedVinylResponse(items=items, total=total, skip=skip, limit=limit)

@router.post("", response_model=VinylResponse, status_code=201)
def create_vinyl(
    *,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_user),
    vinyl_in: VinylCreate,
) -> Any:
    """Agrega un nuevo vinilo."""
    vinyl = crud_vinyl.create_vinyl(db=db, vinyl=vinyl_in)
    return vinyl

@router.get("/{vinyl_id}", response_model=VinylResponse)
def read_vinyl(
    vinyl_id: str,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_user),
) -> Any:
    """Busca un vinilo específico por ID."""
    vinyl = crud_vinyl.get_vinyl(db=db, vinyl_id=vinyl_id)
    if not vinyl:
        raise HTTPException(status_code=404, detail="Vinilo no encontrado")
    return vinyl

@router.put("/{vinyl_id}", response_model=VinylResponse)
def update_vinyl(
    *,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_user),
    vinyl_id: str,
    vinyl_in: VinylUpdate,
) -> Any:
    """Actualiza toda la información de un vinilo."""
    vinyl = crud_vinyl.get_vinyl(db=db, vinyl_id=vinyl_id)
    if not vinyl:
        raise HTTPException(status_code=404, detail="Vinilo no encontrado")
    vinyl = crud_vinyl.update_vinyl(db=db, db_vinyl=vinyl, vinyl_in=vinyl_in)
    return vinyl

@router.patch("/{vinyl_id}/status", response_model=VinylResponse)
def update_vinyl_status(
    *,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_user),
    vinyl_id: str,
    status_in: VinylStatusUpdate,
) -> Any:
    """Mueve rápido un disco (Wishlist <-> Owned)."""
    vinyl = crud_vinyl.get_vinyl(db=db, vinyl_id=vinyl_id)
    if not vinyl:
        raise HTTPException(status_code=404, detail="Vinilo no encontrado")
    vinyl = crud_vinyl.update_vinyl_status(db=db, db_vinyl=vinyl, status=status_in.status)
    return vinyl

@router.delete("/{vinyl_id}")
def delete_vinyl(
    *,
    db: Session = Depends(get_db),
    _: Any = Depends(get_current_user),
    vinyl_id: str,
) -> Any:
    """Borra un disco de la BD."""
    vinyl = crud_vinyl.get_vinyl(db=db, vinyl_id=vinyl_id)
    if not vinyl:
        raise HTTPException(status_code=404, detail="Vinilo no encontrado")
    crud_vinyl.delete_vinyl(db=db, db_vinyl=vinyl)
    return {"message": "Vinilo eliminado con éxito"}
