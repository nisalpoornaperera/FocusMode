import sqlite3
import os
from datetime import date, timedelta


class Database:
    def __init__(self):
        app_data = os.path.join(os.environ.get("APPDATA", "."), "FocusMode")
        os.makedirs(app_data, exist_ok=True)
        self.db_path = os.path.join(app_data, "focusmode.db")
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS usage_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT,
                category TEXT DEFAULT 'other',
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration INTEGER DEFAULT 0,
                date TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS custom_blocked_sites (
                domain TEXT PRIMARY KEY
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS weekly_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                week_start TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reward_type TEXT NOT NULL,
                date TEXT NOT NULL,
                message TEXT
            )
        """)

        defaults = {
            "daily_social_limit": "7200",
            "daily_screen_limit": "28800",
            "healthy_threshold": "7200",
            "moderate_threshold": "14400",
            "porn_blocking": "true",
            "social_blocking": "true",
            "notification_interval": "1800",
            "pin_hash": "",
        }
        for key, value in defaults.items():
            c.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )

        conn.commit()
        conn.close()

    def save_session(self, app_name, window_title, category, start_time, end_time, duration):
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO usage_sessions
               (app_name, window_title, category, start_time, end_time, duration, date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                app_name,
                window_title,
                category,
                start_time.isoformat(),
                end_time.isoformat(),
                int(duration),
                date.today().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def get_today_usage(self):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT category, SUM(duration) as total FROM usage_sessions WHERE date = ? GROUP BY category",
            (date.today().isoformat(),),
        ).fetchall()
        result = {r["category"]: r["total"] for r in rows}
        conn.close()
        return result

    def get_today_app_usage(self):
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT app_name, category, SUM(duration) as total
               FROM usage_sessions WHERE date = ?
               GROUP BY app_name ORDER BY total DESC""",
            (date.today().isoformat(),),
        ).fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result

    def get_weekly_usage(self):
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT date, SUM(duration) as total
               FROM usage_sessions
               WHERE date >= date('now', '-7 days')
               GROUP BY date ORDER BY date"""
        ).fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result

    def get_social_media_time_today(self):
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COALESCE(SUM(duration), 0) as total FROM usage_sessions WHERE date = ? AND category = 'social_media'",
            (date.today().isoformat(),),
        ).fetchone()
        val = row["total"]
        conn.close()
        return val

    def get_total_screen_time_today(self):
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COALESCE(SUM(duration), 0) as total FROM usage_sessions WHERE date = ?",
            (date.today().isoformat(),),
        ).fetchone()
        val = row["total"]
        conn.close()
        return val

    def get_setting(self, key):
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        conn.close()
        return row["value"] if row else None

    def set_setting(self, key, value):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        conn.commit()
        conn.close()

    def get_custom_blocked_sites(self):
        conn = self._get_conn()
        rows = conn.execute("SELECT domain FROM custom_blocked_sites").fetchall()
        result = [r["domain"] for r in rows]
        conn.close()
        return result

    def add_custom_blocked_site(self, domain):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO custom_blocked_sites (domain) VALUES (?)",
            (domain,),
        )
        conn.commit()
        conn.close()

    def remove_custom_blocked_site(self, domain):
        conn = self._get_conn()
        conn.execute("DELETE FROM custom_blocked_sites WHERE domain = ?", (domain,))
        conn.commit()
        conn.close()

    # --- Daily Tasks ---

    def add_task(self, title, task_date=None):
        d = task_date or date.today().isoformat()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO daily_tasks (title, date, completed, created_at) VALUES (?, ?, 0, ?)",
            (title, d, date.today().isoformat()),
        )
        conn.commit()
        conn.close()

    def get_tasks(self, task_date=None):
        d = task_date or date.today().isoformat()
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, title, completed FROM daily_tasks WHERE date = ? ORDER BY id",
            (d,),
        ).fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result

    def toggle_task(self, task_id):
        conn = self._get_conn()
        conn.execute(
            "UPDATE daily_tasks SET completed = CASE WHEN completed = 0 THEN 1 ELSE 0 END WHERE id = ?",
            (task_id,),
        )
        conn.commit()
        conn.close()

    def delete_task(self, task_id):
        conn = self._get_conn()
        conn.execute("DELETE FROM daily_tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

    def get_task_completion_rate(self, task_date=None):
        d = task_date or date.today().isoformat()
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as total, COALESCE(SUM(completed), 0) as done FROM daily_tasks WHERE date = ?",
            (d,),
        ).fetchone()
        total = row["total"]
        done = row["done"]
        conn.close()
        if total == 0:
            return 0, 0, 0.0
        return total, done, done / total

    # --- Weekly Goals ---

    @staticmethod
    def _week_start(d=None):
        today = d or date.today()
        start = today - timedelta(days=today.weekday())
        return start.isoformat()

    def add_weekly_goal(self, title):
        ws = self._week_start()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO weekly_goals (title, week_start, completed, created_at) VALUES (?, ?, 0, ?)",
            (title, ws, date.today().isoformat()),
        )
        conn.commit()
        conn.close()

    def get_weekly_goals(self):
        ws = self._week_start()
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, title, completed FROM weekly_goals WHERE week_start = ? ORDER BY id",
            (ws,),
        ).fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result

    def toggle_weekly_goal(self, goal_id):
        conn = self._get_conn()
        conn.execute(
            "UPDATE weekly_goals SET completed = CASE WHEN completed = 0 THEN 1 ELSE 0 END WHERE id = ?",
            (goal_id,),
        )
        conn.commit()
        conn.close()

    def delete_weekly_goal(self, goal_id):
        conn = self._get_conn()
        conn.execute("DELETE FROM weekly_goals WHERE id = ?", (goal_id,))
        conn.commit()
        conn.close()

    def get_weekly_goal_completion(self):
        ws = self._week_start()
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as total, COALESCE(SUM(completed), 0) as done FROM weekly_goals WHERE week_start = ?",
            (ws,),
        ).fetchone()
        total = row["total"]
        done = row["done"]
        conn.close()
        if total == 0:
            return 0, 0, 0.0
        return total, done, done / total

    # --- Rewards ---

    def add_reward(self, reward_type, message):
        today = date.today().isoformat()
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id FROM rewards WHERE reward_type = ? AND date = ?",
            (reward_type, today),
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO rewards (reward_type, date, message) VALUES (?, ?, ?)",
                (reward_type, today, message),
            )
            conn.commit()
        conn.close()
        return existing is None

    def get_today_rewards(self):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT reward_type, message FROM rewards WHERE date = ?",
            (date.today().isoformat(),),
        ).fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result

    def get_streak(self):
        conn = self._get_conn()
        streak = 0
        d = date.today()
        while True:
            row = conn.execute(
                "SELECT COUNT(*) as total, COALESCE(SUM(completed), 0) as done FROM daily_tasks WHERE date = ?",
                (d.isoformat(),),
            ).fetchone()
            total = row["total"]
            done = row["done"]
            if total == 0:
                if d == date.today():
                    d -= timedelta(days=1)
                    continue
                break
            if done / total >= 0.7:
                streak += 1
                d -= timedelta(days=1)
            else:
                break
        conn.close()
        return streak

    def get_hourly_screen_time(self):
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT CAST(strftime('%H', start_time) AS INTEGER) as hour,
                      SUM(duration) as total
               FROM usage_sessions
               WHERE date = ?
               GROUP BY hour
               ORDER BY hour""",
            (date.today().isoformat(),),
        ).fetchall()
        result = {}
        for r in rows:
            result[r["hour"]] = r["total"]
        conn.close()
        # Return 24-hour array
        return [result.get(h, 0) for h in range(24)]
