import os
import requests
import smtplib
from email.message import EmailMessage
from supabase import create_client
from datetime import datetime, timedelta

# -------------------------
# ENV VARIABLES (GitHub)
# -------------------------
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]   # SERVICE ROLE KEY
OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]

# -------------------------
# CONNECT SUPABASE
# -------------------------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------
# CURRENT TIME (IST)
# -------------------------
ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
current_time = ist_time.strftime("%H:%M")
today_date = str(ist_time.date())

print("================================")
print("Current IST Time :", current_time)
print("Today Date      :", today_date)
print("================================")

# -------------------------
# FETCH USERS
# -------------------------
users = supabase.table("users").select("*").execute().data or []

print("Total users:", len(users))

# -------------------------
# LOOP USERS
# -------------------------
for user in users:
    email = user["email"]
    name = user["name"]
    location = user["location"]
    alert_time = user["alert_time"][:5]
    last_sent = user.get("last_sent_date")

    print("--------------------------------")
    print("User:", email)
    print("Alert time:", alert_time)
    print("Last sent:", last_sent)

    # 1️⃣ Check time
    if alert_time != current_time:
        continue

    # 2️⃣ Avoid duplicate mail
    if last_sent == today_date:
        print("Already sent today → skipping")
        continue

    # -------------------------
    # WEATHER API
    # -------------------------
    weather_url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={location}&appid={OPENWEATHER_API_KEY}&units=metric"
    )

    weather = requests.get(weather_url).json()

    if "main" not in weather:
        print("Weather API error")
        continue

    temp = weather["main"]["temp"]
    condition = weather["weather"][0]["description"]

    # -------------------------
    # EMAIL
    # -------------------------
    msg = EmailMessage()
    msg["Subject"] = f"Daily Weather Alert – {location}"
    msg["From"] = EMAIL_USER
    msg["To"] = email

    msg.set_content(
        f"""
Hello {name},

📍 Location: {location}
🌡 Temperature: {temp}°C
☁ Condition: {condition}

This is your daily weather alert.

Stay safe 🌦️
AI Weather Alert System
"""
    )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)

        print("Email sent to", email)

        # -------------------------
        # UPDATE last_sent_date
        # -------------------------
        supabase.table("users").update({
            "last_sent_date": today_date
        }).eq("email", email).execute()

        print("last_sent_date updated")

    except Exception as e:
        print("Email failed:", e)

print("=========== DONE ===========")
