from typing import Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from random import randrange
from time import sleep

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class APIMessage(BaseModel):
    msg : str

@app.get("/message")
async def message() -> APIMessage:
    sleep(randrange(50, 200)/100)
    return { "msg": "Hello World!" }
