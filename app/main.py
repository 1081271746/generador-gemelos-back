from fastapi import FastAPI

app = FastAPI(
    title="Negotiation Twin Generator API",
    description="Backend API for the Negotiation Twin Generator.",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Negotiation Twin Generator API is running."
    }