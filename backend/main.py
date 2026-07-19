import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import ligands, screen, targets, workflows

app = FastAPI(title="NeuroLab API", version="0.1.0")

app.include_router(targets.router)
app.include_router(ligands.router)
app.include_router(workflows.router)
app.include_router(screen.router)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
