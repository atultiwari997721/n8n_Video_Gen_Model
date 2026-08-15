# AI Automation Dashboard - Handbook & Setup Guide

This document serves as a comprehensive handbook to understand, replicate, and deploy this AI Automation project. It contains everything a developer needs to know about the architecture, external services, and deployment strategy used to build this SaaS Dashboard.

## 🚀 1. Project Overview
This project is an automated SaaS dashboard containing two primary engines:
1. **YouTube Shorts Engine:** Automatically researches a topic via Gemini, generates AI images, compiles them into a video with text/music using `moviepy`, and uploads it to YouTube.
2. **GitHub Problem Bot:** Automatically generates daily programming problems (Python/JS) via Gemini and commits them to a GitHub repository under a `problems/<date>/` directory.

The system is designed to run **fully unattended**. It features per-user scheduling (select the exact hour to run) and automated history logging.

---

## 🛠 2. Tech Stack & Dependencies
- **Backend:** Python 3.10+, FastAPI, Uvicorn.
- **Database:** SQLite (local) / PostgreSQL (production via SQLAlchemy).
- **Frontend:** Vanilla HTML, CSS, JavaScript (no heavy frontend frameworks).
- **Video Generation:** `moviepy`, `Pillow`, `gTTS` (Google Text-to-Speech), `ImageMagick`.
- **AI/LLM:** `google-generativeai` (Gemini API).
- **Platform APIs:** `google-auth-oauthlib`, `google-api-python-client` (YouTube Data API v3), `PyGithub` (GitHub API).
- **Deployment:** Docker, Render (Free Tier), `cron-job.org`.

*(See `requirements.txt` for exact Python package versions).*

---

## 📁 3. Project Architecture
The codebase is structured to separate concerns between web serving, database management, and automation logic.

```text
n8n_Video_Gen_Model/
├── src/
│   ├── web_app.py           # FastAPI server, endpoints, cron routing, OAuth callbacks
│   ├── database.py          # SQLAlchemy models (User, ActivityLog) and DB connection
│   ├── main.py              # The YouTube Pipeline (Image Gen -> Video Gen -> Upload)
│   ├── github_bot.py        # The GitHub Problem Bot logic
│   ├── youtube_uploader.py  # Google OAuth authentication and YouTube Data API upload logic
│   ├── templates/
│   │   └── index.html       # The Dashboard UI, Settings sync, Logs viewer
├── Dockerfile               # Containerization instructions (installs ImageMagick & dependencies)
├── requirements.txt         # Python dependencies
└── DetaildAndWork.md        # This handbook
```

---

## ⚙️ 4. Google Cloud & OAuth Setup (Crucial)
Because this app allows users to authenticate with their *own* Google accounts to upload videos to their *own* YouTube channels, you must set up Google OAuth.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new Project and navigate to **APIs & Services > Library**.
3. Enable the **YouTube Data API v3**.
4. Navigate to **OAuth consent screen**. Select "External" and fill out the required App name and email fields. Add your email as a "Test User" if the app is in testing.
5. Navigate to **Credentials** -> Create Credentials -> **OAuth client ID**.
6. Select **Web application**.
7. **Authorized redirect URIs:** Add the exact callback URL of your deployed app. 
   - Local testing: `http://localhost:8000/oauth2callback`
   - Production: `https://<your-render-url>.onrender.com/oauth2callback`
8. Copy your **Client ID** and **Client Secret**. (Users will paste these into the Dashboard UI).

---

## 💻 5. Local Development Setup
If you want to run this project on your local machine:

1. **Install System Dependencies:**
   - You MUST install [ImageMagick](https://imagemagick.org/script/download.php) on your machine.
   - For Windows users, install the executable and ensure it is added to your system `PATH`.
2. **Install Python Packages:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Server:**
   ```bash
   uvicorn src.web_app:app --host 0.0.0.0 --port 8000 --reload
   ```
4. **Access the Dashboard:** Go to `http://localhost:8000`

---

## 🌍 6. Deployment on Render
This project relies on heavy system libraries (`ImageMagick`, `ffmpeg`, `gcc` for database drivers). Therefore, it must be deployed using **Docker**.

1. Create a new **Web Service** on [Render](https://render.com/).
2. Connect your GitHub repository.
3. Choose the **Docker** runtime environment (Render will automatically detect the `Dockerfile`).
4. Set the internal port to `8000`.
5. Under **Environment Variables**, add:
   - `DATABASE_URL`: Provide a PostgreSQL connection string (Render provides a free PostgreSQL database you can attach).
6. Deploy! Render will build the Docker container and host the app.

*(Note: Render's free tier spins down the server after 15 minutes of inactivity).*

---

## ⏱ 7. Background Automation & `cron-job.org`
The standout feature of this app is its ability to automatically push code and upload videos at specific times of the day, completely unattended.

**The Problem:** Render's free servers sleep, which kills internal background schedulers.
**The Solution:** An external "Heartbeat" architecture.

1. The FastAPI app exposes a master endpoint: `GET /api/cron/hourly`.
2. When this endpoint is hit, it scans the database for all users whose selected runtime (e.g., `14:00 UTC`) matches the current UTC hour.
3. It spawns asynchronous `BackgroundTasks` to execute those users' pipelines, logging the results in the `ActivityLog` database table.
4. **Action Required:** To power this heartbeat, go to [cron-job.org](https://cron-job.org) (a free cron service).
5. Create a job that pings `https://<your-render-url>.onrender.com/api/cron/hourly` **exactly once every hour**.

This external ping prevents the server from sleeping indefinitely and acts as the master clock that drives all custom user schedules!
