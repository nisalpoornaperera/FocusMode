"""Google Calendar integration for Focus Mode.

Syncs daily tasks as calendar events and weekly goals as reminders.
Uses OAuth 2.0 with a local redirect for authentication.
"""
import os
import json
import threading
from datetime import date, datetime, timedelta

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_DIR = os.path.join(os.environ.get("APPDATA", "."), "FocusMode")
TOKEN_PATH = os.path.join(TOKEN_DIR, "gcal_token.json")
CREDS_PATH = os.path.join(TOKEN_DIR, "gcal_credentials.json")
CALENDAR_NAME = "Focus Mode"


class GoogleCalendar:
    """Manages Google Calendar OAuth and event sync."""

    def __init__(self):
        self._service = None
        self._calendar_id = None

    def is_credentials_file_present(self):
        return os.path.exists(CREDS_PATH)

    def is_connected(self):
        if self._service:
            return True
        if os.path.exists(TOKEN_PATH):
            try:
                self._build_service_from_token()
                return self._service is not None
            except Exception:
                return False
        return False

    def save_credentials_json(self, creds_json):
        """Save the OAuth client credentials JSON from the user."""
        os.makedirs(TOKEN_DIR, exist_ok=True)
        if isinstance(creds_json, str):
            data = json.loads(creds_json)
        else:
            data = creds_json
        with open(CREDS_PATH, "w") as f:
            json.dump(data, f)

    def _build_service_from_token(self):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        if not os.path.exists(TOKEN_PATH):
            return
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        if creds and creds.valid:
            self._service = build("calendar", "v3", credentials=creds)

    def authenticate(self):
        """Run the OAuth flow. Returns True on success."""
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        if not os.path.exists(CREDS_PATH):
            return False

        try:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=True)
            os.makedirs(TOKEN_DIR, exist_ok=True)
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
            self._service = build("calendar", "v3", credentials=creds)
            return True
        except Exception as e:
            print(f"Google Calendar auth failed: {e}")
            return False

    def disconnect(self):
        """Remove stored token."""
        self._service = None
        self._calendar_id = None
        if os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)

    def _get_or_create_calendar(self):
        """Get or create the 'Focus Mode' calendar."""
        if self._calendar_id:
            return self._calendar_id
        if not self._service:
            return None

        try:
            cals = self._service.calendarList().list().execute()
            for cal in cals.get("items", []):
                if cal.get("summary") == CALENDAR_NAME:
                    self._calendar_id = cal["id"]
                    return self._calendar_id

            body = {
                "summary": CALENDAR_NAME,
                "description": "Tasks and goals from Focus Mode app",
                "timeZone": self._get_timezone(),
            }
            created = self._service.calendars().insert(body=body).execute()
            self._calendar_id = created["id"]
            return self._calendar_id
        except Exception as e:
            print(f"Calendar creation error: {e}")
            return None

    def _get_timezone(self):
        try:
            import time
            offset = -time.timezone if time.daylight == 0 else -time.altzone
            hours = offset // 3600
            mins = abs(offset) % 3600 // 60
            return f"Etc/GMT{'-' if hours >= 0 else '+'}{abs(hours)}"
        except Exception:
            return "UTC"

    def sync_task(self, title, task_date=None, completed=False):
        """Add a daily task as an all-day event in Google Calendar."""
        if not self._service:
            return None
        cal_id = self._get_or_create_calendar()
        if not cal_id:
            return None

        d = task_date or date.today().isoformat()
        try:
            event = {
                "summary": ("✅ " if completed else "📋 ") + title,
                "description": "Daily task from Focus Mode",
                "start": {"date": d},
                "end": {"date": d},
                "transparency": "transparent",
            }
            result = self._service.events().insert(
                calendarId=cal_id, body=event
            ).execute()
            return result.get("id")
        except Exception as e:
            print(f"Task sync error: {e}")
            return None

    def sync_weekly_goal(self, title, week_start=None):
        """Add a weekly goal as a week-long event with a reminder."""
        if not self._service:
            return None
        cal_id = self._get_or_create_calendar()
        if not cal_id:
            return None

        ws = week_start or date.today()
        if isinstance(ws, str):
            ws = date.fromisoformat(ws)
        we = ws + timedelta(days=6)

        try:
            event = {
                "summary": "🎯 " + title,
                "description": "Weekly goal from Focus Mode",
                "start": {"date": ws.isoformat()},
                "end": {"date": we.isoformat()},
                "transparency": "transparent",
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 1440},
                        {"method": "popup", "minutes": 60},
                    ],
                },
            }
            result = self._service.events().insert(
                calendarId=cal_id, body=event
            ).execute()
            return result.get("id")
        except Exception as e:
            print(f"Goal sync error: {e}")
            return None

    def sync_all_tasks(self, tasks, task_date=None):
        """Sync multiple tasks at once."""
        if not self._service:
            return 0
        count = 0
        for t in tasks:
            result = self.sync_task(t["title"], task_date, bool(t.get("completed")))
            if result:
                count += 1
        return count

    def sync_all_goals(self, goals, week_start=None):
        """Sync multiple goals at once."""
        if not self._service:
            return 0
        count = 0
        for g in goals:
            result = self.sync_weekly_goal(g["title"], week_start)
            if result:
                count += 1
        return count
