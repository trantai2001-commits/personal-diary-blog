import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    db_url = os.getenv("DATABASE_URL")

    # Khi deploy, ưu tiên PostgreSQL
    if db_url:
        # Ép SQLAlchemy dùng driver psycopg 3
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        # Local fallback
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024