"""
Cleanup old share event records from the events table.
Removes share_cancelled events and outdated share_succeeded breakdown records.
Also cleans up the bl_first_visit_ts entries from the analytics data.

Usage:
    cd backend && python cleanup_share_events.py
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "betweenlines.db")


def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── Show current counts ──
    print("=== Before cleanup ===")
    for table in ["events", "analysis_log", "share_rewards"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")

    # Event breakdown
    for event_name in ["share_clicked", "share_succeeded", "share_cancelled", "analysis_success"]:
        cursor.execute("SELECT COUNT(*) FROM events WHERE event_name = ?", (event_name,))
        count = cursor.fetchone()[0]
        print(f"  events.{event_name}: {count}")

    # ── Cleanup share_cancelled events ──
    cursor.execute("DELETE FROM events WHERE event_name = 'share_cancelled'")
    cancelled_deleted = cursor.rowcount
    print(f"\nDeleted {cancelled_deleted} share_cancelled events")

    # ── Cleanup old analysis_success events that contain time_to_first_analysis_ms (deprecated field) ──
    # We don't delete the event, just note — the field is ignored by new queries.
    cursor.execute(
        "SELECT COUNT(*) FROM events WHERE event_name = 'analysis_success' "
        "AND properties LIKE '%time_to_first_analysis_ms%'"
    )
    old_ttfa_count = cursor.fetchone()[0]
    print(f"  {old_ttfa_count} analysis_success events contain deprecated time_to_first_analysis_ms field (kept, ignored)")

    conn.commit()

    # ── Show after counts ──
    print("\n=== After cleanup ===")
    cursor.execute("SELECT COUNT(*) FROM events")
    total = cursor.fetchone()[0]
    print(f"  events: {total} rows")

    for event_name in ["share_clicked", "share_succeeded", "share_cancelled"]:
        cursor.execute("SELECT COUNT(*) FROM events WHERE event_name = ?", (event_name,))
        count = cursor.fetchone()[0]
        print(f"  events.{event_name}: {count}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
