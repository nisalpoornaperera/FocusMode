import threading
import time
import ctypes
import ctypes.wintypes
from datetime import datetime, date

import psutil
import win32gui
import win32process

SOCIAL_KEYWORDS = [
    "youtube", "facebook", "instagram", "twitter", "x.com",
    "tiktok", "reddit", "snapchat", "pinterest", "linkedin",
    "tumblr", "twitch",
]

BROWSER_EXES = {
    "chrome.exe", "firefox.exe", "msedge.exe", "opera.exe",
    "brave.exe", "vivaldi.exe", "iexplore.exe",
}

PRODUCTIVITY_KEYWORDS = [
    "visual studio", "vscode", "code.exe", "pycharm", "intellij",
    "eclipse", "word", "excel", "powerpoint", "outlook",
    "notion", "obsidian", "terminal", "cmd", "powershell",
    "acrobat", "acrord32", "xournal+", "xournal",
]


class ScreenTimeTracker:
    def __init__(self, db, blocker, notifier):
        self.db = db
        self.blocker = blocker
        self.notifier = notifier
        self.running = False
        self._thread = None
        self._lock = threading.Lock()
        self._cur_app = None
        self._cur_title = None
        self._cur_cat = None
        self._session_start = None
        self._last_notif = 0
        self._current_date = date.today()
        self.idle_threshold = 300  # 5 min

    # --- public ---

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)

    # --- helpers ---

    @staticmethod
    def _idle_seconds():
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            return (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) / 1000.0
        return 0

    @staticmethod
    def _active_window():
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None, None
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return None, None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                app = psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app = "Unknown"
            return app, title
        except Exception:
            return None, None

    @staticmethod
    def _categorize(app, title):
        if not app or not title:
            return "other"
        app_l, title_l = app.lower(), title.lower()
        if app_l in BROWSER_EXES:
            for kw in SOCIAL_KEYWORDS:
                if kw in title_l:
                    return "social_media"
            # Non-social browsing is considered productive
            return "productivity"
        for kw in PRODUCTIVITY_KEYWORDS:
            if kw in title_l or kw in app_l:
                return "productivity"
        return "other"

    @staticmethod
    def _get_display_name(app, title):
        """Return a meaningful app name. For browsers, detect the site."""
        if not app or not title:
            return app or "Unknown"
        app_l = app.lower()
        if app_l in BROWSER_EXES:
            title_l = title.lower()
            if "youtube" in title_l:
                return "YouTube"
            for kw in SOCIAL_KEYWORDS:
                if kw in title_l:
                    return kw.capitalize()
            return app
        return app

    def _save_session(self):
        if self._cur_app and self._session_start:
            now = datetime.now()
            dur = (now - self._session_start).total_seconds()
            if dur >= 2:
                self.db.save_session(
                    self._cur_app, self._cur_title, self._cur_cat,
                    self._session_start, now, dur,
                )

    @staticmethod
    def _fmt(seconds):
        h, rem = divmod(int(seconds), 3600)
        m = rem // 60
        return f"{h}h {m}m" if h else f"{m}m"

    def _check_limits(self):
        # Social-media limit
        social = self.db.get_social_media_time_today()
        limit = int(self.db.get_setting("daily_social_limit") or 7200)
        social_blocking_enabled = self.db.get_setting("social_blocking") == "true"
        
        # Apply blocks if over limit and blocking enabled
        if social >= limit and social_blocking_enabled:
            self.blocker.apply_social_blocks()
            if social == limit or (social - limit) < 4:
                self.notifier.notify(
                    "Social Media Limit Reached",
                    f"You've used {self._fmt(social)} of social media today. Sites are now blocked.",
                )
        # Remove blocks if under limit and currently blocked
        elif social < limit and self.blocker.is_social_blocked():
            self.blocker.remove_social_blocks()

        # Screen-time health notification
        total = self.db.get_total_screen_time_today()
        now = time.time()
        interval = int(self.db.get_setting("notification_interval") or 1800)
        if now - self._last_notif < interval:
            return
        moderate = int(self.db.get_setting("moderate_threshold") or 14400)
        healthy = int(self.db.get_setting("healthy_threshold") or 7200)
        if total > moderate:
            self.notifier.notify(
                "⚠ Unhealthy Screen Time!",
                f"You've been on screen for {self._fmt(total)}. Take a break!",
            )
            self._last_notif = now
        elif total > healthy:
            self.notifier.notify(
                "Screen Time Alert",
                f"{self._fmt(total)} of screen time today. Consider a break.",
            )
            self._last_notif = now

    # --- main loop ---

    def _loop(self):
        while self.running:
            try:
                # Midnight reset
                today = date.today()
                if today != self._current_date:
                    self._current_date = today
                    self.blocker.remove_social_blocks()

                # Idle check
                if self._idle_seconds() > self.idle_threshold:
                    with self._lock:
                        self._save_session()
                        self._cur_app = None
                        self._session_start = None
                    time.sleep(2)
                    continue

                app, title = self._active_window()
                if not app:
                    time.sleep(2)
                    continue

                cat = self._categorize(app, title)
                display = self._get_display_name(app, title)

                with self._lock:
                    if display != self._cur_app or cat != self._cur_cat:
                        self._save_session()
                        self._cur_app = display
                        self._cur_title = title
                        self._cur_cat = cat
                        self._session_start = datetime.now()
                    else:
                        self._cur_title = title

                self._check_limits()
            except Exception:
                pass

            time.sleep(2)
