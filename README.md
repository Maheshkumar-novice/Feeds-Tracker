# RSS Reader

A minimal RSS/Atom feed reader built with Flask and vanilla JavaScript.

## Setup

```bash
uv sync
uv run app.py
```

Open `http://localhost:5000`

## Authentication (Optional)

To secure write operations (add/delete feeds), set an `ADMIN_TOKEN`:

```bash
ADMIN_TOKEN=secret uv run app.py
```

- **Read:** Public
- **Write:** Requires Login (click "🔒 Login" in sidebar)

## Features

- Two-pane layout (feeds + articles)
- Add/delete/refresh feeds
- Mobile responsive
- 8 default tech blogs included

## Tech Stack

Flask • feedparser • SQLite • Vanilla JS
