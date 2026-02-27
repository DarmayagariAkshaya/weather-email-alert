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

# We use HH:MM format for comparison
current_time = now.strftime("%H:%M")
today_date = now.strftime("%Y-%m-%d")

print(f"Current IST Time: {current_time}")
print(f"Today's Date: {today_date}")

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
    # Convert HH:MM:SS to HH:MM for easy comparison
    alert_time = user["alert_time"][:5]  
    location = user["location"]
    last_sent = user.get("last_sent_date")

    print(f"--- Checking user: {user_email} ---")

    # =============================
    # 5️⃣ Smart Time Match Check
    # =============================
    # Logic: If it is past the user's alert time AND we haven't sent it today yet...
    if current_time >= alert_time:
        
        if last_sent == today_date:
            print(f"Skipping: Already sent an email to {user_email} today.")
            continue

        print(f"Triggering! Current time {current_time} is >= Alert time {alert_time}")

        # =============================
        # 6️⃣ Get Weather Data
        # =============================
        api_key = os.getenv("OPENWEATHER_API_KEY")
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"

        try:
            weather_response = requests.get(weather_url).json()
            if weather_response.get("cod") != 200:
                print(f"Weather fetch failed for {location}: {weather_response.get('message')}")
                continue

            temp = weather_response["main"]["temp"]
            description = weather_response["weather"][0]["description"]

            # =============================
            # 7️⃣ Send Email
            # =============================
            subject = f"🌤 Daily Weather Alert for {location}"
            body = f"""
Hello,

Here is your weather update for {location}:

Temperature: {temp}°C
Condition: {description.capitalize()}

Have a great day!
"""

            message = MIMEText(body)
            message["Subject"] = subject
            message["From"] = os.getenv("EMAIL_USER")
            message["To"] = user_email

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
                server.send_message(message)

            print(f"✅ Email sent successfully to {user_email}!")

            # =============================
            # 8️⃣ Update last_sent_date
            # =============================
            # This is CRITICAL. It prevents the script from sending 
            # another email in the next minute.
            supabase.table("users").update(
                {"last_sent_date": today_date}
            ).eq("id", user["id"]).execute()

            print(f"Database updated for {user_email}.")

        except Exception as e:
            print(f"❌ Error for user {user_email}: {e}")

    else:
        print(f"Not time yet. Alert is at {alert_time}, currently {current_time}.")

print("Script finished.")
