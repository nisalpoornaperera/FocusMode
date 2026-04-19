import json
import hashlib
import threading
import webview

from src.database import Database
from src.blocker import ContentBlocker
from src.tracker import ScreenTimeTracker
from src.notifier import Notifier
from src.gcal_ical import GoogleCalendar
from src.ai_review import AIReviewer


class Api:
    """Python <-> JS bridge exposed to pywebview."""

    def __init__(self):
        self.db = Database()
        self.notifier = Notifier()
        self.blocker = ContentBlocker(self.db)
        self.tracker = ScreenTimeTracker(self.db, self.blocker, self.notifier)
        self.gcal = GoogleCalendar()
        self.reviewer = AIReviewer()

    def start(self):
        self.blocker.apply_porn_blocks()
        self.blocker.apply_custom_blocks()
        self.tracker.start()

    def stop(self):
        self.tracker.stop()

    # ---- PIN Lock ----

    def _hash_pin(self, pin):
        return hashlib.sha256(pin.encode()).hexdigest()

    def has_pin(self):
        pin_hash = self.db.get_setting("pin_hash") or ""
        return json.dumps({"has_pin": bool(pin_hash)})

    def verify_pin(self, pin):
        stored = self.db.get_setting("pin_hash") or ""
        if not stored:
            return json.dumps({"ok": True})
        ok = self._hash_pin(pin) == stored
        return json.dumps({"ok": ok})

    def set_pin(self, pin):
        if not pin or len(pin) < 4:
            return json.dumps({"ok": False, "error": "PIN must be at least 4 digits"})
        self.db.set_setting("pin_hash", self._hash_pin(pin))
        return json.dumps({"ok": True})

    def remove_pin(self):
        self.db.set_setting("pin_hash", "")
        return json.dumps({"ok": True})

    # ---- Data for UI ----

    def get_dashboard(self):
        total = self.db.get_total_screen_time_today()
        social = self.db.get_social_media_time_today()
        usage = self.db.get_today_usage()
        apps = self.db.get_today_app_usage()
        weekly = self.db.get_weekly_usage()
        limit = int(self.db.get_setting("daily_social_limit") or 7200)
        screen_limit = int(self.db.get_setting("daily_screen_limit") or 28800)
        healthy = int(self.db.get_setting("healthy_threshold") or 7200)
        moderate = int(self.db.get_setting("moderate_threshold") or 14400)

        if total > moderate:
            health = "unhealthy"
        elif total > healthy:
            health = "moderate"
        else:
            health = "healthy"

        return json.dumps({
            "total_screen_time": total,
            "social_media_time": social,
            "social_limit": limit,
            "screen_limit": screen_limit,
            "social_blocked": self.blocker.is_social_blocked(),
            "health_status": health,
            "usage_by_category": usage,
            "top_apps": apps[:10],
            "weekly": weekly,
            "task_rate": self.db.get_task_completion_rate()[2],
            "streak": self.db.get_streak(),
            "today_rewards": self.db.get_today_rewards(),
        })

    def get_settings(self):
        keys = [
            "daily_social_limit", "daily_screen_limit",
            "healthy_threshold", "moderate_threshold",
            "porn_blocking", "social_blocking",
            "notification_interval",
        ]
        result = {k: self.db.get_setting(k) for k in keys}
        return json.dumps(result)

    def update_setting(self, key, value):
        allowed = {
            "daily_social_limit", "daily_screen_limit",
            "healthy_threshold", "moderate_threshold",
            "porn_blocking", "social_blocking",
            "notification_interval",
        }
        if key not in allowed:
            return json.dumps({"ok": False, "error": "Unknown setting"})
        self.db.set_setting(key, value)
        if key == "porn_blocking":
            if value == "true":
                self.blocker.apply_porn_blocks()
            else:
                self.blocker.remove_porn_blocks()
        return json.dumps({"ok": True})

    def unblock_social_now(self):
        self.blocker.remove_social_blocks()
        return json.dumps({"ok": True})

    def get_custom_blocked_sites(self):
        sites = self.blocker.get_custom_domains()
        return json.dumps(sites)

    def add_custom_blocked_site(self, url):
        domain = self.blocker.add_custom_domain(url)
        return json.dumps({"ok": True, "domain": domain})

    def remove_custom_blocked_site(self, domain):
        self.blocker.remove_custom_domain(domain)
        return json.dumps({"ok": True})

    # ---- Tasks ----

    def get_tasks(self):
        tasks = self.db.get_tasks()
        total, done, rate = self.db.get_task_completion_rate()
        return json.dumps({
            "tasks": tasks,
            "total": total,
            "done": done,
            "rate": rate,
        })

    def add_task(self, title):
        title = title.strip()
        if not title:
            return json.dumps({"ok": False, "error": "Empty title"})
        self.db.add_task(title)
        self._check_task_rewards()
        return json.dumps({"ok": True})

    def toggle_task(self, task_id):
        self.db.toggle_task(task_id)
        self._check_task_rewards()
        return json.dumps({"ok": True})

    def delete_task(self, task_id):
        self.db.delete_task(task_id)
        return json.dumps({"ok": True})

    # ---- Weekly Goals ----

    def get_weekly_goals(self):
        goals = self.db.get_weekly_goals()
        total, done, rate = self.db.get_weekly_goal_completion()
        return json.dumps({
            "goals": goals,
            "total": total,
            "done": done,
            "rate": rate,
        })

    def add_weekly_goal(self, title):
        title = title.strip()
        if not title:
            return json.dumps({"ok": False, "error": "Empty title"})
        self.db.add_weekly_goal(title)
        return json.dumps({"ok": True})

    def toggle_weekly_goal(self, goal_id):
        self.db.toggle_weekly_goal(goal_id)
        self._check_weekly_rewards()
        return json.dumps({"ok": True})

    def delete_weekly_goal(self, goal_id):
        self.db.delete_weekly_goal(goal_id)
        return json.dumps({"ok": True})

    # ---- Rewards ----

    def get_rewards_data(self):
        rewards = self.db.get_today_rewards()
        streak = self.db.get_streak()
        _, _, task_rate = self.db.get_task_completion_rate()
        _, _, goal_rate = self.db.get_weekly_goal_completion()
        return json.dumps({
            "rewards": rewards,
            "streak": streak,
            "task_rate": task_rate,
            "goal_rate": goal_rate,
        })

    def get_ai_review(self):
        tasks = self.db.get_tasks()
        total_screen = self.db.get_total_screen_time_today()
        social_time = self.db.get_social_media_time_today()
        social_limit = int(self.db.get_setting("daily_social_limit") or 7200)
        screen_limit = int(self.db.get_setting("daily_screen_limit") or 28800)
        top_apps = self.db.get_today_app_usage()[:10]
        usage = self.db.get_today_usage()
        health_thresh = int(self.db.get_setting("healthy_threshold") or 7200)
        moderate_thresh = int(self.db.get_setting("moderate_threshold") or 14400)
        if total_screen > moderate_thresh:
            health = "unhealthy"
        elif total_screen > health_thresh:
            health = "moderate"
        else:
            health = "healthy"
        streak = self.db.get_streak()
        weekly_goals = self.db.get_weekly_goals()

        review = self.reviewer.generate_review(
            tasks=tasks,
            screen_time=total_screen,
            social_time=social_time,
            social_limit=social_limit,
            screen_limit=screen_limit,
            top_apps=top_apps,
            usage_by_category=usage,
            health_status=health,
            streak=streak,
            weekly_goals=weekly_goals,
        )
        return json.dumps({"review": review})

    def _check_task_rewards(self):
        total, done, rate = self.db.get_task_completion_rate()
        if total > 0 and rate >= 0.7:
            msg = f"You completed {done}/{total} tasks today! Keep it up!"
            is_new = self.db.add_reward("daily_tasks", msg)
            if is_new:
                streak = self.db.get_streak()
                notif_msg = f"🎉 {done}/{total} tasks done! "
                if streak > 1:
                    notif_msg += f"🔥 {streak}-day streak!"
                self.notifier.notify("🏆 Daily Goal Achieved!", notif_msg)

    def _check_weekly_rewards(self):
        total, done, rate = self.db.get_weekly_goal_completion()
        if total > 0 and rate >= 1.0:
            msg = f"All {total} weekly goals completed! Amazing week!"
            is_new = self.db.add_reward("weekly_goals", msg)
            if is_new:
                self.notifier.notify(
                    "🏆 Weekly Goals Complete!",
                    f"You achieved all {total} weekly goals! Incredible!",
                )

    def send_startup_reminder(self):
        tasks = self.db.get_tasks()
        total, done, _ = self.db.get_task_completion_rate()
        if total > 0:
            pending = total - done
            if pending > 0:
                task_names = [t["title"] for t in tasks if not t["completed"]]
                preview = ", ".join(task_names[:3])
                if len(task_names) > 3:
                    preview += "..."
                self.notifier.notify(
                    "📋 Today's Tasks",
                    f"You have {pending} task(s) pending: {preview}",
                )
            else:
                self.notifier.notify(
                    "✅ All Tasks Done!",
                    "Great job! All tasks for today are complete.",
                )
        else:
            self.notifier.notify(
                "📋 Plan Your Day",
                "No tasks set for today. Open Focus Mode to add your daily tasks!",
            )

    # ---- Google Calendar (iCal) ----

    def gcal_status(self):
        return json.dumps({
            "connected": self.gcal.is_connected(),
        })

    def gcal_connect(self, ical_url):
        ok, msg = self.gcal.connect(ical_url)
        return json.dumps({"ok": ok, "message": msg})

    def gcal_disconnect(self):
        self.gcal.disconnect()
        return json.dumps({"ok": True})

    def gcal_get_today(self):
        events = self.gcal.get_today_events()
        return json.dumps({"events": events})

    # ---- Hourly Screen Time ----

    def get_hourly_screen_time(self):
        data = self.db.get_hourly_screen_time()
        return json.dumps({"hourly": data})
