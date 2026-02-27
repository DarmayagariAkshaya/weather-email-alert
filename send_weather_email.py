import os
from supabase import create_client
from datetime import datetime
import pytz
import smtplib
from email.mime.text import MIMEText
import requests

print("Script started...")

# =============================
# 1️⃣ Connect to Supabase
# =============================

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise Exception("Supabase credentials not found!")

supabase = create_client(url, key)

# =============================
# 2️⃣ Get Current IST Time
# =============================

ist = pytz.timezone("Asia/Kolkata")
now = datetime.now(ist)

current_time = now.strftime("%H:%M")
today_date = now.strftime("%Y-%m-%d")

print("Current IST Time:", current_time)

# =============================
# 3️⃣ Fetch Users from Database
# =============================

response = supabase.table("users").select("*").execute()
users = response.data

if not users:
    print("No users found.")
    exit()

# =============================
# 4️⃣ Loop Through Users
# =============================

for user in users:

    user_email = user["email"]
    alert_time = user["alert_time"][:5]  # convert HH:MM:SS to HH:MM
    location = user["location"]
    last_sent = user.get("last_sent_date")

    print(f"Checking user: {user_email} | Alert Time: {alert_time}")

    # =============================
    # 5️⃣ Time Match Check
    # =============================

    if alert_time == current_time:

        if last_sent == today_date:
            print("Already sent today. Skipping...")
            continue

        print("Time matched. Fetching weather...")

        # =============================
        # 6️⃣ Get Weather Data
        # =============================

        api_key = os.getenv("OPENWEATHER_API_KEY")
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"

        weather_response = requests.get(weather_url).json()

        if weather_response.get("cod") != 200:
            print("Weather fetch failed.")
            continue

        temp = weather_response["main"]["temp"]
        description = weather_response["weather"][0]["description"]

        # =============================
        # 7️⃣ Send Email
        # =============================

        subject = "🌤 Daily Weather Alert"
        body = f"""
Hello,

Here is your weather update for {location}:

Temperature: {temp}°C
Condition: {description}

Have a great day!
"""

        message = MIMEText(body)
        message["Subject"] = subject
        message["From"] = os.getenv("EMAIL_USER")
        message["To"] = user_email

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
                server.send_message(message)

            print("Email sent successfully!")

            # =============================
            # 8️⃣ Update last_sent_date
            # =============================

            supabase.table("users").update(
                {"last_sent_date": today_date}
            ).eq("id", user["id"]).execute()

            print("Database updated.")

        except Exception as e:
            print("Email failed:", e)

print("Script finished.")
