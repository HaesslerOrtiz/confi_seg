# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routers import login
from backend.routers import projects
from backend.routers import projects
import os

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #revisar en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluye rutas API
app.include_router(login.router)
app.include_router(projects.router)
app.include_router(projects.router)

# Frontend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
front_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
app.mount("/", StaticFiles(directory=front_dir, html=True), name="frontend")