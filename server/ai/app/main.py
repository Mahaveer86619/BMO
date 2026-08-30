from fastapi import FastAPI

from .routes.internal import router as internal_router

app = FastAPI(
    title="BMO AI Service",
    description=(
        "Internal-only — bound to 127.0.0.1, never exposed outside the container. "
        "The Go hub (server/cmd) is the only caller. See server/ai/README.md."
    ),
)
app.include_router(internal_router)
