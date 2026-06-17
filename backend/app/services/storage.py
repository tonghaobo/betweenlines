import sqlite3
import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "betweenlines.db"


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
                reason TEXT DEFAULT '',
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # 为旧表添加缺失列（兼容已有数据库）
        try:
            cursor.execute("ALTER TABLE feedback ADD COLUMN reason TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE feedback ADD COLUMN comment TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_length INTEGER NOT NULL,
                chat_status TEXT,
                relationship_type TEXT DEFAULT 'romantic',
                request_duration_ms REAL,
                error TEXT,
                turning_point_detected BOOLEAN DEFAULT 0,
                turning_point_confidence REAL DEFAULT 0,
                features_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        try:
            cursor.execute("ALTER TABLE analysis_log ADD COLUMN relationship_type TEXT DEFAULT 'romantic'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE analysis_log ADD COLUMN turning_point_detected BOOLEAN DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE analysis_log ADD COLUMN turning_point_confidence REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE analysis_log ADD COLUMN features_json TEXT")
        except sqlite3.OperationalError:
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outcome (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT,
                reply_used TEXT,
                outcome TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT NOT NULL,
                review_status TEXT,
                advice_effective TEXT,
                new_chat_length INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER NOT NULL,
                conversation_stage TEXT DEFAULT '',
                other_style TEXT DEFAULT '',
                user_issue TEXT DEFAULT '',
                label_source TEXT DEFAULT 'rule',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_tags_analysis_id
                ON analysis_tags(analysis_id)
            """)
        except sqlite3.OperationalError:
            pass
        
        # Events table for analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                anonymous_user_id TEXT NOT NULL,
                event_name TEXT NOT NULL,
                properties TEXT,
                session_id TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        # Indexes for analytics queries
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_user_created_at
                ON events(anonymous_user_id, created_at)
            """)
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_event_name
                ON events(event_name)
            """)
        except sqlite3.OperationalError:
            pass
        
        # Share rewards table (V1.2)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS share_rewards (
                id TEXT PRIMARY KEY,
                anonymous_user_id TEXT NOT NULL,
                reward_date TEXT NOT NULL,
                reward_type TEXT NOT NULL,
                reward_count INTEGER DEFAULT 1,
                share_hash TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_share_rewards_user_date
                ON share_rewards(anonymous_user_id, reward_date)
            """)
        except sqlite3.OperationalError:
            pass

        # Feedback rewards table (V1.3)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_rewards (
                id TEXT PRIMARY KEY,
                anonymous_user_id TEXT NOT NULL,
                reward_date TEXT NOT NULL,
                reward_count INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Good cases table — stores high-quality analysis examples for few-shot prompting
        # NOTE: Stores only extracted features (not raw chat content) per privacy policy.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS good_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_hash TEXT NOT NULL,
                total_messages INTEGER NOT NULL,
                total_rounds INTEGER NOT NULL,
                user_msgs INTEGER NOT NULL,
                other_msgs INTEGER NOT NULL,
                avg_user_len REAL NOT NULL,
                avg_other_len REAL NOT NULL,
                other_question_ratio REAL NOT NULL,
                notable_patterns TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                language TEXT DEFAULT 'zh',
                quality_reason TEXT DEFAULT '',
                other_emoji_count INTEGER DEFAULT 0,
                user_emoji_count INTEGER DEFAULT 0,
                other_short_ratio REAL DEFAULT 0,
                sentiment_pos INTEGER DEFAULT 0,
                sentiment_neg INTEGER DEFAULT 0,
                topic_coherence REAL DEFAULT 0,
                user_question_ratio REAL DEFAULT 0,
                user_solution_ratio REAL DEFAULT 0,
                user_closing_ratio REAL DEFAULT 0,
                safe_zone_ratio REAL DEFAULT 0,
                max_emoji_relay INTEGER DEFAULT 0,
                usage_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # Migrate old good_cases: add feature columns if missing
        for col_def in [
            ("feature_hash", "TEXT NOT NULL DEFAULT ''"),
            ("total_messages", "INTEGER NOT NULL DEFAULT 0"),
            ("total_rounds", "INTEGER NOT NULL DEFAULT 0"),
            ("user_msgs", "INTEGER NOT NULL DEFAULT 0"),
            ("other_msgs", "INTEGER NOT NULL DEFAULT 0"),
            ("avg_user_len", "REAL NOT NULL DEFAULT 0"),
            ("avg_other_len", "REAL NOT NULL DEFAULT 0"),
            ("other_question_ratio", "REAL NOT NULL DEFAULT 0"),
            ("notable_patterns", "TEXT NOT NULL DEFAULT ''"),
            ("quality_reason", "TEXT DEFAULT ''"),
            ("other_emoji_count", "INTEGER DEFAULT 0"),
            ("user_emoji_count", "INTEGER DEFAULT 0"),
            ("other_short_ratio", "REAL DEFAULT 0"),
            ("sentiment_pos", "INTEGER DEFAULT 0"),
            ("sentiment_neg", "INTEGER DEFAULT 0"),
            ("topic_coherence", "REAL DEFAULT 0"),
            ("user_question_ratio", "REAL DEFAULT 0"),
            ("user_solution_ratio", "REAL DEFAULT 0"),
            ("user_closing_ratio", "REAL DEFAULT 0"),
            ("safe_zone_ratio", "REAL DEFAULT 0"),
            ("max_emoji_relay", "INTEGER DEFAULT 0"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE good_cases ADD COLUMN {col_def[0]} {col_def[1]}")
            except sqlite3.OperationalError:
                pass
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_good_cases_relationship
                ON good_cases(relationship_type, language)
            """)
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_rewards_user_date
                ON feedback_rewards(anonymous_user_id, reward_date)
            """)
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
    logger.info("Database initialized successfully")


def _ensure_daily_usage_table():
    """Ensure daily_usage table exists (called lazily)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                user_key TEXT NOT NULL,
                usage_date TEXT NOT NULL,
                analysis_count INTEGER NOT NULL DEFAULT 0,
                screenshot_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_key, usage_date)
            )
        """)
        # Migrate: add usage_records table (anonymous_user_id based)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_records (
                anonymous_user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                text_analysis_count INTEGER NOT NULL DEFAULT 0,
                image_analysis_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (anonymous_user_id, date)
            )
        """)
        conn.commit()


_ensure_daily_usage_table()


def get_daily_usage(anonymous_user_id: str) -> dict:
    """Get today's usage counts for a user. Returns {analysis_count, screenshot_count}."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Try usage_records table first (new system)
        row = cursor.execute(
            "SELECT text_analysis_count, image_analysis_count FROM usage_records WHERE anonymous_user_id = ? AND date = ?",
            (anonymous_user_id, today),
        ).fetchone()

    if row:
        return {"analysis_count": row[0], "screenshot_count": row[1]}
    return {"analysis_count": 0, "screenshot_count": 0}


