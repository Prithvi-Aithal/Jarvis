# 🧠 Jarvis — AI-Powered Digital Wellness Platform

Jarvis watches how you actually use your devices — not how you think you use them — and turns that raw activity into a stress score, a wellness score, and a handful of nudges that tell you when to put the phone down. It tracks PC and Android usage in the background, runs the numbers through a trained ML model, and surfaces everything in a live dashboard with charts, alerts, and a small wellness chatbot.

No surveys. No manual logging. Just two background scripts, a Flask API, and a React dashboard that updates in near real time.

---

## ✨ What it does

- **Tracks screen time automatically** on Windows (active window polling) and Android (via ADB) — no app installs required on the phone.
- **Predicts a stress level** (`Low` / `Medium` / `High`) from behavioral features using a trained Decision Tree model.
- **Computes a 0–100 Wellness Score** that blends stress, screen time, night usage, breaks, and productive-vs-distracting ratio.
- **Generates smart alerts** in real time — long unbroken sessions, late-night usage, heavy phone use, "distraction mode," and positive reinforcement when you're doing well.
- **Sends phone push notifications** directly via ADB when you've spent too long in a distracting app.
- **Visualizes everything**: 7-day history, an hourly activity heatmap, a stress scatter plot, and category breakdowns.
- **Analyzes Digital Wellbeing screenshots** with Gemini — drop in a screenshot, get a parsed breakdown of app usage and recommendations.
- **Recommends therapy content** (breathing exercises, mood-based Spotify playlists) based on your current stress level.
- **Answers natural-language questions** about your day ("how was my day", "should I take a break", "what should I fix tomorrow") through a lightweight rule-based chat endpoint.

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   tracker.py     │     │ phone_tracker.py │
│  (PC, Windows)   │     │  (Android, ADB)  │
└────────┬─────────┘     └────────┬─────────┘
         │   writes every 5s              │
         └──────────────┬──────────────────┘
                         ▼
              backend/api/activity_log.csv
                         │
                         ▼
              ┌─────────────────────┐
              │   Flask API (app.py) │
              │  feature extraction  │
              │  + stress_model.pkl  │
              └──────────┬───────────┘
                         │ REST / JSON
                         ▼
              ┌─────────────────────┐
              │  React + TS frontend │
              │  (Dashboard, charts,  │
              │   alerts, therapy)    │
              └─────────────────────┘
```

**Data flow:** the two tracker scripts append rows (`timestamp, app, duration_seconds, source`) to a shared CSV every 5 seconds. The Flask backend reads that CSV on each request, computes behavioral features (screen time, continuous usage, night usage, app switches, breaks, productive ratio), feeds them into a pre-trained scikit-learn model, and returns stress/wellness data as JSON. The frontend polls these endpoints and renders the dashboard.

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| PC tracker | Python, `pygetwindow`, Win32 idle detection (`ctypes`) |
| Phone tracker | Python, Android Debug Bridge (ADB), `dumpsys` parsing |
| Backend API | Flask, Flask-CORS, pandas, scikit-learn, Pillow, `google-generativeai` |
| ML model | `DecisionTreeClassifier` (scikit-learn), trained on 6 behavioral features |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, Framer Motion, Recharts, React Router, lucide-react |

---

## 📋 Prerequisites

- **Python 3.10+** (the project ships compiled artifacts for both 3.10 and 3.14, so most recent versions work)
- **Node.js 18+** and npm
- **Windows OS** for `tracker.py` — it uses the Win32 API (`ctypes.windll`) for idle detection and active-window polling. On other platforms idle detection silently no-ops.
- **An Android phone with ADB enabled** (optional) — only needed for phone tracking. USB debugging must be turned on, and the device must be authorized.
- **A Gemini API key** (optional) — only needed for the screenshot-analysis feature.

> ⚠️ **Note on phone tracking:** `phone_tracker.py` was built and tested against a specific device (Nothing Phone, Nothing OS 15 / Android 15) and parses `dumpsys window` / `dumpsys power` output specific to that OS build. It will likely need adjustment (notably the `mFocusedApp` parsing logic and the hardcoded ADB path) for other Android skins or versions.

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/Prithvi-Aithal/Jarvis.git
cd Jarvis
```

### 2. Backend setup

The backend doesn't ship a `requirements.txt`, so install the packages it imports directly:

```bash
cd backend
pip install flask flask-cors pandas scikit-learn joblib numpy pillow google-generativeai python-dotenv
```

If you're on Windows and want PC tracking, also install:

```bash
pip install pygetwindow
```

Create a `.env` file inside `backend/api/` if you want screenshot analysis to work:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

Optionally, point the frontend at a non-default API URL by creating `frontend/.env`:

```env
VITE_API_URL=http://localhost:5000
```

### 4. (Optional) Phone tracking setup

1. Install [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) (ADB).
2. Enable **Developer Options → USB Debugging** on your phone.
3. Open `backend/api/phone_tracker.py` and update the `ADB` constant to point at your local `adb.exe` / `adb` binary path.
4. Connect your phone via USB and run `adb devices` to confirm it's authorized.

---

## ▶️ Running the project

You'll need up to **four terminals**, depending on which features you want active.

