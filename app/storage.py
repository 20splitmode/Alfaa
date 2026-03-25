from __future__ import annotations

import csv
import sqlite3
import threading
from datetime import timedelta
from pathlib import Path
from typing import Any

from .antifraud import default_agent_share, generate_referral_code
from .config import Settings
from .utils import json_dumps, json_loads, now_utc, parse_iso


class Storage:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = Path(settings.db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def init_db(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            first_name TEXT,
            activity TEXT,
            segment TEXT,
            status TEXT,
            turnover_band TEXT,
            turnover_value INTEGER,
            city TEXT,
            payment_method TEXT,
            works_with_companies TEXT,
            need_rko TEXT,
            need_registration INTEGER NOT NULL DEFAULT 0,
            need_online_registration TEXT,
            primary_pain TEXT,
            scenario TEXT,
            priority_focus TEXT,
            journey_stage TEXT NOT NULL DEFAULT 'new',
            source TEXT,
            campaign TEXT,
            creative TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            utm_content TEXT,
            utm_term TEXT,
            start_payload TEXT,
            consent_followup INTEGER NOT NULL DEFAULT 0,
            followup_opt_in_at TEXT,
            reminder_enabled INTEGER NOT NULL DEFAULT 1,
            reminder_hour INTEGER NOT NULL DEFAULT 9,
            last_daily_ping_at TEXT,
            panel_chat_id INTEGER,
            panel_message_id INTEGER,
            panel_media_path TEXT,
            quiz_completed_at TEXT,
            last_result_at TEXT,
            last_seen_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quiz_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_key TEXT NOT NULL,
            answer_key TEXT,
            answer_text TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, question_key)
        );

        CREATE TABLE IF NOT EXISTS daily_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entry_type TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT,
            entry_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            agent_id INTEGER,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            contact_time TEXT NOT NULL,
            current_status TEXT,
            lead_status TEXT NOT NULL DEFAULT 'new',
            temperature TEXT NOT NULL DEFAULT 'warm',
            note TEXT,
            duplicate_of INTEGER,
            consent_text_version TEXT NOT NULL,
            consent_confirmed_at TEXT NOT NULL,
            consent_followup INTEGER NOT NULL DEFAULT 0,
            source TEXT,
            campaign TEXT,
            creative TEXT,
            segment TEXT,
            scenario TEXT,
            fraud_score INTEGER NOT NULL DEFAULT 0,
            fraud_status TEXT NOT NULL DEFAULT 'hold',
            fraud_reasons_json TEXT,
            form_duration_sec INTEGER,
            antifraud_version TEXT,
            sent_to_partner INTEGER NOT NULL DEFAULT 0,
            sent_to_partner_at TEXT,
            external_lead_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            agent_status TEXT NOT NULL DEFAULT 'pending',
            agent_level TEXT NOT NULL DEFAULT 'junior',
            referral_code TEXT UNIQUE,
            payout_type TEXT NOT NULL DEFAULT 'revshare',
            payout_value REAL NOT NULL DEFAULT 30,
            application_json TEXT,
            application_summary TEXT,
            submitted_at TEXT,
            offer_confirmed_at TEXT,
            offer_document_version TEXT,
            exam_status TEXT NOT NULL DEFAULT 'not_started',
            exam_score INTEGER,
            exam_total INTEGER,
            exam_passed_at TEXT,
            exam_attempts INTEGER NOT NULL DEFAULT 0,
            exam_last_attempt_at TEXT,
            exam_blocked_until TEXT,
            exam_version TEXT,
            note TEXT,
            approved_by INTEGER,
            approved_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_payouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL,
            lead_id INTEGER,
            amount REAL NOT NULL DEFAULT 0,
            payout_type TEXT NOT NULL DEFAULT 'revshare',
            status TEXT NOT NULL DEFAULT 'pending',
            note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_exam_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            agent_id INTEGER,
            exam_version TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'in_progress',
            questions_json TEXT NOT NULL,
            answers_json TEXT,
            score INTEGER,
            total_questions INTEGER NOT NULL DEFAULT 0,
            passed INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            blocked_until TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reminder_type TEXT NOT NULL,
            scheduled_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            payload_json TEXT,
            sent_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, reminder_type)
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            lead_id INTEGER,
            event_type TEXT NOT NULL,
            payload_json TEXT,
            created_at TEXT NOT NULL
        );
        """
        with self._lock:
            self.conn.executescript(schema)
            self._ensure_column("users", "priority_focus", "TEXT")
            self._ensure_column("users", "reminder_enabled", "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column("users", "reminder_hour", "INTEGER NOT NULL DEFAULT 9")
            self._ensure_column("users", "last_daily_ping_at", "TEXT")
            self._ensure_column("users", "panel_chat_id", "INTEGER")
            self._ensure_column("users", "panel_message_id", "INTEGER")
            self._ensure_column("users", "panel_media_path", "TEXT")
            self._ensure_column("users", "referred_by_agent_id", "INTEGER")
            self._ensure_column("leads", "agent_id", "INTEGER")
            self._ensure_column("leads", "fraud_score", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column("leads", "fraud_status", "TEXT NOT NULL DEFAULT 'hold'")
            self._ensure_column("leads", "fraud_reasons_json", "TEXT")
            self._ensure_column("leads", "form_duration_sec", "INTEGER")
            self._ensure_column("leads", "antifraud_version", "TEXT")
            self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id)")
            self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_referral_code ON agents(referral_code)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_exam_attempts_user_id ON agent_exam_attempts(user_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_exam_attempts_status ON agent_exam_attempts(status)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_referred_by_agent_id ON users(referred_by_agent_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_agent_id ON leads(agent_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_fraud_status ON leads(fraud_status)")
            self._ensure_column("agents", "application_json", "TEXT")
            self._ensure_column("agents", "application_summary", "TEXT")
            self._ensure_column("agents", "submitted_at", "TEXT")
            self._ensure_column("agents", "offer_confirmed_at", "TEXT")
            self._ensure_column("agents", "offer_document_version", "TEXT")
            self._ensure_column("agents", "exam_status", "TEXT NOT NULL DEFAULT 'not_started'")
            self._ensure_column("agents", "exam_score", "INTEGER")
            self._ensure_column("agents", "exam_total", "INTEGER")
            self._ensure_column("agents", "exam_passed_at", "TEXT")
            self._ensure_column("agents", "exam_attempts", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column("agents", "exam_last_attempt_at", "TEXT")
            self._ensure_column("agents", "exam_blocked_until", "TEXT")
            self._ensure_column("agents", "exam_version", "TEXT")
            self.conn.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column in columns:
            return
        self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _fetchone(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self._lock:
            row = self.conn.execute(query, params).fetchone()
        return dict(row) if row else None

    def _fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        with self._lock:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return int(cursor.lastrowid)

    def get_or_create_user(
        self,
        telegram_id: int,
        *,
        username: str | None = None,
        full_name: str | None = None,
        first_name: str | None = None,
        tracking: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        user = self.get_user(telegram_id)
        now = now_utc().isoformat()
        if user:
            update_fields: dict[str, Any] = {
                "username": username or user.get("username"),
                "full_name": full_name or user.get("full_name"),
                "first_name": first_name or user.get("first_name"),
                "last_seen_at": now,
            }
            if tracking:
                for key in (
                    "source",
                    "campaign",
                    "creative",
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                    "utm_content",
                    "utm_term",
                    "start_payload",
                ):
                    if tracking.get(key):
                        update_fields[key] = tracking[key]
            return self.update_user(telegram_id, **update_fields) or self.get_user(telegram_id) or {}

        row_id = self._execute(
            """
            INSERT INTO users (
                telegram_id, username, full_name, first_name, last_seen_at,
                source, campaign, creative, utm_source, utm_medium, utm_campaign, utm_content, utm_term, start_payload,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                username,
                full_name,
                first_name,
                now,
                (tracking or {}).get("source", ""),
                (tracking or {}).get("campaign", ""),
                (tracking or {}).get("creative", ""),
                (tracking or {}).get("utm_source", ""),
                (tracking or {}).get("utm_medium", ""),
                (tracking or {}).get("utm_campaign", ""),
                (tracking or {}).get("utm_content", ""),
                (tracking or {}).get("utm_term", ""),
                (tracking or {}).get("start_payload", ""),
                now,
                now,
            ),
        )
        return self.get_user(telegram_id) or {"id": row_id, "telegram_id": telegram_id}

    def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        return self._fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        return self._fetchone("SELECT * FROM users WHERE id = ?", (user_id,))

    def get_agent(self, agent_id: int) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT agents.*, users.telegram_id, users.username, users.first_name, users.full_name
            FROM agents
            JOIN users ON users.id = agents.user_id
            WHERE agents.id = ?
            """,
            (agent_id,),
        )

    def get_agent_by_user(self, telegram_id: int) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT agents.*, users.telegram_id, users.username, users.first_name, users.full_name
            FROM agents
            JOIN users ON users.id = agents.user_id
            WHERE users.telegram_id = ?
            """,
            (telegram_id,),
        )

    def get_agent_by_code(self, referral_code: str) -> dict[str, Any] | None:
        clean = (referral_code or "").strip()
        if not clean:
            return None
        return self._fetchone(
            """
            SELECT agents.*, users.telegram_id, users.username, users.first_name, users.full_name
            FROM agents
            JOIN users ON users.id = agents.user_id
            WHERE agents.referral_code = ?
              AND agents.agent_status = 'approved'
            """,
            (clean,),
        )

    def create_agent_application(self, telegram_id: int) -> dict[str, Any]:
        user = self.get_user(telegram_id)
        if not user:
            raise ValueError("User not found")
        existing = self.get_agent_by_user(telegram_id)
        if existing:
            return existing
        now = now_utc().isoformat()
        agent_id = self._execute(
            """
            INSERT INTO agents (user_id, agent_status, agent_level, payout_type, payout_value, created_at, updated_at)
            VALUES (?, 'pending', 'junior', 'revshare', ?, ?, ?)
            """,
            (user["id"], default_agent_share("junior"), now, now),
        )
        return self.get_agent(agent_id) or {"id": agent_id, "user_id": user["id"]}

    def save_agent_draft_application(
        self,
        telegram_id: int,
        *,
        answers: dict[str, Any],
        summary: str,
    ) -> dict[str, Any]:
        user = self.get_user(telegram_id)
        if not user:
            raise ValueError("User not found")
        now = now_utc().isoformat()
        payload_json = json_dumps(answers)
        existing = self.get_agent_by_user(telegram_id)
        if existing:
            self._execute(
                """
                UPDATE agents
                SET agent_status = CASE WHEN agent_status IN ('approved', 'banned') THEN agent_status ELSE 'draft' END,
                    application_json = ?,
                    application_summary = ?,
                    submitted_at = CASE WHEN agent_status = 'pending' THEN submitted_at ELSE NULL END,
                    offer_confirmed_at = CASE WHEN agent_status IN ('approved', 'banned') THEN offer_confirmed_at ELSE NULL END,
                    offer_document_version = CASE WHEN agent_status IN ('approved', 'banned') THEN offer_document_version ELSE NULL END,
                    exam_status = CASE WHEN agent_status IN ('approved', 'banned') THEN exam_status ELSE 'not_started' END,
                    exam_score = CASE WHEN agent_status IN ('approved', 'banned') THEN exam_score ELSE NULL END,
                    exam_total = CASE WHEN agent_status IN ('approved', 'banned') THEN exam_total ELSE NULL END,
                    exam_passed_at = CASE WHEN agent_status IN ('approved', 'banned') THEN exam_passed_at ELSE NULL END,
                    exam_blocked_until = CASE WHEN agent_status IN ('approved', 'banned') THEN exam_blocked_until ELSE NULL END,
                    exam_version = CASE WHEN agent_status IN ('approved', 'banned') THEN exam_version ELSE NULL END,
                    updated_at = ?
                WHERE id = ?
                """,
                (payload_json, summary, now, existing["id"]),
            )
            return self.get_agent(int(existing["id"])) or existing
        agent_id = self._execute(
            """
            INSERT INTO agents (
                user_id, agent_status, agent_level, payout_type, payout_value,
                application_json, application_summary, offer_confirmed_at, offer_document_version, exam_status, created_at, updated_at
            )
            VALUES (?, 'draft', 'junior', 'revshare', ?, ?, ?, NULL, NULL, 'not_started', ?, ?)
            """,
            (
                user["id"],
                default_agent_share("junior"),
                payload_json,
                summary,
                now,
                now,
            ),
        )
        return self.get_agent(agent_id) or {"id": agent_id, "user_id": user["id"]}

    def mark_agent_offer_confirmed(
        self,
        telegram_id: int,
        *,
        document_version: str,
    ) -> dict[str, Any] | None:
        agent = self.get_agent_by_user(telegram_id)
        if not agent:
            return None
        now = now_utc().isoformat()
        self._execute(
            """
            UPDATE agents
            SET offer_confirmed_at = ?,
                offer_document_version = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now, document_version, now, int(agent["id"])),
        )
        return self.get_agent(int(agent["id"]))

    def submit_agent_application(
        self,
        telegram_id: int,
        *,
        answers: dict[str, Any],
        summary: str,
    ) -> dict[str, Any]:
        user = self.get_user(telegram_id)
        if not user:
            raise ValueError("User not found")
        now = now_utc().isoformat()
        existing = self.get_agent_by_user(telegram_id)
        payload_json = json_dumps(answers)
        if existing:
            self._execute(
                """
                UPDATE agents
                SET agent_status = CASE WHEN agent_status = 'banned' THEN agent_status ELSE 'pending' END,
                    application_json = ?,
                    application_summary = ?,
                    submitted_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (payload_json, summary, now, now, existing["id"]),
            )
            return self.get_agent(int(existing["id"])) or existing
        agent_id = self._execute(
            """
            INSERT INTO agents (
                user_id, agent_status, agent_level, payout_type, payout_value,
                application_json, application_summary, submitted_at, created_at, updated_at
            )
            VALUES (?, 'pending', 'junior', 'revshare', ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                default_agent_share("junior"),
                payload_json,
                summary,
                now,
                now,
                now,
            ),
        )
        return self.get_agent(agent_id) or {"id": agent_id, "user_id": user["id"]}

    def activate_agent_application(self, agent_id: int) -> dict[str, Any] | None:
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        now = now_utc().isoformat()
        self._execute(
            """
            UPDATE agents
            SET agent_status = CASE WHEN agent_status = 'banned' THEN agent_status ELSE 'pending' END,
                submitted_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, agent_id),
        )
        return self.get_agent(agent_id)

    def _build_unique_referral_code(self, telegram_id: int) -> str:
        base = generate_referral_code(f"{telegram_id}:{now_utc().isoformat()}")
        candidate = base
        suffix = 0
        while self._fetchone("SELECT id FROM agents WHERE referral_code = ?", (candidate,)):
            suffix += 1
            candidate = f"{base[:10]}{suffix:02d}"
        return candidate

    def set_agent_state(
        self,
        agent_id: int,
        *,
        agent_status: str | None = None,
        agent_level: str | None = None,
        note: str | None = None,
        approved_by: int | None = None,
    ) -> dict[str, Any] | None:
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        fields: dict[str, Any] = {}
        if agent_status:
            fields["agent_status"] = agent_status
        if agent_level:
            fields["agent_level"] = agent_level
            fields["payout_value"] = default_agent_share(agent_level)
        if note is not None:
            fields["note"] = note
        if agent_status == "approved":
            fields["approved_at"] = now_utc().isoformat()
            if approved_by is not None:
                fields["approved_by"] = approved_by
            if not agent.get("referral_code"):
                fields["referral_code"] = self._build_unique_referral_code(int(agent["telegram_id"]))
        if not fields:
            return agent
        fields["updated_at"] = now_utc().isoformat()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        self._execute(f"UPDATE agents SET {assignments} WHERE id = ?", tuple(fields.values()) + (agent_id,))
        return self.get_agent(agent_id)

    def create_agent_exam_attempt(
        self,
        telegram_id: int,
        *,
        agent_id: int,
        exam_version: str,
        questions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        user = self.get_user(telegram_id)
        if not user:
            raise ValueError("User not found")
        now = now_utc().isoformat()
        payload = json_dumps(questions)
        attempt_id = self._execute(
            """
            INSERT INTO agent_exam_attempts (
                user_id, agent_id, exam_version, status, questions_json, answers_json,
                total_questions, started_at, created_at, updated_at
            )
            VALUES (?, ?, ?, 'in_progress', ?, '[]', ?, ?, ?, ?)
            """,
            (user["id"], agent_id, exam_version, payload, len(questions), now, now, now),
        )
        self._execute(
            """
            UPDATE agents
            SET exam_status = 'in_progress',
                exam_attempts = COALESCE(exam_attempts, 0) + 1,
                exam_last_attempt_at = ?,
                exam_blocked_until = NULL,
                exam_version = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now, exam_version, now, agent_id),
        )
        return self.get_agent_exam_attempt(attempt_id) or {"id": attempt_id, "agent_id": agent_id}

    def get_agent_exam_attempt(self, attempt_id: int) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT
                agent_exam_attempts.*,
                users.telegram_id
            FROM agent_exam_attempts
            JOIN users ON users.id = agent_exam_attempts.user_id
            WHERE agent_exam_attempts.id = ?
            """,
            (attempt_id,),
        )

    def latest_agent_exam_attempt(self, telegram_id: int) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT
                agent_exam_attempts.*,
                users.telegram_id
            FROM agent_exam_attempts
            JOIN users ON users.id = agent_exam_attempts.user_id
            WHERE users.telegram_id = ?
            ORDER BY agent_exam_attempts.created_at DESC
            LIMIT 1
            """,
            (telegram_id,),
        )

    def update_agent_exam_attempt_answers(self, attempt_id: int, answers: list[str]) -> dict[str, Any] | None:
        now = now_utc().isoformat()
        self._execute(
            """
            UPDATE agent_exam_attempts
            SET answers_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (json_dumps(answers), now, attempt_id),
        )
        return self.get_agent_exam_attempt(attempt_id)

    def finish_agent_exam_attempt(
        self,
        attempt_id: int,
        *,
        score: int,
        passed: bool,
        blocked_until: str | None,
    ) -> dict[str, Any] | None:
        attempt = self.get_agent_exam_attempt(attempt_id)
        if not attempt:
            return None
        now = now_utc().isoformat()
        total_questions = int(attempt.get("total_questions") or 0)
        self._execute(
            """
            UPDATE agent_exam_attempts
            SET status = ?,
                score = ?,
                passed = ?,
                blocked_until = ?,
                finished_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            ("passed" if passed else "failed", score, 1 if passed else 0, blocked_until, now, now, attempt_id),
        )
        if attempt.get("agent_id"):
            self._execute(
                """
                UPDATE agents
                SET exam_status = ?,
                    exam_score = ?,
                    exam_total = ?,
                    exam_passed_at = ?,
                    exam_blocked_until = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    "passed" if passed else "failed",
                    score,
                    total_questions,
                    now if passed else None,
                    blocked_until,
                    now,
                    int(attempt["agent_id"]),
                ),
            )
        return self.get_agent_exam_attempt(attempt_id)

    def list_agents(self, *, agent_status: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        params: list[Any] = []
        where = ""
        if agent_status:
            where = "WHERE agents.agent_status = ?"
            params.append(agent_status)
        params.append(limit)
        return self._fetchall(
            f"""
            SELECT agents.*, users.telegram_id, users.username, users.first_name, users.full_name
            FROM agents
            JOIN users ON users.id = agents.user_id
            {where}
            ORDER BY agents.updated_at DESC
            LIMIT ?
            """,
            tuple(params),
        )

    def attach_referral(self, telegram_id: int, referral_code: str) -> dict[str, Any] | None:
        user = self.get_user(telegram_id)
        agent = self.get_agent_by_code(referral_code)
        if not user or not agent:
            return None
        if int(agent["user_id"]) == int(user["id"]):
            return None
        if user.get("referred_by_agent_id"):
            return self.get_agent(int(user["referred_by_agent_id"]))
        self.update_user(telegram_id, referred_by_agent_id=int(agent["id"]))
        return agent

    def update_user(self, telegram_id: int, **fields: Any) -> dict[str, Any] | None:
        if not fields:
            return self.get_user(telegram_id)
        allowed = {
            "username",
            "full_name",
            "first_name",
            "activity",
            "segment",
            "status",
            "turnover_band",
            "turnover_value",
            "city",
            "payment_method",
            "works_with_companies",
            "need_rko",
            "need_registration",
            "need_online_registration",
            "primary_pain",
            "scenario",
            "priority_focus",
            "journey_stage",
            "source",
            "campaign",
            "creative",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_content",
            "utm_term",
            "start_payload",
            "consent_followup",
            "followup_opt_in_at",
            "reminder_enabled",
            "reminder_hour",
            "last_daily_ping_at",
            "panel_chat_id",
            "panel_message_id",
            "panel_media_path",
            "quiz_completed_at",
            "last_result_at",
            "last_seen_at",
            "referred_by_agent_id",
        }
        payload = {key: value for key, value in fields.items() if key in allowed}
        if not payload:
            return self.get_user(telegram_id)
        payload["updated_at"] = now_utc().isoformat()
        assignments = ", ".join(f"{key} = ?" for key in payload)
        params = tuple(payload.values()) + (telegram_id,)
        self._execute(f"UPDATE users SET {assignments} WHERE telegram_id = ?", params)
        return self.get_user(telegram_id)

    def save_panel(self, telegram_id: int, chat_id: int, message_id: int, media_path: str | None = None) -> dict[str, Any] | None:
        return self.update_user(
            telegram_id,
            panel_chat_id=chat_id,
            panel_message_id=message_id,
            panel_media_path=media_path or "",
        )

    def get_panel(self, telegram_id: int) -> dict[str, Any] | None:
        user = self.get_user(telegram_id)
        if not user or not user.get("panel_chat_id") or not user.get("panel_message_id"):
            return None
        return {
            "chat_id": int(user["panel_chat_id"]),
            "message_id": int(user["panel_message_id"]),
            "media_path": user.get("panel_media_path") or None,
        }

    def save_quiz_answer(self, telegram_id: int, question_key: str, answer_key: str, answer_text: str) -> None:
        user = self.get_user(telegram_id)
        if not user:
            return
        now = now_utc().isoformat()
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO quiz_answers (user_id, question_key, answer_key, answer_text, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, question_key)
                DO UPDATE SET answer_key = excluded.answer_key, answer_text = excluded.answer_text, created_at = excluded.created_at
                """,
                (user["id"], question_key, answer_key, answer_text, now),
            )
            self.conn.commit()

    def complete_profile(self, telegram_id: int, result: dict[str, Any]) -> dict[str, Any] | None:
        now = now_utc().isoformat()
        return self.update_user(
            telegram_id,
            segment=result.get("segment"),
            scenario=result.get("scenario"),
            primary_pain=result.get("primary_pain"),
            need_registration=1 if result.get("need_registration") else 0,
            journey_stage="ready",
            quiz_completed_at=now,
            last_result_at=now,
        )

    def enable_followups(self, telegram_id: int) -> dict[str, Any] | None:
        return self.update_user(telegram_id, consent_followup=1, followup_opt_in_at=now_utc().isoformat())

    def disable_followups(self, telegram_id: int) -> dict[str, Any] | None:
        return self.update_user(telegram_id, consent_followup=0)

    def schedule_followups(self, telegram_id: int) -> None:
        user = self.get_user(telegram_id)
        if not user:
            return
        now = now_utc()
        payload = json_dumps({"scenario": user.get("scenario"), "segment": user.get("segment")})
        with self._lock:
            for reminder_type, minutes in self.settings.reminder_plan.items():
                scheduled_at = (now + timedelta(minutes=minutes)).isoformat()
                self.conn.execute(
                    """
                    INSERT INTO reminders (user_id, reminder_type, scheduled_at, status, payload_json, created_at, updated_at)
                    VALUES (?, ?, ?, 'pending', ?, ?, ?)
                    ON CONFLICT(user_id, reminder_type)
                    DO UPDATE SET scheduled_at = excluded.scheduled_at, status = 'pending', payload_json = excluded.payload_json, updated_at = excluded.updated_at
                    """,
                    (
                        user["id"],
                        reminder_type,
                        scheduled_at,
                        payload,
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
            self.conn.commit()

    def cancel_pending_reminders(self, telegram_id: int) -> None:
        user = self.get_user(telegram_id)
        if not user:
            return
        now = now_utc().isoformat()
        with self._lock:
            self.conn.execute(
                "UPDATE reminders SET status = 'cancelled', updated_at = ? WHERE user_id = ? AND status = 'pending'",
                (now, user["id"]),
            )
            self.conn.commit()

    def get_due_reminders(self, limit: int = 50) -> list[dict[str, Any]]:
        now = now_utc().isoformat()
        rows = self._fetchall(
            """
            SELECT reminders.*, users.telegram_id, users.first_name, users.scenario
            FROM reminders
            JOIN users ON users.id = reminders.user_id
            WHERE reminders.status = 'pending'
              AND reminders.scheduled_at <= ?
              AND users.consent_followup = 1
            ORDER BY reminders.scheduled_at ASC
            LIMIT ?
            """,
            (now, limit),
        )
        for row in rows:
            row["payload"] = json_loads(row.get("payload_json"), {})
        return rows

    def mark_reminder_sent(self, reminder_id: int, *, failed: bool = False) -> None:
        now = now_utc().isoformat()
        status = "failed" if failed else "sent"
        with self._lock:
            self.conn.execute(
                "UPDATE reminders SET status = ?, sent_at = ?, updated_at = ? WHERE id = ?",
                (status, now, now, reminder_id),
            )
            self.conn.commit()

    def users_due_for_daily_ping(self, hour: int) -> list[dict[str, Any]]:
        today = now_utc().date().isoformat()
        return self._fetchall(
            """
            SELECT * FROM users
            WHERE reminder_enabled = 1
              AND reminder_hour = ?
              AND (last_daily_ping_at IS NULL OR substr(last_daily_ping_at, 1, 10) < ?)
            """,
            (hour, today),
        )

    def mark_daily_ping(self, telegram_id: int) -> dict[str, Any] | None:
        return self.update_user(telegram_id, last_daily_ping_at=now_utc().isoformat())

    def create_daily_entry(self, telegram_id: int, entry_type: str, amount: float, note: str = "") -> dict[str, Any] | None:
        user = self.get_user(telegram_id)
        if not user:
            return None
        now = now_utc()
        row_id = self._execute(
            """
            INSERT INTO daily_entries (user_id, entry_type, amount, note, entry_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user["id"], entry_type, amount, note, now.date().isoformat(), now.isoformat()),
        )
        self.log_event("daily_entry_created", user_id=user["id"], payload={"type": entry_type, "amount": amount})
        return self._fetchone("SELECT * FROM daily_entries WHERE id = ?", (row_id,))

    def today_summary(self, telegram_id: int) -> dict[str, Any]:
        user = self.get_user(telegram_id)
        if not user:
            return {"income": 0.0, "expense": 0.0, "obligation": 0.0, "balance": 0.0}
        date_key = now_utc().date().isoformat()
        rows = self._fetchall(
            """
            SELECT entry_type, COALESCE(SUM(amount), 0) AS amount
            FROM daily_entries
            WHERE user_id = ? AND entry_date = ?
            GROUP BY entry_type
            """,
            (user["id"], date_key),
        )
        summary = {"income": 0.0, "expense": 0.0, "obligation": 0.0}
        for row in rows:
            if row["entry_type"] in summary:
                summary[row["entry_type"]] = float(row["amount"] or 0.0)
        summary["balance"] = summary["income"] - summary["expense"] - summary["obligation"]
        return summary

    def recent_entries(self, telegram_id: int, limit: int = 5) -> list[dict[str, Any]]:
        user = self.get_user(telegram_id)
        if not user:
            return []
        return self._fetchall(
            """
            SELECT * FROM daily_entries
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user["id"], limit),
        )

    def create_or_update_lead(
        self,
        telegram_id: int,
        *,
        name: str,
        phone: str,
        city: str,
        contact_time: str,
        current_status: str,
        consent_followup: bool,
        consent_text_version: str = "v2",
    ) -> dict[str, Any]:
        user = self.get_user(telegram_id)
        if not user:
            raise ValueError("User not found")
        now = now_utc()
        agent_id = int(user["referred_by_agent_id"]) if user.get("referred_by_agent_id") else None
        existing = self._fetchone(
            """
            SELECT * FROM leads
            WHERE phone = ?
              AND created_at >= ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (phone, (now - timedelta(days=30)).isoformat()),
        )
        if existing:
            with self._lock:
                self.conn.execute(
                    """
                    UPDATE leads
                    SET name = ?, city = ?, contact_time = ?, current_status = ?, consent_followup = ?, agent_id = COALESCE(agent_id, ?), updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        city,
                        contact_time,
                        current_status,
                        1 if consent_followup else 0,
                        agent_id,
                        now.isoformat(),
                        existing["id"],
                    ),
                )
                self.conn.commit()
            lead = self.get_lead(int(existing["id"])) or existing
            return {"lead": lead, "is_duplicate": True}

        lead_id = self._execute(
            """
            INSERT INTO leads (
                user_id, agent_id, name, phone, city, contact_time, current_status, lead_status, consent_text_version,
                consent_confirmed_at, consent_followup, source, campaign, creative, segment, scenario, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                agent_id,
                name,
                phone,
                city,
                contact_time,
                current_status,
                consent_text_version,
                now.isoformat(),
                1 if consent_followup else 0,
                user.get("source"),
                user.get("campaign"),
                user.get("creative"),
                user.get("segment"),
                user.get("scenario"),
                now.isoformat(),
                now.isoformat(),
            ),
        )
        self.update_user(telegram_id, journey_stage="lead_sent", status=current_status, city=city)
        return {"lead": self.get_lead(lead_id) or {"id": lead_id}, "is_duplicate": False}

    def get_lead(self, lead_id: int) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT
                leads.*,
                users.telegram_id,
                users.first_name,
                users.segment AS user_segment,
                users.scenario AS user_scenario,
                agents.agent_status,
                agents.agent_level,
                agents.referral_code
            FROM leads
            JOIN users ON users.id = leads.user_id
            LEFT JOIN agents ON agents.id = leads.agent_id
            WHERE leads.id = ?
            """,
            (lead_id,),
        )

    def list_user_leads(self, telegram_id: int, limit: int = 5) -> list[dict[str, Any]]:
        user = self.get_user(telegram_id)
        if not user:
            return []
        return self._fetchall(
            """
            SELECT * FROM leads
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user["id"], limit),
        )

    def list_leads(
        self,
        *,
        status: str | None = None,
        temperature: str | None = None,
        segment: str | None = None,
        fraud_status: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if status:
            clauses.append("leads.lead_status = ?")
            params.append(status)
        if temperature:
            clauses.append("leads.temperature = ?")
            params.append(temperature)
        if segment:
            clauses.append("COALESCE(leads.segment, users.segment) = ?")
            params.append(segment)
        if fraud_status:
            clauses.append("leads.fraud_status = ?")
            params.append(fraud_status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        return self._fetchall(
            f"""
            SELECT
                leads.*,
                users.telegram_id,
                users.first_name,
                users.segment AS user_segment,
                users.scenario AS user_scenario,
                agents.agent_status,
                agents.agent_level,
                agents.referral_code
            FROM leads
            JOIN users ON users.id = leads.user_id
            LEFT JOIN agents ON agents.id = leads.agent_id
            {where}
            ORDER BY leads.created_at DESC
            LIMIT ?
            """,
            tuple(params),
        )

    def set_lead_state(
        self,
        lead_id: int,
        *,
        lead_status: str | None = None,
        temperature: str | None = None,
        fraud_status: str | None = None,
    ) -> dict[str, Any] | None:
        fields: dict[str, Any] = {}
        if lead_status:
            fields["lead_status"] = lead_status
        if temperature:
            fields["temperature"] = temperature
        if fraud_status:
            fields["fraud_status"] = fraud_status
        if not fields:
            return self.get_lead(lead_id)
        fields["updated_at"] = now_utc().isoformat()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        self._execute(f"UPDATE leads SET {assignments} WHERE id = ?", tuple(fields.values()) + (lead_id,))
        return self.get_lead(lead_id)

    def set_lead_quality(
        self,
        lead_id: int,
        *,
        fraud_score: int,
        fraud_status: str,
        reasons: list[str],
        form_duration_sec: int | None,
        antifraud_version: str = "v1",
    ) -> dict[str, Any] | None:
        self._execute(
            """
            UPDATE leads
            SET fraud_score = ?, fraud_status = ?, fraud_reasons_json = ?, form_duration_sec = ?, antifraud_version = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                fraud_score,
                fraud_status,
                json_dumps(reasons),
                form_duration_sec,
                antifraud_version,
                now_utc().isoformat(),
                lead_id,
            ),
        )
        return self.get_lead(lead_id)

    def lead_quality_context(self, lead_id: int) -> dict[str, Any]:
        lead = self.get_lead(lead_id)
        if not lead:
            return {}
        duplicate_phone_count = self._fetchone(
            """
            SELECT COUNT(*) AS count
            FROM leads
            WHERE phone = ?
              AND created_at >= ?
              AND id != ?
            """,
            (lead["phone"], (now_utc() - timedelta(days=30)).isoformat(), lead_id),
        ) or {"count": 0}
        recent_user_leads = self._fetchone(
            """
            SELECT COUNT(*) AS count
            FROM leads
            WHERE user_id = ?
              AND created_at >= ?
              AND id != ?
            """,
            (lead["user_id"], (now_utc() - timedelta(hours=24)).isoformat(), lead_id),
        ) or {"count": 0}
        user = self.get_user_by_id(int(lead["user_id"])) or {}
        user_age_sec = None
        user_created_at = parse_iso(user.get("created_at"))
        if user_created_at:
            user_age_sec = int((now_utc() - user_created_at).total_seconds())
        agent_recent = {"count": 0}
        agent_totals = {"total": 0, "rejected": 0}
        if lead.get("agent_id"):
            agent_recent = self._fetchone(
                """
                SELECT COUNT(*) AS count
                FROM leads
                WHERE agent_id = ?
                  AND created_at >= ?
                  AND id != ?
                """,
                (lead["agent_id"], (now_utc() - timedelta(minutes=10)).isoformat(), lead_id),
            ) or {"count": 0}
            agent_totals = self._fetchone(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN fraud_status = 'reject' THEN 1 ELSE 0 END) AS rejected
                FROM leads
                WHERE agent_id = ?
                  AND id != ?
                """,
                (lead["agent_id"], lead_id),
            ) or {"total": 0, "rejected": 0}
        return {
            "duplicate_phone_count": int(duplicate_phone_count["count"] or 0),
            "recent_user_leads": int(recent_user_leads["count"] or 0),
            "user_age_sec": user_age_sec,
            "agent_recent_leads": int(agent_recent["count"] or 0),
            "agent_total_leads": int(agent_totals["total"] or 0),
            "agent_rejected_leads": int(agent_totals["rejected"] or 0),
        }

    def mark_lead_synced(self, lead_id: int, *, external_lead_id: str | None = None) -> None:
        now = now_utc().isoformat()
        with self._lock:
            self.conn.execute(
                """
                UPDATE leads
                SET sent_to_partner = 1, sent_to_partner_at = ?, external_lead_id = COALESCE(?, external_lead_id), updated_at = ?
                WHERE id = ?
                """,
                (now, external_lead_id, now, lead_id),
            )
            self.conn.commit()

    def log_event(
        self,
        event_type: str,
        *,
        user_id: int | None = None,
        lead_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._execute(
            """
            INSERT INTO events (user_id, lead_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, lead_id, event_type, json_dumps(payload or {}), now_utc().isoformat()),
        )

    def recent_users(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._fetchall("SELECT * FROM users ORDER BY created_at DESC LIMIT ?", (limit,))

    def recent_activity_by_day(self, days: int = 7) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS events_count
            FROM events
            WHERE created_at >= ?
            GROUP BY substr(created_at, 1, 10)
            ORDER BY day DESC
            """,
            ((now_utc() - timedelta(days=days)).isoformat(),),
        )

    def recent_api_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT * FROM events
            WHERE event_type = 'api_error'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    def quality_summary(self) -> dict[str, Any]:
        by_fraud = self._fetchall(
            "SELECT fraud_status, COUNT(*) AS count FROM leads GROUP BY fraud_status ORDER BY count DESC"
        )
        pending_agents = self._fetchone(
            "SELECT COUNT(*) AS count FROM agents WHERE agent_status = 'pending'"
        ) or {"count": 0}
        approved_agents = self._fetchone(
            "SELECT COUNT(*) AS count FROM agents WHERE agent_status = 'approved'"
        ) or {"count": 0}
        suspicious_agents = self._fetchall(
            """
            SELECT
                agents.id,
                users.first_name,
                users.full_name,
                agents.agent_level,
                COUNT(leads.id) AS total_leads,
                SUM(CASE WHEN leads.fraud_status = 'reject' THEN 1 ELSE 0 END) AS rejected_leads
            FROM agents
            JOIN users ON users.id = agents.user_id
            LEFT JOIN leads ON leads.agent_id = agents.id
            WHERE agents.agent_status = 'approved'
            GROUP BY agents.id
            HAVING COUNT(leads.id) >= 3
               AND (SUM(CASE WHEN leads.fraud_status = 'reject' THEN 1 ELSE 0 END) * 1.0 / COUNT(leads.id)) > 0.30
            ORDER BY rejected_leads DESC, total_leads DESC
            LIMIT 5
            """
        )
        return {
            "by_fraud": by_fraud,
            "pending_agents": int(pending_agents["count"]),
            "approved_agents": int(approved_agents["count"]),
            "suspicious_agents": suspicious_agents,
        }

    def traffic_summary(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT
                COALESCE(NULLIF(users.source, ''), NULLIF(users.utm_source, ''), 'unknown') AS source_key,
                COUNT(DISTINCT users.id) AS users_count,
                COUNT(DISTINCT leads.id) AS leads_count
            FROM users
            LEFT JOIN leads ON leads.user_id = users.id
            GROUP BY COALESCE(NULLIF(users.source, ''), NULLIF(users.utm_source, ''), 'unknown')
            ORDER BY leads_count DESC, users_count DESC
            LIMIT ?
            """,
            (limit,),
        )

    def stage_summary(self) -> dict[str, int]:
        rows = self._fetchall(
            """
            SELECT COALESCE(journey_stage, 'unknown') AS stage_key, COUNT(*) AS count
            FROM users
            GROUP BY COALESCE(journey_stage, 'unknown')
            """
        )
        summary = {str(row["stage_key"]): int(row["count"]) for row in rows}
        summary["started"] = int((self._fetchone("SELECT COUNT(*) AS count FROM users") or {"count": 0})["count"])
        summary["diagnostic_completed"] = int(
            (self._fetchone("SELECT COUNT(*) AS count FROM users WHERE quiz_completed_at IS NOT NULL") or {"count": 0})["count"]
        )
        summary["result_ready"] = int(
            (self._fetchone("SELECT COUNT(*) AS count FROM users WHERE last_result_at IS NOT NULL") or {"count": 0})["count"]
        )
        summary["lead_sent"] = int(
            (self._fetchone("SELECT COUNT(*) AS count FROM leads") or {"count": 0})["count"]
        )
        return summary

    def funnel_summary(self) -> dict[str, Any]:
        total_users = self._fetchone("SELECT COUNT(*) AS count FROM users") or {"count": 0}
        active_users = self._fetchone(
            "SELECT COUNT(*) AS count FROM users WHERE last_seen_at >= ?",
            ((now_utc() - timedelta(days=7)).isoformat(),),
        ) or {"count": 0}
        leads_total = self._fetchone("SELECT COUNT(*) AS count FROM leads") or {"count": 0}
        by_status = self._fetchall(
            "SELECT lead_status, COUNT(*) AS count FROM leads GROUP BY lead_status ORDER BY count DESC"
        )
        by_segment = self._fetchall(
            "SELECT COALESCE(segment, 'unknown') AS segment, COUNT(*) AS count FROM users GROUP BY COALESCE(segment, 'unknown') ORDER BY count DESC"
        )
        by_scenario = self._fetchall(
            "SELECT COALESCE(scenario, 'unknown') AS scenario, COUNT(*) AS count FROM users GROUP BY COALESCE(scenario, 'unknown') ORDER BY count DESC"
        )
        return {
            "total_users": int(total_users["count"]),
            "active_users": int(active_users["count"]),
            "leads_total": int(leads_total["count"]),
            "by_status": by_status,
            "by_segment": by_segment,
            "by_scenario": by_scenario,
        }

    def branch_conversion(self) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT
                COALESCE(users.scenario, 'unknown') AS scenario,
                COUNT(DISTINCT users.id) AS users_count,
                COUNT(DISTINCT leads.id) AS leads_count
            FROM users
            LEFT JOIN leads ON leads.user_id = users.id
            GROUP BY COALESCE(users.scenario, 'unknown')
            ORDER BY leads_count DESC, users_count DESC
            """
        )

    def agent_overview(self, agent_id: int) -> dict[str, Any] | None:
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        stats = self._fetchone(
            """
            SELECT
                COUNT(*) AS total_leads,
                SUM(CASE WHEN fraud_status = 'good' THEN 1 ELSE 0 END) AS good_leads,
                SUM(CASE WHEN fraud_status = 'hold' THEN 1 ELSE 0 END) AS hold_leads,
                SUM(CASE WHEN fraud_status = 'reject' THEN 1 ELSE 0 END) AS reject_leads,
                SUM(CASE WHEN lead_status = 'confirmed' THEN 1 ELSE 0 END) AS confirmed_leads
            FROM leads
            WHERE agent_id = ?
            """,
            (agent_id,),
        ) or {"total_leads": 0, "good_leads": 0, "hold_leads": 0, "reject_leads": 0, "confirmed_leads": 0}
        return {**agent, **stats}

    def export_leads_csv(self) -> Path:
        timestamp = now_utc().strftime("%Y%m%d_%H%M%S")
        target = self.settings.export_dir / f"leads_{timestamp}.csv"
        rows = self._fetchall(
            """
            SELECT
                leads.id,
                leads.name,
                leads.phone,
                leads.city,
                leads.contact_time,
                leads.current_status,
                leads.lead_status,
                leads.temperature,
                leads.agent_id,
                leads.fraud_score,
                leads.fraud_status,
                leads.segment,
                leads.scenario,
                leads.source,
                leads.campaign,
                leads.creative,
                leads.sent_to_partner,
                leads.created_at,
                users.telegram_id,
                agents.referral_code
            FROM leads
            JOIN users ON users.id = leads.user_id
            LEFT JOIN agents ON agents.id = leads.agent_id
            ORDER BY leads.created_at DESC
            """
        )
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "id",
                    "name",
                    "phone",
                    "city",
                    "contact_time",
                    "current_status",
                    "lead_status",
                    "temperature",
                    "agent_id",
                    "fraud_score",
                    "fraud_status",
                    "segment",
                    "scenario",
                    "source",
                    "campaign",
                    "creative",
                    "sent_to_partner",
                    "created_at",
                    "telegram_id",
                    "referral_code",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return target

    def export_agents_csv(self) -> Path:
        timestamp = now_utc().strftime("%Y%m%d_%H%M%S")
        target = self.settings.export_dir / f"agents_{timestamp}.csv"
        rows = self._fetchall(
            """
            SELECT
                agents.id,
                agents.agent_status,
                agents.agent_level,
                agents.referral_code,
                agents.payout_type,
                agents.payout_value,
                agents.application_summary,
                agents.exam_status,
                agents.exam_score,
                agents.exam_total,
                agents.exam_attempts,
                agents.exam_blocked_until,
                agents.approved_at,
                users.telegram_id,
                users.username,
                users.first_name,
                users.full_name
            FROM agents
            JOIN users ON users.id = agents.user_id
            ORDER BY agents.updated_at DESC
            """
        )
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "id",
                    "agent_status",
                    "agent_level",
                    "referral_code",
                    "payout_type",
                    "payout_value",
                    "application_summary",
                    "exam_status",
                    "exam_score",
                    "exam_total",
                    "exam_attempts",
                    "exam_blocked_until",
                    "approved_at",
                    "telegram_id",
                    "username",
                    "first_name",
                    "full_name",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return target

    def lead_owner_user(self, lead_id: int) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT users.*
            FROM leads
            JOIN users ON users.id = leads.user_id
            WHERE leads.id = ?
            """,
            (lead_id,),
        )

    def lead_age_days(self, lead: dict[str, Any]) -> int:
        created_at = parse_iso(lead.get("created_at"))
        if not created_at:
            return 0
        return max(0, (now_utc() - created_at).days)