def increment_daily_usage(anonymous_user_id: str, usage_type: str) -> int:
    """Increment today's usage count. usage_type: 'analysis' or 'screenshot'. Returns new count."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    column = "text_analysis_count" if usage_type == "analysis" else "image_analysis_count"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Upsert: insert if not exists, otherwise increment
        cursor.execute(
            f"INSERT INTO usage_records (anonymous_user_id, date, {column}) VALUES (?, ?, 1) "
            f"ON CONFLICT(anonymous_user_id, date) DO UPDATE SET {column} = {column} + 1",
            (anonymous_user_id, today),
        )
        conn.commit()

        row = cursor.execute(
            f"SELECT {column} FROM usage_records WHERE anonymous_user_id = ? AND date = ?",
            (anonymous_user_id, today),
        ).fetchone()

    return row[0] if row else 1


def decrement_daily_usage(anonymous_user_id: str, usage_type: str) -> int:
    """Decrement today's usage count (undo on failure). usage_type: 'analysis' or 'screenshot'. Returns new count."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    column = "text_analysis_count" if usage_type == "analysis" else "image_analysis_count"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE usage_records SET {column} = MAX(0, {column} - 1) "
            f"WHERE anonymous_user_id = ? AND date = ?",
            (anonymous_user_id, today),
        )
        conn.commit()

        row = cursor.execute(
            f"SELECT {column} FROM usage_records WHERE anonymous_user_id = ? AND date = ?",
            (anonymous_user_id, today),
        ).fetchone()

    return row[0] if row else 0


