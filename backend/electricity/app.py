"""Run the electricity module on its own:
    cd backend
    uvicorn electricity.app:app --reload --port 8002       docs: http://localhost:8001/docs
Later, one combined app can include electricity.api.router next to the electricity and food routers.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import api, auth

app = FastAPI(title="LiveBetter - Electricity module", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(api.router)


@app.get("/health")
def health():
    return {"ok": True, "module": "electricity"}
