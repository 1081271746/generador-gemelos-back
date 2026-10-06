from fastapi import FastAPI
from app.routers.auth import router as auth_router
from app.routers.scenarios import router as scenarios_router

app = FastAPI(
    title="Negotiation Twin Generator API",
    description="Backend API for the Negotiation Twin Generator.",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(scenarios_router)

@app.get("/")
def root():
    return {
        "message": "Negotiation Twin Generator API is running."
    }