def save_feedback(helpful: bool, analysis_id: str | None = None, reason: str = "", comment: str = ""):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (helpful, analysis_id, reason, comment) VALUES (?, ?, ?, ?)",
            (helpful, analysis_id, reason, comment),
        )
        conn.commit()
    logger.info(f"Feedback saved: helpful={helpful}")


def save_analysis_log(
    chat_length: int,
    chat_status: str | None,
    duration_ms: float,
    error: str | None = None,
    relationship_type: str | None = None,
    turning_point_detected: bool | None = None,
    turning_point_confidence: float | None = None,
    features_json: str | None = None,
) -> int | None:
    """Save analysis log. Returns the auto-increment ID, or None on error."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO analysis_log (chat_length, chat_status, relationship_type, request_duration_ms, error, turning_point_detected, turning_point_confidence, features_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (chat_length, chat_status, relationship_type, duration_ms, error,
             1 if turning_point_detected else 0 if turning_point_detected is not None else None,
             turning_point_confidence,
             features_json),
        )
        conn.commit()
        return cursor.lastrowid


def get_analysis_log(analysis_id: int) -> dict | None:
    """Retrieve an analysis log entry by ID. Returns None if not found."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM analysis_log WHERE id = ?", (analysis_id,)
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def save_review_log(
    analysis_id: str,
    review_status: str | None = None,
    advice_effective: str | None = None,
    new_chat_length: int = 0,
) -> int | None:
    """Save a review log entry. Returns the auto-increment ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO review_log (analysis_id, review_status, advice_effective, new_chat_length) VALUES (?, ?, ?, ?)",
            (analysis_id, review_status, advice_effective, new_chat_length),
        )
        conn.commit()
        return cursor.lastrowid


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


def save_outcome(analysis_id: str | None = None, reply_used: str = "", outcome: str = ""):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO outcome (analysis_id, reply_used, outcome) VALUES (?, ?, ?)",
            (analysis_id, reply_used, outcome),
        )
        conn.commit()
    logger.info(f"Outcome saved: reply_used={reply_used}, outcome={outcome}")


def get_outcome_stats():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        total = cursor.execute("SELECT COUNT(*) FROM outcome").fetchone()[0]
        reply_used_count = cursor.execute(
            "SELECT COUNT(*) FROM outcome WHERE reply_used IN ('sent', 'modified')"
        ).fetchone()[0]
        positive_count = cursor.execute(
            "SELECT COUNT(*) FROM outcome WHERE outcome = 'more_positive'"
        ).fetchone()[0]

    return {
        "total": total,
        "reply_adoption_rate": round(reply_used_count / total * 100, 1) if total > 0 else 0,
        "positive_outcome_rate": round(positive_count / total * 100, 1) if total > 0 else 0,
    }


# ── Analytics: event tracking & metrics ──

VALID_EVENTS = {
    "page_view", "analysis_created", "analysis_success",
    "reply_generated", "reply_used", "feedback_given", "return_visit",
    "relationship_selected", "usage_limit_hit", "image_analysis_started",
    "image_analysis_success",
    "share_clicked", "share_image_generated", "share_succeeded", "share_cancelled",
    "share_reward_granted", "share_reward_limit_hit",
}


def save_event(anonymous_user_id: str, event_name: str, properties: str | None = None, session_id: str | None = None):
    event_id = str(uuid.uuid4())
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO events (id, anonymous_user_id, event_name, properties, session_id) VALUES (?, ?, ?, ?, ?)",
            (event_id, anonymous_user_id, event_name, properties, session_id),
        )
        conn.commit()


def get_metrics() -> dict:
    """Compute all V1 metrics from the events table."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        # DAU: unique users with any event today
        dau = cursor.execute(
            "SELECT COUNT(DISTINCT anonymous_user_id) FROM events WHERE date(created_at) = ?",
            (today,),
        ).fetchone()[0]

        # D1 retention: users active yesterday who were also active on their first day
        # Logic: users whose first event was on a day X, and who also have events on day X+1
        d1_numerator = cursor.execute("""
            SELECT COUNT(DISTINCT e1.anonymous_user_id)
            FROM events e1
            JOIN events e2 ON e1.anonymous_user_id = e2.anonymous_user_id
            WHERE date(e1.created_at) = ?
              AND date(e2.created_at) = date(e1.created_at, '+1 day')
              AND e1.anonymous_user_id IN (
                  SELECT anonymous_user_id FROM events
                  GROUP BY anonymous_user_id
                  HAVING date(MIN(created_at)) = date(e1.created_at)
              )
        """, (yesterday,)).fetchone()[0]

        d1_denominator_row = cursor.execute("""
            SELECT COUNT(DISTINCT anonymous_user_id)
            FROM events
            GROUP BY anonymous_user_id
            HAVING date(MIN(created_at)) = ?
        """, (yesterday,)).fetchone()
        d1_denominator = d1_denominator_row[0] if d1_denominator_row else 0

        d1_retention = round(d1_numerator / d1_denominator * 100, 1) if d1_denominator > 0 else 0

        # D7 retention
        d7_numerator = cursor.execute("""
            SELECT COUNT(DISTINCT e1.anonymous_user_id)
            FROM events e1
            JOIN events e2 ON e1.anonymous_user_id = e2.anonymous_user_id
            WHERE date(e1.created_at) = ?
              AND date(e2.created_at) = date(e1.created_at, '+7 days')
              AND e1.anonymous_user_id IN (
                  SELECT anonymous_user_id FROM events
                  GROUP BY anonymous_user_id
                  HAVING date(MIN(created_at)) = date(e1.created_at)
              )
        """, (week_ago,)).fetchone()[0]

        d7_denominator_row = cursor.execute("""
            SELECT COUNT(DISTINCT anonymous_user_id)
            FROM events
            GROUP BY anonymous_user_id
            HAVING date(MIN(created_at)) = ?
        """, (week_ago,)).fetchone()
        d7_denominator = d7_denominator_row[0] if d7_denominator_row else 0

        d7_retention = round(d7_numerator / d7_denominator * 100, 1) if d7_denominator > 0 else 0

        # Total analyses (analysis_success events)
        total_analyses = cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event_name = 'analysis_success'"
        ).fetchone()[0]

        # Helpful rate: feedback_given events where properties contains "helpful": true
        feedback_total = cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event_name = 'feedback_given'"
        ).fetchone()[0]
        feedback_helpful = cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event_name = 'feedback_given' AND properties LIKE '%helpful\": true%'"
        ).fetchone()[0]
        helpful_rate = round(feedback_helpful / feedback_total * 100, 1) if feedback_total > 0 else 0

        # Reply adoption rate: reply_used / analysis_success
        reply_used_count = cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event_name = 'reply_used'"
        ).fetchone()[0]
        reply_adoption_rate = round(reply_used_count / total_analyses * 100, 1) if total_analyses > 0 else 0

        # Avg analyses per user
        analysis_per_user_row = cursor.execute("""
            SELECT AVG(cnt) FROM (
                SELECT COUNT(*) as cnt FROM events
                WHERE event_name = 'analysis_success'
                GROUP BY anonymous_user_id
            )
        """).fetchone()[0]
        analysis_count_per_user = round(analysis_per_user_row, 1) if analysis_per_user_row else 0

        # Avg analysis duration (ms from client-reported properties)
        duration_row = cursor.execute("""
            SELECT AVG(CAST(json_extract(properties, '$.duration_ms') AS REAL))
            FROM events
            WHERE event_name = 'analysis_success'
              AND properties LIKE '%duration_ms%'
              AND CAST(json_extract(properties, '$.duration_ms') AS REAL) > 0
        """).fetchone()[0]
        avg_analysis_duration_ms = round(duration_row) if duration_row else 0

        # Avg OCR (screenshot text extraction) duration
        ocr_duration_row = cursor.execute("""
            SELECT AVG(CAST(json_extract(properties, '$.duration_ms') AS REAL))
            FROM events
            WHERE event_name = 'image_analysis_success'
              AND properties LIKE '%duration_ms%'
              AND CAST(json_extract(properties, '$.duration_ms') AS REAL) > 0
        """).fetchone()[0]
        avg_ocr_duration_ms = round(ocr_duration_row) if ocr_duration_row else 0

        # Total image analyses
        total_image_analyses = cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event_name = 'image_analysis_success'"
        ).fetchone()[0]

        # Share conversion rate: share_succeeded / share_clicked
        share_clicked_count = cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event_name = 'share_clicked'"
        ).fetchone()[0]
        share_succeeded_count = cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event_name = 'share_succeeded'"
        ).fetchone()[0]
        share_conversion_rate = round(share_succeeded_count / share_clicked_count * 100, 1) if share_clicked_count > 0 else 0

    return {
        "dau": dau,
        "d1_retention": d1_retention,
        "d7_retention": d7_retention,
        "total_analyses": total_analyses,
        "total_image_analyses": total_image_analyses,
        "helpful_rate": helpful_rate,
        "reply_adoption_rate": reply_adoption_rate,
        "analysis_count_per_user": analysis_count_per_user,
        "avg_analysis_duration_ms": avg_analysis_duration_ms,
        "avg_ocr_duration_ms": avg_ocr_duration_ms,
        "share_conversion_rate": share_conversion_rate,
        "share_clicked_count": share_clicked_count,
        "share_succeeded_count": share_succeeded_count,
    }


