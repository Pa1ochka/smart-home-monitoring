# test_db_connection.py
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:admin12345@postgres:5432/smarthome"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.fetchone())