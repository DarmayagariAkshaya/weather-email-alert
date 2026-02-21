import os
import requests
import smtplib
from email.message import EmailMessage
from supabase import create_client
from datetime import datetime

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

current_time = datetime.now().strftime("%H:%M")

users = supabase.table("users").select("*").execute().data

for user in users:
    if user["alert_time"][:5] != current_time:
        continue

    url = f"https://api.openweathermap.org/data/2.5/weather?q={user['location']}&appid={OPENWEATHER_API_KEY}&units=metric"
    weather = requests.get(url).json()

    temp = weather["main"]["temp"]
    condition = weather["weather"][0]["description"]

    msg = EmailMessage()
    msg["Subject"] = f"Weather Alert for {user['location']}"
    msg["From"] = EMAIL_USER
    msg["To"] = user["email"]

    msg.set_content(
        f"""
Hello {user['name']},

Location: {user['location']}
Temperature: {temp}°C
Condition: {condition}

Stay safe 🌦️
"""
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

print("Emails sent")