# ── Share Rewards (V1.2) ──

def get_share_reward_count(anonymous_user_id: str, reward_date: str) -> int:
    """Get today's share reward count for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT COALESCE(SUM(reward_count), 0) FROM share_rewards WHERE anonymous_user_id = ? AND reward_date = ?",
            (anonymous_user_id, reward_date),
        ).fetchone()
    return row[0] if row else 0


def save_share_reward(anonymous_user_id: str, reward_type: str, share_hash: str) -> str:
    """Save a share reward record. Returns the reward ID."""
    reward_id = str(uuid.uuid4())
    reward_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO share_rewards (id, anonymous_user_id, reward_date, reward_type, reward_count, share_hash) VALUES (?, ?, ?, ?, 1, ?)",
            (reward_id, anonymous_user_id, reward_date, reward_type, share_hash),
        )
        conn.commit()
    logger.info(f"Share reward granted: user={anonymous_user_id}, type={reward_type}")
    return reward_id


# ── Feedback Rewards (V1.3) ──

def get_feedback_reward_count(anonymous_user_id: str, reward_date: str) -> int:
    """Get today's feedback reward count for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT COALESCE(SUM(reward_count), 0) FROM feedback_rewards WHERE anonymous_user_id = ? AND reward_date = ?",
            (anonymous_user_id, reward_date),
        ).fetchone()
    return row[0] if row else 0


