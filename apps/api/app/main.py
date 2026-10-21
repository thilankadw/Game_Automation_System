from fastapi import FastAPI

app = FastAPI(title="Game Automation System API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
