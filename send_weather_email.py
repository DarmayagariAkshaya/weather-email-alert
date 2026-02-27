import os
import requests
import smtplib
from email.message import EmailMessage
from supabase import create_client
from datetime import datetime
from zoneinfo import ZoneInfo

# =============================
# ENVIRONMENT VARIABLES
# =============================
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]

# =============================
# CONNECT TO SUPABASE
# =============================
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================
# GET CURRENT IST TIME
# =============================
ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
current_time = ist_now.strftime("%H:%M")
today_date = ist_now.strftime("%Y-%m-%d")

print("====================================")
print("Current IST Time :", current_time)
print("Today Date       :", today_date)
print("====================================")

# =============================
# FETCH USERS FROM DATABASE
# =============================
response = supabase.table("users").select("*").execute()
users = response.data or []

print("Total users found:", len(users))

# =============================
# LOOP THROUGH USERS
# =============================
for user in users:
    email = user["email"]
    name = user["name"]
    location = user["location"]
    alert_time = user["alert_time"][:5]  # Convert 11:40:00 → 11:40
    last_sent = user.get("last_sent_date")

    print("------------------------------------")
    print("User:", email)
    print("Alert Time:", alert_time)
    print("Last Sent:", last_sent)

    # =============================
    # CHECK IF TIME MATCHES
    # =============================
    if current_time != alert_time:
        print("Time does not match. Skipping.")
        continue

    # =============================
    # PREVENT DUPLICATE EMAIL
    # =============================
    if last_sent == today_date:
        print("Already sent today. Skipping.")
        continue

    print("Time matched. Preparing email...")

    # =============================
    # FETCH WEATHER DATA
    # =============================
    weather_url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={location}&appid={OPENWEATHER_API_KEY}&units=metric"
    )

    weather_response = requests.get(weather_url)
    weather = weather_response.json()

    if "main" not in weather:
        print("Weather API error for:", location)
        continue

    temperature = weather["main"]["temp"]
    condition = weather["weather"][0]["description"]

    # =============================
    # CREATE EMAIL
    # =============================
    msg = EmailMessage()
    msg["Subject"] = f"Daily Weather Alert – {location}"
    msg["From"] = EMAIL_USER
    msg["To"] = email

    msg.set_content(f"""
Hello {name},

📍 Location: {location}
🌡 Temperature: {temperature}°C
☁ Condition: {condition}

Have a great day! 🌤
AI Weather Alert System
""")

    # =============================
    # SEND EMAIL
    # =============================
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)

        print("Email sent successfully to:", email)

        # =============================
        # UPDATE last_sent_date
        # =============================
        supabase.table("users").update({
            "last_sent_date": today_date
        }).eq("email", email).execute()

        print("Database updated for:", email)

    except Exception as e:
        print("Email failed for:", email)
        print("Error:", e)

print("=========== SCRIPT COMPLETED ===========")
