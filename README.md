# Automated Headless YouTube Shorts Generator

This project is a 100% free, fully automated, headless video generation and YouTube upload pipeline. It generates motivational YouTube Shorts using Gemini, edge-tts, Pollinations.ai, and MoviePy, and uploads them automatically via GitHub Actions.

## Prerequisites

1.  A Google account and a YouTube channel.
2.  A [Google Gemini API Key](https://aistudio.google.com/app/apikey).
3.  A GitHub Repository to host this code.

## Setup Instructions

### 1. Google Cloud Console Setup (YouTube API)

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project.
3.  Go to **APIs & Services > Library** and enable the **YouTube Data API v3**.
4.  Go to **APIs & Services > OAuth consent screen**.
    *   Choose **External** user type.
    *   Fill in required app information.
    *   Add the scope `https://www.googleapis.com/auth/youtube.upload`.
    *   Add your Google account email as a **Test User** (very important if your app is not verified).
5.  Go to **APIs & Services > Credentials**.
    *   Click **Create Credentials** > **OAuth client ID**.
    *   Application type: **Desktop app**.
    *   Click **Create**.
    *   Download the JSON file and rename it to `client_secrets.json`. Place this file in the root of this project locally.

### 2. Local Authentication (`token.json`)

To allow GitHub Actions to upload on your behalf headlessly, you need to generate a `token.json` file.

1.  Ensure you have python installed locally.
2.  Run `pip install -r requirements.txt`.
3.  Make sure `client_secrets.json` is in the project root.
4.  Run the helper script:
    ```bash
    python auth_setup.py
    ```
5.  A browser window will open asking you to authenticate with your Google account. Ensure you check the box to grant the app permission to upload YouTube videos.
6.  Once successful, a `token.json` file will be created in your directory. **DO NOT COMMIT this file or `client_secrets.json` to public version control.**

### 3. GitHub Actions Setup

1.  Push this code to your GitHub repository.
2.  Go to your repository settings on GitHub: **Settings > Secrets and variables > Actions**.
3.  Click **New repository secret**.
4.  Add the following secrets:
    *   **Name:** `GEMINI_API_KEY`
        *   **Secret:** (Your Gemini API Key string)
    *   **Name:** `YOUTUBE_TOKEN_JSON`
        *   **Secret:** (Copy the *entire contents* of the `token.json` file you generated in step 2 and paste it here).

### 4. Running the Pipeline

*   The GitHub Actions workflow is scheduled to run daily at 12:00 UTC.
*   You can also manually trigger it by going to the **Actions** tab in your repository, selecting the **Daily YouTube Shorts Generator** workflow, and clicking **Run workflow**.