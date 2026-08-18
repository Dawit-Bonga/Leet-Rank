from fastapi import FastAPI

from app.routes.friends import router as friends_router
from app.routes.users import router as users_router


app = FastAPI(title="LeetRank API")
app.include_router(users_router)
app.include_router(friends_router)
