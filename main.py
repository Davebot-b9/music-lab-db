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

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Music Lab API is running. Visit /docs for documentation."}
