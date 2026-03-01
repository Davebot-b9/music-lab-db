from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import api_router
from app.db.database import engine, Base
import app.models.vinyl  # ensure models are imported before creating tables

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Vinyl Dashboard API",
    description="Backend API for managing vinyl collections and wishlists.",
    version="1.0.0"
)

# Enable CORS for the Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Angular dev ports and PyWebview local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.responses import FileResponse

# Include the API router
app.include_router(api_router, prefix="/api")

# Serve the static files from Angular built directory
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Web", "Angular", "music-place-dashboard", "dist", "music-place-dashboard", "browser"))

@app.get("/")
def read_root():
    return FileResponse(os.path.join(frontend_path, "index.csr.html"))

@app.get("/{full_path:path}")
async def serve_angular(full_path: str):
    if full_path.startswith("api/"):
        # Let FastAPI return 404 for unhandled API routes instead of the angular app
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="API route not found")
        
    target_path = os.path.join(frontend_path, full_path)
    if full_path != "" and os.path.exists(target_path) and os.path.isfile(target_path):
        return FileResponse(target_path)
    # Return index.csr.html for Angular routes (client-side routing)
    return FileResponse(os.path.join(frontend_path, "index.csr.html"))
