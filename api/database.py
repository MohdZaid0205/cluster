import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session

load_dotenv()

# ---------------------------------------------------------
# Database Configuration
# ---------------------------------------------------------
# Abstracts the database layer. Default is local SQLite,
# but can explicitly use MySQL (or Postgres) if defined in env.

DB_TYPE = os.getenv("DB_TYPE", "sqlite")

if DB_TYPE == "mysql":
    # MySQL Configuration
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "cluster_db")
    
    # Needs PyMySQL driver installed: pip install pymysql
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

else:
    # Default SQLite Configuration
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "temp", "db", "research.db")
    
    # Ensure directory exists just in case
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    # check_same_thread necessary for FastAPI + SQLite
    engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def get_session():
    """
    Dependency generator for FastAPI routes to access the unified database.
    """
    with Session(engine) as session:
        yield session
