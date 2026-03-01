import os
import json
import re
import httpx
from fastapi import APIRouter, HTTPException, Query, Depends
from dotenv import load_dotenv
from typing import List, Optional
from pydantic import BaseModel
from google import genai
from app.core.security import get_current_user

load_dotenv()

router = APIRouter()

DISCOGS_KEY = os.getenv("DISCOGS_CONSUMER_KEY")
DISCOGS_SECRET = os.getenv("DISCOGS_CONSUMER_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

@router.get("/discogs/search")
async def search_discogs(
    artist: str = Query(..., min_length=1),
    title: str = Query(..., min_length=1),
    _=Depends(get_current_user)
):
    if not DISCOGS_KEY or not DISCOGS_SECRET:
        raise HTTPException(status_code=500, detail="Discogs API credentials not configured.")
        
    url = "https://api.discogs.com/database/search"
    headers = {
        "User-Agent": "VinylDashboardApp/1.0"
    }
    params = {
        "release_title": title,
        "artist": artist,
        "type": "release",
        "format": "Vinyl", # filter only vinyl records
        "key": DISCOGS_KEY,
        "secret": DISCOGS_SECRET,
        "per_page": 5
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                raise HTTPException(status_code=404, detail="No matching vinyl records found on Discogs.")
                
            # Take the first most relevant result
            best_match = results[0]
            
            # Map to our standard format
            mapped_result = {
                "title": best_match.get("title", ""),
                "year": best_match.get("year", ""),
                "coverUrl": best_match.get("cover_image", ""),
                "genre": best_match.get("genre", [""])[0] if best_match.get("genre") else "",
                "country": best_match.get("country", ""),
                "catalog_number": best_match.get("catno", "")
            }
            
            return mapped_result
            
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Discogs API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ─── Crate Digger ─────────────────────────────────────────────────────────────

class VinylSummary(BaseModel):
    title: str
    artist: str
    genre: Optional[str] = None
    year: Optional[int] = None
    rating: Optional[int] = None

class CrateDiggerRequest(BaseModel):
    vinyls: List[VinylSummary]

@router.post("/crate-digger")
async def get_crate_digger_recommendations(
    request: CrateDiggerRequest,
    _=Depends(get_current_user)
):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured in .env")
    
    if not request.vinyls:
        raise HTTPException(status_code=400, detail="Collection is empty. Add some vinyls first.")

    # Build a human-readable summary of the collection
    collection_lines = []
    for v in request.vinyls:
        rating_str = f", Valoración: {'⭐' * (v.rating or 0)}" if v.rating else ""
        collection_lines.append(f"- {v.artist} — {v.title} ({v.year or 'S/A'}, {v.genre or 'Género desconocido'}{rating_str})")
    
    collection_text = "\n".join(collection_lines)
    
    prompt = f"""Eres un experto coleccionista de discos de vinilo y curador musical con conocimiento enciclopédico de prensados raros, álbumes de culto y joyas ocultas de todos los géneros. Responde SIEMPRE en español.

Esta es la colección actual del coleccionista (discos físicos en su poder):
{collection_text}

Basándote en esta colección, recomienda exactamente 5 discos de vinilo que el coleccionista NO tenga y que serían perfectos para él. Enfócate en joyas ocultas, discos importantes, prensados raros o álbumes esenciales que le puedan faltar.

Para cada recomendación, considera:
- Los estilos musicales y artistas que ya ama
- Los vacíos en su colección por género o década
- Discos con alto valor para coleccionistas o significado cultural
- Discos que amplíen su gusto de forma natural

Devuelve ÚNICAMENTE un array JSON válido con exactamente 5 objetos. Cada objeto debe tener estos campos:
- "artist": string (nombre del artista, puede ser en inglés si así se llama)
- "title": string (título del álbum, puede ser en inglés si así se llama)
- "year": number
- "genre": string
- "reason": string (2-3 oraciones EN ESPAÑOL explicando por qué encaja perfectamente con su colección, siendo específico sobre la conexión con discos que ya tiene)

Formato de ejemplo:
[{{"artist": "...", "title": "...", "year": 1973, "genre": "...", "reason": "..."}}]

Devuelve ÚNICAMENTE el array JSON, sin markdown, sin explicaciones, solo el array."""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt
        )
        
        raw_text = response.text.strip()
        
        # Strip markdown code blocks if present
        raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)
        
        recommendations = json.loads(raw_text)
        
        if not isinstance(recommendations, list):
            raise ValueError("Expected a list from Gemini")
            
        return {"recommendations": recommendations[:5]}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Gemini returned an invalid format. Please try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")


# ─── Cover / Spine Scanner ────────────────────────────────────────────────────

from fastapi import File, UploadFile
from google.genai import types as genai_types

SCAN_PROMPT = """Eres un experto identificador de discos de vinilo. Voy a mostrarte una foto de un disco de vinilo. Responde SIEMPRE en español.
La foto puede mostrar la portada frontal, la contraportada, o la espina (el lomo delgado visible cuando los discos están guardados en el estante).

Identifica el disco de vinilo y devuelve ÚNICAMENTE un objeto JSON válido con estos campos exactos:
{
  "artist": "Nombre del artista o banda",
  "title": "Título del álbum",
  "year": 1970,
  "genre": "Género principal (Rock, Jazz, Pop, Clásica, Electrónica, etc.)",
  "notes": "Nota breve EN ESPAÑOL sobre qué fue visible en la imagen y el nivel de confianza de la identificación"
}

Reglas:
- Usa el nombre oficial exacto del artista y el título del álbum (los nombres propios pueden quedar en su idioma original)
- El campo year debe ser un número entero, no una cadena de texto
- Si no puedes identificar el álbum con certeza, igual proporciona tu mejor estimación y anota la incertidumbre en el campo "notes" en español
- Devuelve ÚNICAMENTE el objeto JSON, sin markdown, sin explicaciones

JSON:"""

@router.post("/scan-cover")
async def scan_vinyl_cover(
    image: UploadFile = File(...),
    _=Depends(get_current_user)
):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured in .env")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    content_type = image.content_type or "image/jpeg"
    if content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {content_type}. Use JPEG, PNG, or WEBP.")

    try:
        image_bytes = await image.read()

        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type=content_type),
                SCAN_PROMPT
            ]
        )

        raw_text = response.text.strip()

        # Strip markdown code blocks if present
        raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)

        result = json.loads(raw_text)

        # Ensure year is an integer
        if "year" in result and result["year"]:
            result["year"] = int(result["year"])

        return result

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Gemini returned an invalid format. Please try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini Vision error: {str(e)}")
