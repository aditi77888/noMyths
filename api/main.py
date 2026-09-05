"""FastAPI application entry point."""
from fastapi import FastAPI

app = FastAPI(title="noMyths API", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "healthy"}