def save_feedback_reward(anonymous_user_id: str) -> str:
    """Save a feedback reward record. Returns the reward ID."""
    reward_id = str(uuid.uuid4())
    reward_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback_rewards (id, anonymous_user_id, reward_date, reward_count) VALUES (?, ?, ?, 1)",
            (reward_id, anonymous_user_id, reward_date),
        )
        conn.commit()
    logger.info(f"Feedback reward granted: user={anonymous_user_id}")
    return reward_id


# ── Analysis Tags (Phase 3) ──

def save_analysis_tags(
    analysis_id: int,
    conversation_stage: str = "",
    other_style: str = "",
    user_issue: str = "",
    label_source: str = "rule",
) -> int | None:
    """Save auto-generated tags for an analysis. Returns the tag ID or None on error."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO analysis_tags (analysis_id, conversation_stage, other_style, user_issue, label_source) VALUES (?, ?, ?, ?, ?)",
                (analysis_id, conversation_stage, other_style, user_issue, label_source),
            )
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.warning(f"Failed to save analysis tags (analysis_id={analysis_id}): {e}")
        return None


def get_analysis_tags(analysis_id: int) -> dict | None:
    """Get tags for an analysis by ID. Returns None if not found."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM analysis_tags WHERE analysis_id = ? ORDER BY created_at DESC LIMIT 1",
            (analysis_id,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_tag_stats() -> dict:
    """Get tag distribution stats for dashboard."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        total_tagged = cursor.execute("SELECT COUNT(*) FROM analysis_tags").fetchone()[0]

        # conversation_stage distribution
        stage_rows = cursor.execute(
            "SELECT conversation_stage, COUNT(*) as cnt FROM analysis_tags WHERE conversation_stage != '' GROUP BY conversation_stage ORDER BY cnt DESC"
        ).fetchall()
        conversation_stage_dist = {row["conversation_stage"]: row["cnt"] for row in stage_rows}

        # other_style distribution
        style_rows = cursor.execute(
            "SELECT other_style, COUNT(*) as cnt FROM analysis_tags WHERE other_style != '' GROUP BY other_style ORDER BY cnt DESC"
        ).fetchall()
        other_style_dist = {row["other_style"]: row["cnt"] for row in style_rows}

        # user_issue distribution
        issue_rows = cursor.execute(
            "SELECT user_issue, COUNT(*) as cnt FROM analysis_tags WHERE user_issue != '' GROUP BY user_issue ORDER BY cnt DESC"
        ).fetchall()
        user_issue_dist = {row["user_issue"]: row["cnt"] for row in issue_rows}

    return {
        "total_tagged": total_tagged,
        "conversation_stage_dist": conversation_stage_dist,
        "other_style_dist": other_style_dist,
        "user_issue_dist": user_issue_dist,
    }


# ── Error Case Queries (Phase 4) ──

def get_error_case_stats() -> dict:
    """Get error case statistics: reason distribution and stage-error cross stats."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        total_errors = cursor.execute(
            "SELECT COUNT(*) FROM feedback WHERE helpful = 0"
        ).fetchone()[0]

        # Reason distribution (reason is comma-separated in DB)
        reason_rows = cursor.execute(
            "SELECT reason FROM feedback WHERE helpful = 0 AND reason != ''"
        ).fetchall()

        reason_dist: dict[str, int] = {}
        for row in reason_rows:
            for r in row["reason"].split(","):
                r = r.strip()
                if r:
                    reason_dist[r] = reason_dist.get(r, 0) + 1

        # Stage-error cross distribution
        stage_error_rows = cursor.execute("""
            SELECT at.conversation_stage, COUNT(*) as cnt
            FROM feedback f
            JOIN analysis_tags at ON CAST(f.analysis_id AS INTEGER) = at.analysis_id
            WHERE f.helpful = 0 AND at.conversation_stage != ''
            GROUP BY at.conversation_stage
            ORDER BY cnt DESC
        """).fetchall()
        stage_error_dist = {row["conversation_stage"]: row["cnt"] for row in stage_error_rows}

    return {
        "total_errors": total_errors,
        "reason_distribution": reason_dist,
        "stage_error_distribution": stage_error_dist,
    }


