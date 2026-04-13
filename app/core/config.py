from pydantic import BaseSettings


class Settings(BaseSettings):
    DATA_DIR: str = "data"
    GROQ_API_KEY: str = ""


settings = Settings()