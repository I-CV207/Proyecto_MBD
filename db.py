from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine("sqlite:///transacciones.db")

def get_connection():
    return engine.connect()

def ensure_user(conn, username):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        );
    """))
    user_row = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).fetchone()
    if not user_row:
        conn.execute(text("INSERT INTO users (username) VALUES (:u)"), {"u": username})
        user_row = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).fetchone()
    return user_row[0]

def ensure_transacciones_table(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS transacciones (
            ID INTEGER PRIMARY KEY,
            Fecha TEXT,
            Categoría TEXT,
            Cuenta TEXT,
            Monto REAL,
            user_id INTEGER
        );
    """))

def get_user_transacciones(user_id):
    with get_connection() as conn:
        df = pd.read_sql(f"SELECT * FROM transacciones WHERE user_id = {user_id}", conn)
        return df

def guardar_transacciones(df):
    df.to_sql("transacciones", engine, if_exists="replace", index=False)
