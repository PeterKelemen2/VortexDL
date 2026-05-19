from fastapi import FastAPI
from app.api.routes import health, auth, admin

app = FastAPI(title="Downloader API")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)