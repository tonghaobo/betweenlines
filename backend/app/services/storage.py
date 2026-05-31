import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "chatcoach.db"


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                helpful BOOLEAN NOT NULL,
                analysis_id TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_length INTEGER NOT NULL,
                chat_status TEXT,
                request_duration_ms REAL,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        conn.commit()
    logger.info("Database initialized successfully")


def save_feedback(helpful: bool, analysis_id: str | None = None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (helpful, analysis_id) VALUES (?, ?)",
            (helpful, analysis_id),
        )
        conn.commit()
    logger.info(f"Feedback saved: helpful={helpful}")


def save_analysis_log(
    chat_length: int,
    chat_status: str | None,
    duration_ms: float,
    error: str | None = None,
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO analysis_log (chat_length, chat_status, request_duration_ms, error) VALUES (?, ?, ?, ?)",
            (chat_length, chat_status, duration_ms, error),
        )
        conn.commit()


def get_feedback_stats():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        total = cursor.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        helpful = cursor.execute("SELECT COUNT(*) FROM feedback WHERE helpful = 1").fetchone()[0]
    
    return {
        "total": total,
        "helpful": helpful,
        "helpful_rate": round(helpful / total * 100, 1) if total > 0 else 0,
    }
