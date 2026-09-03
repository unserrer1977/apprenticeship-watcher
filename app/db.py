"""SQLite storage layer with deduplication."""
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import List, Optional

from .config import config
from .models import Opportunity

_SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedup_key TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    employer TEXT,
    role TEXT,
    location TEXT,
    salary TEXT,
    application_link TEXT,
    opening_date TEXT,
    deadline TEXT,
    start_date TEXT,
    training_course TEXT,
    description TEXT,
    region TEXT,
    priority INTEGER DEFAULT 10,
    topic TEXT DEFAULT '',
    is_degree INTEGER DEFAULT 0,
    big_employer INTEGER DEFAULT 0,
    first_seen TEXT,
    last_seen TEXT,
    status TEXT DEFAULT 'active',
    alerted_new INTEGER DEFAULT 0,
    alerted_deadline INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_deadline ON opportunities(deadline);
CREATE INDEX IF NOT EXISTS idx_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_region ON opportunities(region);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Storage:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.db_path
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init(self):
        with self._lock, self._connect() as conn:
            conn.executescript(_SCHEMA)
            # Migrate existing databases that predate priority scoring.
            for col, ddl in (
                ("priority", "ALTER TABLE opportunities ADD COLUMN priority INTEGER DEFAULT 10"),
                ("topic", "ALTER TABLE opportunities ADD COLUMN topic TEXT DEFAULT ''"),
                ("is_degree", "ALTER TABLE opportunities ADD COLUMN is_degree INTEGER DEFAULT 0"),
                ("big_employer", "ALTER TABLE opportunities ADD COLUMN big_employer INTEGER DEFAULT 0"),
            ):
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(opportunities)")]
                if col not in cols:
                    conn.execute(ddl)
            conn.commit()

    def upsert(self, opp: Opportunity) -> str:
        """Insert a new opportunity or refresh an existing one.

        Returns 'new' if inserted, 'updated' if an existing row was refreshed,
        or 'duplicate' if nothing changed.
        """
        now = _now()
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT id, first_seen, alerted_new, alerted_deadline, status "
                "FROM opportunities WHERE dedup_key=?",
                (opp.dedup_key,),
            ).fetchone()
            if row is None:
                opp.first_seen = now
                opp.last_seen = now
                conn.execute(
                    """INSERT INTO opportunities
                       (dedup_key, source, employer, role, location, salary,
                        application_link, opening_date, deadline, start_date,
                        training_course, description, region, priority, topic,
                        is_degree, big_employer, first_seen, last_seen, status,
                        alerted_new, alerted_deadline)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        opp.dedup_key, opp.source, opp.employer, opp.role,
                        opp.location, opp.salary, opp.application_link,
                        opp.opening_date, opp.deadline, opp.start_date,
                        opp.training_course, opp.description, opp.region,
                        opp.priority, opp.topic, opp.is_degree, opp.big_employer,
                        opp.first_seen, opp.last_seen, opp.status,
                        opp.alerted_new, opp.alerted_deadline,
                    ),
                )
                conn.commit()
                return "new"

            # Existing: refresh metadata, keep first_seen + alert flags.
            conn.execute(
                """UPDATE opportunities SET
                     employer=?, role=?, location=?, salary=?,
                     application_link=?, opening_date=?, deadline=?,
                     start_date=?, training_course=?, description=?,
                     region=?, priority=?, topic=?, is_degree=?,
                     big_employer=?, last_seen=?, status='active'
                   WHERE dedup_key=?""",
                (
                    opp.employer, opp.role, opp.location, opp.salary,
                    opp.application_link, opp.opening_date, opp.deadline,
                    opp.start_date, opp.training_course, opp.description,
                    opp.region, opp.priority, opp.topic, opp.is_degree,
                    opp.big_employer, now, opp.dedup_key,
                ),
            )
            conn.commit()
            return "updated"

    def mark_closed(self, dedup_keys: List[str]):
        """Mark opportunities not seen in the latest scan as closed."""
        if not dedup_keys:
            return
        placeholders = ",".join("?" for _ in dedup_keys)
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE opportunities SET status='closed' "
                f"WHERE status='active' AND dedup_key NOT IN ({placeholders})",
                dedup_keys,
            )
            conn.commit()

    def list(self, region: Optional[str] = None, status: Optional[str] = None,
             source: Optional[str] = None, closing_soon: bool = False,
             days: Optional[int] = None, topic: Optional[str] = None,
             min_priority: Optional[int] = None,
             sort: str = "newest") -> List[dict]:
        q = "SELECT * FROM opportunities WHERE 1=1"
        params = []
        if region:
            q += " AND region=?"
            params.append(region)
        if status:
            q += " AND status=?"
            params.append(status)
        if source:
            q += " AND source=?"
            params.append(source)
        if topic:
            q += " AND topic=?"
            params.append(topic)
        if min_priority is not None:
            q += " AND priority>=?"
            params.append(min_priority)
        if closing_soon:
            q += " AND status='active' AND deadline != '' AND deadline IS NOT NULL"
        if sort == "priority":
            q += " ORDER BY priority DESC, deadline ASC NULLS LAST"
        elif sort == "deadline":
            q += " ORDER BY deadline ASC NULLS LAST"
        elif closing_soon:
            q += " ORDER BY deadline ASC NULLS LAST"
        else:
            q += " ORDER BY first_seen DESC"
        with self._lock, self._connect() as conn:
            rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]

    def get(self, opp_id: int) -> Optional[dict]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM opportunities WHERE id=?", (opp_id,)
            ).fetchone()
        return dict(row) if row else None

    def id_for_key(self, dedup_key: str) -> Optional[int]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM opportunities WHERE dedup_key=?", (dedup_key,)
            ).fetchone()
        return row["id"] if row else None

    def stats(self) -> dict:
        with self._lock, self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) c FROM opportunities WHERE status='active'"
            ).fetchone()["c"]
            by_source = {
                r["source"]: r["c"]
                for r in conn.execute(
                    "SELECT source, COUNT(*) c FROM opportunities "
                    "WHERE status='active' GROUP BY source"
                ).fetchall()
            }
            by_region = {
                r["region"]: r["c"]
                for r in conn.execute(
                    "SELECT region, COUNT(*) c FROM opportunities "
                    "WHERE status='active' GROUP BY region"
                ).fetchall()
            }
            closing = conn.execute(
                "SELECT COUNT(*) c FROM opportunities WHERE status='active' "
                "AND deadline != '' AND deadline IS NOT NULL"
            ).fetchone()["c"]
        return {
            "active": total,
            "by_source": by_source,
            "by_region": by_region,
            "with_deadline": closing,
        }

    def unalerted_new(self) -> List[dict]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM opportunities WHERE status='active' "
                "AND alerted_new=0"
            ).fetchall()
        return [dict(r) for r in rows]

    def unalerted_deadline(self, days: int) -> List[dict]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM opportunities WHERE status='active' "
                "AND alerted_deadline=0 AND deadline != '' "
                "AND deadline IS NOT NULL"
            ).fetchall()
        return [dict(r) for r in rows]

    def set_alerted(self, opp_id: int, field: str):
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE opportunities SET {field}=1 WHERE id=?", (opp_id,)
            )
            conn.commit()
