import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            database=os.getenv("DB_NAME", "postgres"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "nancy1234")
        )
    return conn

database_session = get_connection()
cursor = database_session.cursor(cursor_factory=psycopg2.extras.DictCursor)

try:
    cursor.execute("SET search_path TO public;")
except Exception:
    pass