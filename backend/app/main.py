"""FastAPI entrypoint for the RFT Wordle backend."""

from fastapi import FastAPI

app = FastAPI(
    title="RFT Wordle API",
    version="0.1.0",
    description="Backend for the RFT Wordle demo (game engine + AI suggestion).",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "rft-wordle-api"}
