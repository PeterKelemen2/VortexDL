from fastapi import FastAPI
from app.api.routes import health

app = FastAPI(title="My Backend")

app.include_router(health.router)