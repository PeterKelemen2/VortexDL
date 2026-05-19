import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME = os.getenv("APP_NAME", "Downloader API")
    DEBUG = os.getenv("DEBUG", "false") == "true"

settings = Settings()