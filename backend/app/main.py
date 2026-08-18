import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.friends import router as friends_router
from app.routes.users import router as users_router


frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]


app = FastAPI(title="LeetRank API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(users_router)
app.include_router(friends_router)