def get_error_cases(limit: int = 20, offset: int = 0) -> dict:
    """Get paginated error cases with tag info. Returns {cases, total}."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        total = cursor.execute(
            "SELECT COUNT(*) FROM feedback WHERE helpful = 0"
        ).fetchone()[0]

        rows = cursor.execute("""
            SELECT f.id, f.analysis_id, f.reason, f.comment, f.created_at,
                   al.chat_status,
                   at.conversation_stage, at.other_style, at.user_issue
            FROM feedback f
            LEFT JOIN analysis_log al ON CAST(f.analysis_id AS INTEGER) = al.id
            LEFT JOIN analysis_tags at ON CAST(f.analysis_id AS INTEGER) = at.analysis_id
            WHERE f.helpful = 0
            ORDER BY f.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()

        cases = []
        for row in rows:
            cases.append({
                "id": row["id"],
                "analysis_id": row["analysis_id"],
                "reason": row["reason"],
                "comment": row["comment"],
                "chat_status": row["chat_status"] or "",
                "conversation_stage": row["conversation_stage"] or "",
                "other_style": row["other_style"] or "",
                "user_issue": row["user_issue"] or "",
                "created_at": row["created_at"],
            })

    return {"cases": cases, "total": total}


# ── Good Cases (Few-Shot Learning) ──

