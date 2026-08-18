from fastapi import FastAPI

from app.routes.users import router as users_router


app = FastAPI(title="LeetRank API")
app.include_router(users_router)
