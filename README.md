# FocusMode

A Windows desktop productivity app that tracks your screen time, blocks distractions, and helps you stay focused — powered by AI-driven daily reviews and a futuristic dark UI.

![Windows](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Features

### Screen Time Tracking
- Real-time monitoring of active applications and window titles
- Automatic categorization (Productive, Social Media, Entertainment, Communication, etc.)
- Hourly screen time breakdown displayed as an interactive line graph with gradient fill
- Daily totals, streaks, and health indicators

### App & Website Blocking
- Block distracting websites and applications during focus sessions
- PIN-protected settings so you can't cheat your way out
- Custom block lists — add any site or app you want to restrict

### AI-Powered Daily Reviews
- Intelligent end-of-day analysis of your screen time habits
- Task completion insights and missed-task breakdowns
- Social media usage warnings with time-worth comparisons
- Motivational nudges tied to your personal weekly goals (~60% chance per review)
- Contextual verdicts: Legendary, Solid, Room to Grow, or Needs Work

### Daily Tasks & Weekly Goals
- Set daily tasks and track completion
- Define weekly goals that carry across days
- Goals feed into AI reviews for personalized motivation
- Streak tracking and rewards system

### Google Calendar Integration
- Connect via iCal URL (no OAuth complexity)
- View today's calendar events directly in the app
- Simple link/unlink from settings

### Notifications
- Windows toast notifications for focus reminders
- Break reminders and session summaries

### Modern UI
- Futuristic dark theme with glassmorphism effects
- Responsive layout — adapts from compact to wide screens
- Smooth canvas-rendered line graph with glowing current-hour indicator
- Neon accent colors and subtle animations

### Professional Installer
- One-click Windows installer built with Inno Setup
- Desktop shortcut, Start Menu entry, and auto-start on boot
- Clean uninstaller that removes all traces

## Tech Stack

- **Python 3.11** — Backend logic, process monitoring, AI engine
- **pywebview** — Native desktop window with HTML/CSS/JS frontend
- **psutil + pywin32** — Windows process and foreground window tracking
- **SQLite** — Local database for all usage data
- **PyInstaller** — Packages into a single executable
- **Inno Setup** — Professional Windows installer

## Getting Started

### Prerequisites
- Windows 10/11
- Python 3.11+

### Install from Source

```bash
git clone https://github.com/nisalpoornaperera/FocusMode.git
cd FocusMode
pip install -r requirements.txt
python main.py
```

### Build Executable

```bash
python -m PyInstaller --onefile --noconsole --uac-admin --icon=assets\icon.ico --add-data "ui;ui" --add-data "assets;assets" --name FocusMode main.py
```

### Build Installer

Requires [Inno Setup](https://jrsoftware.org/isinfo.php):

```bash
iscc installer.iss
```

## Project Structure

```
FocusMode/
├── main.py              # Entry point, window setup, self-install logic
├── src/
│   ├── api.py           # Python↔JS bridge (pywebview js_api)
│   ├── ai_review.py     # AI-powered daily review engine
│   ├── blocker.py       # Site & app blocking
│   ├── database.py      # SQLite database layer
│   ├── gcal_ical.py     # Google Calendar via iCal URL
│   ├── notifier.py      # Windows toast notifications
│   └── tracker.py       # Process & window tracking
├── ui/
│   └── index.html       # Full frontend (HTML + CSS + JS)
├── assets/
│   └── icon.ico         # App icon
├── installer.iss        # Inno Setup installer script
└── requirements.txt     # Python dependencies
```

## License

MIT
