from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.services.model_loader import state
from app.services.tea_price_service import load_metrics_mape

app = FastAPI(title="Tea Broker AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    state.load_all()
    load_metrics_mape()


@app.get("/")
def root():
    return {"message": "Tea Broker AI API running"}


@app.get("/startup-status")
def startup_status():
    return state.status()


app.include_router(router, prefix="/api")