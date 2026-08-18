from pydantic import BaseModel


class Submission(BaseModel):
    title: str
    timestamp: int


class UserSubmissionsResponse(BaseModel):
    username: str
    submissions: list[Submission]


class ErrorResponse(BaseModel):
    code: str
    message: str
