"""Google Calendar integration for Focus Mode.

Uses public iCal URL — no OAuth, no credentials file needed.
User just pastes their calendar's Secret iCal address from Google Calendar settings.
"""
import os
import re
import json
import urllib.request
import ssl
from datetime import date, datetime, timedelta

TOKEN_DIR = os.path.join(os.environ.get("APPDATA", "."), "FocusMode")
ICAL_URL_FILE = os.path.join(TOKEN_DIR, "gcal_ical_url.txt")


class GoogleCalendar:
    """Fetches events from a Google Calendar iCal feed."""

    def __init__(self):
        self._url = self._load_url()

    def _load_url(self):
        if os.path.exists(ICAL_URL_FILE):
            with open(ICAL_URL_FILE, "r") as f:
                url = f.read().strip()
                if url:
                    return url
        return None

    def is_connected(self):
        return bool(self._url)

    def is_credentials_file_present(self):
        return bool(self._url)

    def connect(self, ical_url):
        ical_url = ical_url.strip()
        if not ical_url.startswith("https://"):
            return False, "URL must start with https://"
        if "calendar.google.com" not in ical_url and "ical" not in ical_url.lower():
            return False, "This doesn't look like a Google Calendar iCal URL"
        # Test fetch
        try:
            events = self._fetch_events(ical_url)
            if events is None:
                return False, "Could not fetch calendar. Check the URL."
        except Exception as e:
            return False, f"Connection failed: {e}"
        os.makedirs(TOKEN_DIR, exist_ok=True)
        with open(ICAL_URL_FILE, "w") as f:
            f.write(ical_url)
        self._url = ical_url
        return True, "Connected successfully"

    def disconnect(self):
        self._url = None
        if os.path.exists(ICAL_URL_FILE):
            os.remove(ICAL_URL_FILE)

    def get_today_events(self):
        if not self._url:
            return []
        events = self._fetch_events(self._url)
        if events is None:
            return []
        today = date.today()
        today_events = []
        for ev in events:
            if ev.get("date") == today.isoformat() or (
                ev.get("start") and ev["start"][:10] == today.isoformat()
            ):
                today_events.append(ev)
        today_events.sort(key=lambda e: e.get("start", e.get("date", "")))
        return today_events

    def _fetch_events(self, url):
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, headers={"User-Agent": "FocusMode/1.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                data = resp.read().decode("utf-8", errors="replace")
            return self._parse_ical(data)
        except Exception:
            return None

    def _parse_ical(self, data):
        events = []
        in_event = False
        current = {}
        for line in data.replace("\r\n ", "").replace("\r\n\t", "").split("\r\n"):
            if not line:
                line_parts = data.replace("\r\n ", "").replace("\r\n\t", "").split("\n")
                continue
            if line.startswith("BEGIN:VEVENT"):
                in_event = True
                current = {}
            elif line.startswith("END:VEVENT"):
                in_event = False
                if current.get("summary"):
                    events.append(current)
                current = {}
            elif in_event:
                if line.startswith("SUMMARY:"):
                    current["summary"] = line[8:]
                elif line.startswith("DTSTART;VALUE=DATE:"):
                    current["date"] = self._format_date(line[19:])
                    current["all_day"] = True
                elif line.startswith("DTSTART:"):
                    dt = self._format_datetime(line[8:])
                    current["start"] = dt
                    current["date"] = dt[:10] if dt else ""
                elif line.startswith("DTSTART;"):
                    # DTSTART;TZID=...:20260419T090000
                    val = line.split(":", 1)[-1] if ":" in line else ""
                    dt = self._format_datetime(val)
                    current["start"] = dt
                    current["date"] = dt[:10] if dt else ""
                elif line.startswith("DTEND;VALUE=DATE:"):
                    current["end_date"] = self._format_date(line[17:])
                elif line.startswith("DTEND:"):
                    current["end"] = self._format_datetime(line[6:])
                elif line.startswith("DTEND;"):
                    val = line.split(":", 1)[-1] if ":" in line else ""
                    current["end"] = self._format_datetime(val)
                elif line.startswith("DESCRIPTION:"):
                    current["description"] = line[12:].replace("\\n", "\n").replace("\\,", ",")
        return events

    def _format_date(self, s):
        s = s.strip()
        if len(s) >= 8:
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return s

    def _format_datetime(self, s):
        s = s.strip()
        if len(s) >= 15:
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}T{s[9:11]}:{s[11:13]}:{s[13:15]}"
        if len(s) >= 8:
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return s

    # Legacy stubs for api.py compatibility
    def authenticate(self):
        return False

    def sync_all_tasks(self, tasks):
        return 0

    def sync_all_goals(self, goals):
        return 0