def save_good_case(features: dict, relationship_type: str, analysis_json: str, language: str = "zh", quality_reason: str = "") -> int:
    """Save a high-quality analysis as a few-shot example. Returns the case ID.

    Called when user gives positive feedback (helpful=true) on an analysis.
    Only stores extracted features (not raw chat content) per privacy policy.
    Deduplication: by feature_hash to avoid storing near-identical patterns.
    quality_reason: comma-separated reasons the user gave for finding it helpful.
    """
    import hashlib
    import json

    feature_hash = hashlib.sha256(
        json.dumps(features, sort_keys=True).encode()
    ).hexdigest()[:16]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Dedup check by feature hash
        existing = cursor.execute(
            "SELECT id FROM good_cases WHERE feature_hash = ? AND relationship_type = ? AND language = ?",
            (feature_hash, relationship_type, language),
        ).fetchone()
        if existing:
            logger.info(f"Good case already exists (id={existing[0]}), skipping")
            return existing[0]

        cursor.execute(
            """INSERT INTO good_cases
               (feature_hash, total_messages, total_rounds, user_msgs, other_msgs,
                avg_user_len, avg_other_len, other_question_ratio, notable_patterns,
                relationship_type, analysis_json, language, quality_reason,
                other_emoji_count, user_emoji_count, other_short_ratio,
                sentiment_pos, sentiment_neg, topic_coherence,
                user_question_ratio, user_solution_ratio, user_closing_ratio,
                safe_zone_ratio, max_emoji_relay)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                feature_hash,
                features.get("total_messages", 0),
                features.get("total_rounds", 0),
                features.get("user_msgs", 0),
                features.get("other_msgs", 0),
                features.get("avg_user_len", 0.0),
                features.get("avg_other_len", 0.0),
                features.get("other_question_ratio", 0.0),
                features.get("notable_patterns", ""),
                relationship_type,
                analysis_json,
                language,
                quality_reason,
                features.get("other_emoji_count", 0),
                features.get("user_emoji_count", 0),
                features.get("other_short_ratio", 0.0),
                features.get("sentiment_pos", 0),
                features.get("sentiment_neg", 0),
                features.get("topic_coherence", 0.0),
                features.get("user_question_ratio", 0.0),
                features.get("user_solution_ratio", 0.0),
                features.get("user_closing_ratio", 0.0),
                features.get("safe_zone_ratio", 0.0),
                features.get("max_emoji_relay", 0),
            ),
        )
        conn.commit()
        case_id = cursor.lastrowid

    # Limit to 100 cases to prevent unbounded growth
    _prune_good_cases(max_cases=100)
    logger.info(f"Good case saved: id={case_id}, relationship={relationship_type}, lang={language}")
    return case_id


def get_good_cases(relationship_type: str | None = None, language: str = "zh", limit: int = 3) -> list[dict]:
    """Fetch recent good cases for few-shot prompting.

    Returns cases most recently created, optionally filtered by relationship_type.
    Returns extracted features (not raw chat content) per privacy policy.
    Includes enhanced features (emoji, sentiment, coherence) and quality_reason.
    Limits results to keep prompt lean.
    """
    columns = ("id, total_messages, total_rounds, user_msgs, other_msgs, "
               "avg_user_len, avg_other_len, other_question_ratio, notable_patterns, "
               "relationship_type, analysis_json, language, usage_count, "
               "quality_reason, other_emoji_count, user_emoji_count, "
               "other_short_ratio, sentiment_pos, sentiment_neg, topic_coherence, "
               "user_question_ratio, user_solution_ratio, user_closing_ratio, "
               "safe_zone_ratio, max_emoji_relay")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        if relationship_type:
            rows = cursor.execute(
                f"SELECT {columns} FROM good_cases "
                "WHERE relationship_type = ? AND language = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (relationship_type, language, limit),
            ).fetchall()
        else:
            rows = cursor.execute(
                f"SELECT {columns} FROM good_cases "
                "WHERE language = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (language, limit),
            ).fetchall()

        cases = []
        for row in rows:
            case = dict(row)
            # Increment usage count
            cursor.execute(
                "UPDATE good_cases SET usage_count = usage_count + 1 WHERE id = ?",
                (case["id"],),
            )
            cases.append(case)
        conn.commit()

    return cases


def _prune_good_cases(max_cases: int = 100):
    """Delete oldest good cases when count exceeds max_cases."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            count = cursor.execute("SELECT COUNT(*) FROM good_cases").fetchone()[0]
            if count > max_cases:
                excess = count - max_cases
                cursor.execute(
                    "DELETE FROM good_cases WHERE id IN (SELECT id FROM good_cases ORDER BY created_at ASC LIMIT ?)",
                    (excess,),
                )
                conn.commit()
                logger.info(f"Pruned {excess} old good cases (keeping {max_cases})")
    except Exception as e:
        logger.warning(f"Failed to prune good cases: {e}")
