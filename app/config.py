import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "mysql+pymysql://root:@localhost:3306/livestock_tracker"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
