import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import documents, review, chat

app = FastAPI(title="VeriDoc API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(documents.router)
app.include_router(review.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# When the frontend has been built and copied in alongside the backend
# (see the root Dockerfile), serve it from the same process so the whole
# app runs as one container on one port — needed for single-port hosts
# like Hugging Face Spaces. Mounted last so it never shadows /api routes.
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="frontend")
