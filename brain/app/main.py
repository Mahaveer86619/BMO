import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.talk import router as talk_router
from app.services.filler import FillerService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    FillerService.load()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.include_router(talk_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
