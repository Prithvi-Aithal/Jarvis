import subprocess
import csv
import os
import time
import requests
from datetime import datetime, date
import pandas as pd

LOG_FILE = os.path.join(os.path.dirname(__file__), "activity_log.csv")

# FIX: Use the correct ADB path from your PATH setup
ADB = r"D:\Prithvi\ADB\platform-tools\adb.exe"

API_URL = "http://localhost:5000"

PACKAGE_NAMES = {
    "com.google.android.youtube": "YouTube",
    "com.instagram.android": "Instagram",
    "com.whatsapp": "WhatsApp",
    "com.netflix.mediaclient": "Netflix",
    "com.twitter.android": "Twitter",
    "com.facebook.katana": "Facebook",
    "com.tiktok.android": "TikTok",
    "com.google.android.gm": "Gmail",
    "com.google.android.apps.maps": "Google Maps",
    "com.spotify.music": "Spotify",
    "com.google.android.apps.docs": "Google Docs",
    "com.microsoft.office.word": "Word",
    "com.google.android.chrome": "Chrome (Mobile)",
    "com.samsung.android.browser": "Samsung Browser",
    "com.android.settings": "Settings",
    "com.android.launcher3": "Home Screen",
    "com.nothing.launcher": "Home Screen",       # Nothing OS
    "com.oneplus.launcher": "Home Screen",
    "com.coloros.launcher": "Home Screen",
    "com.oppo.launcher": "Home Screen",
    "com.miui.home": "Home Screen",
    "com.google.android.apps.messaging": "Messages",
    "com.google.android.dialer": "Phone",
    "com.nothing.dialer": "Phone",               # Nothing OS
    "com.google.android.apps.photos": "Photos",
    "com.snapchat.android": "Snapchat",
    "com.reddit.frontpage": "Reddit",
    "com.linkedin.android": "LinkedIn",
    "com.amazon.mShop.android.shopping": "Amazon",
    "com.discord": "Discord",
    "com.supercell.clashofclans": "Clash of Clans",
    "com.application.zomato": "Zomato",
    "com.rapido.passenger": "Rapido",
    "com.microsoft.office.outlook": "Outlook",
}

# Packages that should not be logged as screen time
SKIP_PACKAGES = {
    "com.android.systemui",
    "com.android.launcher",
    "com.android.launcher3",
    "com.nothing.launcher",
    "com.coloros.launcher",
    "com.oppo.launcher",
    "com.oneplus.launcher",
    "com.miui.home",
    "null",
    "",
}

DISTRACTING_APPS = [
    "YouTube", "Instagram", "Netflix", "Twitter",
    "TikTok", "Facebook", "WhatsApp", "Snapchat", "Reddit"
]

notified_milestones = {}
NOTIFY_EVERY_MINS = 10


def send_phone_notification(title: str, message: str):
    """
    FIX: Nothing OS 15 uses the simple 'cmd notification post TAG TEXT' syntax.
    The -S/-t/-T flags do not exist on this Android version and caused silent failure.
    Format: adb shell cmd notification post <TAG> <TEXT>
    TAG is used as the notification identifier (replaces previous notification with same tag).
    We combine title + message into one string since there's no separate title flag.
    """
    try:
        full_text = f"{title}: {message}"
        adb_cmd = [ADB, "shell", "cmd", "notification", "post", "JarvisWellness", full_text]
        result = subprocess.run(adb_cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"[notify] Sent: {full_text}")
        else:
            print(f"[notify] Failed: {result.stderr.strip()}")
    except Exception as e:
        print(f"[notify] Error: {e}")


def get_wellness_score() -> int:
    try:
        res = requests.get(f"{API_URL}/api/wellness", timeout=3)
        data = res.json()
        return data.get("wellness_score", 100)
    except Exception:
        return 100


