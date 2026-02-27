import os
from supabase import create_client
from datetime import datetime
import pytz
import smtplib
from email.mime.text import MIMEText
import requests

# =============================
# 🧬 AI RISK & HEALTH ENGINE
# =============================
def calculate_health_metrics(avg_temp, humidity, condition):
    """
    Calculates a risk score from 0-100 and provides 
    contextual health advice based on environmental data.
    """
    risk_score = 10  # Base level for environmental change
    suggestions = []

    # 1. Temperature Analysis
    if avg_temp > 38:
        risk_score += 60
        suggestions.append("⚠️ Extreme heat: High risk of heatstroke. Stay in cooled environments.")
    elif avg_temp > 32:
        risk_score += 30
        suggestions.append("☀️ High Temp: Increased dehydration risk. Drink 1L extra water today.")
    elif avg_temp < 15:
        risk_score += 25
        suggestions.append("🥶 Cold Alert: Wear thermal layers to protect cardiovascular health.")
    
    # 2. Humidity Impact
    if humidity > 75:
        risk_score += 15
        suggestions.append("💧 High humidity: May trigger respiratory discomfort or asthma.")
    
    # 3. Weather Condition Impact
    cond_lower = condition.lower()
    if "rain" in cond_lower or "drizzle" in cond_lower:
        risk_score += 10
        suggestions.append("☔ Damp conditions: Higher risk of joint pain and seasonal allergies.")
    if "storm" in cond_lower:
        risk_score += 20
        suggestions.append("🌩️ Severe weather: Stay indoors to avoid environmental stress.")

    # Final Score Normalization
    risk_score = min(risk_score, 100)
    
    if risk_score > 70:
        level = "🔴 CRITICAL"
    elif risk_score > 40:
        level = "🟡 MODERATE"
    else:
        level = "🟢 LOW"
        if not suggestions:
            suggestions.append("Conditions are optimal. Maintain standard physical activity.")

    return risk_score, level, " ".join(suggestions[:2])

# =============================
# 1️⃣ Setup & Environment
# =============================
print("Starting Weather & Health Workflow...")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise Exception("Missing Supabase credentials in Environment Secrets!")

supabase = create_client(url, key)

# Get current IST time for comparison
ist = pytz.timezone("Asia/Kolkata")
now = datetime.now(ist)
current_time = now.strftime("%H:%M")
today_date = now.strftime("%Y-%m-%d")

print(f"Current Time (IST): {current_time}")

# =============================
# 2️⃣ Fetch Users from Supabase
# =============================
try:
    response = supabase.table("users").select("*").execute()
    users = response.data
except Exception as e:
    print(f"Failed to fetch users: {e}")
    exit()

# =============================
# 3️⃣ Main Processing Loop
# =============================
for user in users:
    try:
        user_email = user["email"]
        alert_time = user["alert_time"][:5]  # Format HH:MM
        location = user["location"]
        last_sent = user.get("last_sent_date")

        print(f"\n--- Checking: {user_email} ---")

        # 🕒 Check if it's time to send (Current time is >= Alert time)
        if current_time >= alert_time:
            
            # Check if already sent today
            if last_sent == today_date:
                print(f"Skipping: {user_email} already received their mail today.")
                continue

            print(f"Triggering for {user_email} (Alert: {alert_time})")

            # 🌦️ Fetch 5-Day/3-Hour Forecast for 24h Average
            api_key = os.getenv("OPENWEATHER_API_KEY")
            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={location}&appid={api_key}&units=metric"
            
            weather_data = requests.get(forecast_url).json()
            if weather_data.get("cod") != "200":
                print(f"Weather API error for {location}: {weather_data.get('message')}")
                continue

            # Calculate 24h averages (8 forecast blocks of 3 hours each)
            forecast_list = weather_data["list"][:8]
            avg_temp = sum(item["main"]["temp"] for item in forecast_list) / 8
            avg_hum = sum(item["main"]["humidity"] for item in forecast_list) / 8
            main_condition = forecast_list[0]["weather"][0]["description"]

            # 🧠 Generate AI Risk Score and Suggestions
            risk_val, risk_lvl, health_tip = calculate_health_metrics(avg_temp, avg_hum, main_condition)

            # ✉️ Build Email
            subject = f"🩺 Health & Weather Report: {risk_lvl}"
            body = f"""
AI Weather-Health Intelligence Report

LOCATION: {location}
DATE: {today_date}
---------------------------------------------
24H AVG TEMP: {avg_temp:.1f}°C
AVG HUMIDITY: {int(avg_hum)}%
EXPECTED CONDITION: {main_condition.capitalize()}

---------------------------------------------
📊 AI HEALTH RISK SCORE: {risk_val}/100
⚠️ RISK LEVEL: {risk_lvl}
---------------------------------------------

💡 HEALTH SUGGESTION:
{health_tip}

Stay safe and healthy!
Your AI Assistant
"""

            # 📤 Send Email
            message = MIMEText(body)
            message["Subject"] = subject
            message["From"] = os.getenv("EMAIL_USER")
            message["To"] = user_email

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
                server.send_message(message)

            # 💾 Update Supabase (Using 'email' as the identifier)
            supabase.table("users").update(
                {"last_sent_date": today_date}
            ).eq("email", user_email).execute()

            print(f"✅ Success: Report sent and DB updated for {user_email}")

        else:
            print(f"Waiting: Current time {current_time} hasn't reached alert time {alert_time}")

    except Exception as e:
        # If one user fails, the script continues to the next user
        print(f"❌ Error processing {user.get('email', 'Unknown')}: {e}")

print("\nWorkflow complete.")
