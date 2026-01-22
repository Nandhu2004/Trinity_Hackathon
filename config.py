import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "super-secure-hackathon-key")
    DEBUG = True
