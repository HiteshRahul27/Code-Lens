from fastapi import FastAPI
from dotenv import load_dotenv
from app.api.routes import router

load_dotenv()

app = FastAPI()
app.include_router(router)