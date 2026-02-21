import os
import requests
import smtplib
from email.message import EmailMessage
from supabase import create_client
from datetime import datetime, timedelta

# -----------------------------
# 1. READ ENVIRONMENT VARIABLES
# -----------------------------
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]   # Service Role Key
OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]

# -----------------------------
# 2. CONNECT TO SUPABASE
# -----------------------------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# 3. GET CURRENT TIME IN IST
#    (GitHub runs in UTC)
# -----------------------------
ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
current_time = ist_time.strftime("%H:%M")

print("===================================")
print("Current IST Time:", current_time)
print("===================================")

# -----------------------------
# 4. FETCH USERS FROM SUPABASE
# -----------------------------
response = supabase.table("users").select("*").execute()
users = response.data or []

print(f"Total users found: {len(users)}")

# -----------------------------
# 5. PROCESS EACH USER
# -----------------------------
for user in users:
    user_email = user["email"]
    user_name = user["name"]
    user_location = user["location"]
    user_alert_time = user["alert_time"][:5]  # HH:MM

    print("-----------------------------------")
    print("User email      :", user_email)
    print("DB alert_time   :", user_alert_time)
    print("Current IST time:", current_time)

    # Check alert time
    if user_alert_time != current_time:
        print("❌ Time not matched, skipping user")
        continue

    print("✅ Time matched, sending email")

    # -----------------------------
    # 6. FETCH WEATHER DATA
    # -----------------------------
    weather_url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={user_location}&appid={OPENWEATHER_API_KEY}&units=metric"
    )

    weather_response = requests.get(weather_url)
    weather_data = weather_response.json()

    # Safety check
    if weather_response.status_code != 200:
        print("❌ Weather API error:", weather_data)
        continue

    temperature = weather_data["main"]["temp"]
    condition = weather_data["weather"][0]["description"]

    # -----------------------------
    # 7. CREATE EMAIL
    # -----------------------------
    msg = EmailMessage()
    msg["Subject"] = f"Weather Alert for {user_location}"
    msg["From"] = EMAIL_USER
    msg["To"] = user_email

    msg.set_content(
        f"""
Hello {user_name},

🌍 Location: {user_location}
🌡 Temperature: {temperature}°C
☁ Condition: {condition}

This is your scheduled weather alert.

Stay safe 🌦️
AI Weather Alert System
"""
    )

    # -----------------------------
    # 8. SEND EMAIL USING GMAIL SMTP
    # -----------------------------
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)

        print("📧 Email sent successfully to", user_email)

    except Exception as e:
        print("❌ Email sending failed:", e)

print("===================================")
print("Script execution completed")
print("===================================")