```bash
# Terminal 1 — Backend API (required)
cd backend/api
python app.py
# → runs on http://localhost:5000

# Terminal 2 — PC activity tracker (required for PC data)
cd backend/api
python tracker.py

# Terminal 3 — Phone activity tracker (optional)
cd backend/api
python phone_tracker.py

# Terminal 4 — Frontend dashboard
cd frontend
npm run dev
# → runs on http://localhost:5173 (default Vite port)
```

Open the frontend URL in your browser. The dashboard will show "no data yet" until the trackers have written at least a few entries to `activity_log.csv` — give it a minute or two after starting `tracker.py`.

---

## 🔌 API Reference

All endpoints are served from the Flask app at `http://localhost:5000`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/status` | Health check — confirms the backend is running |
| `GET` | `/api/stress` | Current stress level, wellness score, features, and a therapy recommendation |
| `GET` | `/api/features` | Raw computed behavioral features for today |
| `GET` | `/api/wellness` | Wellness score + formatted screen time summary |
| `GET` | `/api/history` | Last 7 days of daily aggregated stats (for charts) |
| `GET` | `/api/heatmap` | Hourly activity intensity grid over the last 7 days |
| `GET` | `/api/alerts` | List of currently active wellness alerts/nudges |
| `POST` | `/api/chat` | Natural-language Q&A about today's activity (`{ "message": "..." }`) |
| `POST` | `/api/analyze-screenshot` | Upload a Digital Wellbeing screenshot (`multipart/form-data`, field name `image`) for Gemini-powered analysis |

---

## 🤖 How the stress prediction works

Every activity entry feeds into six behavioral features, computed per day:

1. **Screen time** — total minutes of tracked activity
2. **Continuous usage** — longest unbroken streak (gaps > 5 min count as a break)
3. **Night usage** — minutes of activity after 10 PM
4. **App switches** — context-switching frequency, capped to filter noise
5. **Breaks** — number of gaps longer than 5 minutes
6. **Productive ratio** — share of time *not* spent in distracting apps (YouTube, Instagram, Netflix, Twitter, TikTok, Facebook, WhatsApp)

These six numbers are passed into a `DecisionTreeClassifier` (`backend/ml/stress_model.pkl`) trained on synthetic/labeled data in `backend/ml/training_data.csv`, which outputs `Low`, `Medium`, or `High`. The wellness score (0–100) is then derived from stress level plus screen time, night usage, productive ratio, and break frequency.

### Retraining the model

```bash
cd backend/ml
python train_model.py
```

This reads `training_data.csv`, trains a fresh `DecisionTreeClassifier` (max depth 5), prints accuracy/cross-validation metrics, and overwrites `stress_model.pkl`.

---

## 📁 Project Structure

```
Jarvis/
├── backend/
│   ├── api/
│   │   ├── app.py              # Flask API — all routes
│   │   ├── tracker.py          # PC activity tracker (Windows)
│   │   ├── phone_tracker.py    # Android activity tracker (ADB)
│   │   └── activity_log.csv    # Shared activity log (auto-generated)
│   └── ml/
│       ├── feature_extractor.py
│       ├── predictor.py        # Loads model, predicts stress level
│       ├── train_model.py      # Trains/retrains the classifier
│       ├── stress_model.pkl    # Trained model artifact
│       └── training_data.csv   # Labeled training data
└── frontend/
    └── src/
        ├── pages/              # Dashboard, Analytics, Therapy, PhoneInsights, Insights, Settings
        ├── components/
        │   ├── charts/         # Line chart, heatmap, scatter plot, category bar chart
        │   ├── dashboard/      # Wellness score, stress gauge, screen time, sleep risk cards
        │   ├── therapy/        # Breathing animation, mood playlist selector
        │   └── notifications/  # Smart in-app notifications
        ├── hooks/useJarvisData.ts
        └── api.ts              # API client
```

---

## 🗺️ Frontend Pages

| Route | Page | Purpose |
|---|---|---|
| `/` | Dashboard | Wellness score, stress gauge, screen time card, sleep risk, smart notifications |
| `/analytics` | Analytics | 7-day trends, category breakdown, hourly heatmap |
| `/therapy` | Therapy | Breathing exercises and mood-based playlists |
| `/phone-insights` | Phone Insights | Phone-specific usage breakdown |
| `/insights` | Insights | Screenshot analysis (upload a Digital Wellbeing screenshot) |
| `/settings` | Settings | App configuration |

---

## 🩹 Known Limitations

- `tracker.py` relies on the Win32 API and only works on Windows.
- `phone_tracker.py` has device-specific parsing logic (built for Nothing OS 15) and a hardcoded local ADB path — update both for your own setup.
- The activity log auto-trims to the last 7 days, so long-term historical trends aren't retained.
- The chat endpoint (`/api/chat`) is keyword/rule-based, not an LLM — only the screenshot-analysis feature uses Gemini.
- The training dataset is small; treat stress predictions as directional rather than clinically meaningful.

---

## 📄 License

No license file is currently included in this repository. Add one (MIT, Apache-2.0, etc.) if you intend for others to reuse this code.

---

*Built by [Prithvi Aithal](https://github.com/Prithvi-Aithal)*
