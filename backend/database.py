from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sih.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def migrate_db_schema():
    """Ensure newly added columns exist in legacy SQLite databases."""
    if "sqlite" not in DATABASE_URL:
        return
    with engine.connect() as conn:
        # Check and add columns to cases table if missing
        try:
            res = conn.execute(text("PRAGMA table_info(cases)")).fetchall()
            existing_cols = {row[1] for row in res}
            if existing_cols:
                if "doctor_notes" not in existing_cols:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN doctor_notes TEXT"))
                if "attachments" not in existing_cols:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN attachments JSON"))
                if "department" not in existing_cols:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN department VARCHAR"))
                conn.commit()
        except Exception as e:
            print(f"Migration note: {e}")


def get_db():
    """FastAPI dependency — yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