def check_and_notify(app_name: str, wellness_score: int):
    """Fire notification every 10 mins of distracting app usage."""
    is_distracting = any(d.lower() in app_name.lower() for d in DISTRACTING_APPS)
    if not is_distracting:
        return

    try:
        df = pd.read_csv(LOG_FILE, encoding='utf-8', encoding_errors='ignore',
                         on_bad_lines='skip')
        df["timestamp"] = pd.to_datetime(df["timestamp"], format='mixed')
        today_rows = df[
            (df["timestamp"].dt.date == date.today()) &
            (df["app"] == app_name)
        ]
        usage_mins = (len(today_rows) * 5) // 60
    except Exception:
        return

    if usage_mins == 0:
        return

    current_bucket = (usage_mins // NOTIFY_EVERY_MINS) * NOTIFY_EVERY_MINS
    if current_bucket == 0:
        return

    last_bucket = notified_milestones.get(app_name, 0)
    if current_bucket <= last_bucket:
        return

    notified_milestones[app_name] = current_bucket
    clean_name = app_name.replace("[Phone] ", "")

    if current_bucket <= 20:
        tone = "Still okay, but stay aware."
    elif current_bucket <= 40:
        tone = f"Wellness at {wellness_score}/100 — consider a break."
    else:
        tone = f"Wellness dropping to {wellness_score}/100. Put it down."

    send_phone_notification(
        "Jarvis Wellness",
        f"{current_bucket} mins on {clean_name}. {tone}"
    )


def check_adb_connected() -> bool:
    try:
        result = subprocess.run(
            [ADB, "devices"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().splitlines()
        devices = [l for l in lines[1:] if l.strip().endswith("device")]
        return len(devices) > 0
    except Exception:
        return False


def is_phone_screen_on() -> bool:
    """
    Check if Nothing 3a screen is on using dumpsys power.
    Returns True if Awake, False if Asleep/Dozing.
    """
    try:
        result = subprocess.run(
            [ADB, "shell", "dumpsys", "power"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if "mWakefulness=" in line:
                state = line.split("mWakefulness=")[1].strip().lower()
                return state == "awake"
    except Exception:
        pass
    return True  # fallback: assume on


def get_foreground_app() -> str | None:
    """
    Get foreground app on Nothing 3a (Android 15 / Nothing OS 15).

    FIX: Nothing OS 15 uses mFocusedApp, NOT mCurrentFocus.
    Format: mFocusedApp=ActivityRecord{... u0 com.package.name/Activity t6}
    Parse using ' u0 ' separator then split on '/' for package name.

    Also skips notification shade, systemui, and launcher packages
    so those don't inflate screen time.
    """
    try:
        result = subprocess.run(
            [ADB, "shell", "dumpsys", "window"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            # FIX: Only use mFocusedApp — mCurrentFocus doesn't exist on Nothing OS 15
            if "mFocusedApp" in line and " u0 " in line:
                after_u0 = line.split(" u0 ")[1]
                package = after_u0.split("/")[0].strip()

                # Skip system/launcher/notification shade packages
                if package in SKIP_PACKAGES:
                    return None
                if any(x in package.lower() for x in [
                    "notification", "shade", "systemui", "launcher",
                    "inputmethod", "wallpaper"
                ]):
                    return None

                friendly = PACKAGE_NAMES.get(package)
                if friendly:
                    # Don't log Home Screen as active usage
                    if friendly == "Home Screen":
                        return None
                    return f"[Phone] {friendly}"

                # Unknown package — use last segment of package name
                short = package.split(".")[-1].capitalize()
                return f"[Phone] {short}"

    except Exception as e:
        print(f"[adb] Error: {e}")
    return None


def ensure_log():
    """Create log file with correct 4-column headers if missing."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # FIX: Must include 'source' column to match tracker.py
            writer.writerow(["timestamp", "app", "duration_seconds", "source"])
        print(f"[phone_tracker] Created log file: {LOG_FILE}")


def run_phone_tracker():
    ensure_log()

    print("[phone_tracker] Checking ADB connection...")
    if not check_adb_connected():
        print(
            "[phone_tracker] No device found.\n"
            "  1. Enable USB Debugging on your Nothing 3a\n"
            "  2. Connect via USB and accept the RSA key prompt\n"
            "  3. Run: adb devices\n"
        )
        return

    print("[phone_tracker] Nothing 3a connected. Starting tracker...")
    print(f"[phone_tracker] Logging to: {LOG_FILE}")
    print("[phone_tracker] Skips logging when screen is off.")
    print("[phone_tracker] Wellness notifications fire every 10 mins on distracting apps.")
    print("[phone_tracker] Press Ctrl+C to stop.\n")

    loop_count = 0

    while True:
        # FIX: Skip logging when phone screen is off
        if not is_phone_screen_on():
            print(f"{datetime.now().isoformat()} | [phone] screen off — skipping")
            loop_count += 1
            time.sleep(5)
            continue

        app = get_foreground_app()

        if app:
            timestamp = datetime.now().isoformat()

            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # FIX: Write source='phone' — missing in original, caused ParserError
                writer.writerow([timestamp, app, 5, "phone"])

            # Check notifications every 12 loops (~60 seconds)
            if loop_count % 12 == 0:
                wellness = get_wellness_score()
                check_and_notify(app, wellness)

            # Print running phone total
            try:
                df = pd.read_csv(LOG_FILE, encoding='utf-8', encoding_errors='ignore',
                                 on_bad_lines='skip')
                df["timestamp"] = pd.to_datetime(df["timestamp"], format='mixed')
                today_phone = df[
                    (df["timestamp"].dt.date == date.today()) &
                    (df["app"].str.startswith("[Phone]", na=False))
                ]
                total_mins = (len(today_phone) * 5) // 60
                total_secs = (len(today_phone) * 5) % 60
                print(f"{timestamp} | {app} | Phone today: {total_mins}m {total_secs}s")
            except Exception:
                print(f"{timestamp} | {app}")
        else:
            print(f"{datetime.now().isoformat()} | [phone] screen on, no foreground app")

        loop_count += 1
        time.sleep(5)


if __name__ == "__main__":
    run_phone_tracker()
