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
    contextual health advice.
    """
    risk_score = 0
    suggestions = []

    # 1. Temperature Analysis
    if avg_temp > 38:
        risk_score += 60
        suggestions.append("Extreme heat detected. High risk of heat exhaustion; stay in air conditioning.")
    elif avg_temp > 32:
        risk_score += 30
        suggestions.append("Elevated temperatures. Increase fluid intake to prevent dehydration.")
    elif avg_temp < 15:
        risk_score += 25
        suggestions.append("Cold weather alert. Wear thermal layers to protect cardiovascular health.")
    
    # 2. Humidity & Respiratory Health
    if humidity > 75:
        risk_score += 15
        suggestions.append("High humidity may cause respiratory discomfort or trigger asthma.")
    
    # 3. Weather Condition Impact
    cond_lower = condition.lower()
    if "rain" in cond_lower or "drizzle" in cond_lower:
        risk_score += 10
        suggestions.append("Damp conditions: Increased risk of seasonal allergies and joint pain.")
    if "storm" in cond_lower:
        risk_score += 20
        suggestions.append("Severe weather: Stay indoors to avoid injury and high-stress environmental factors.")

    # Final logic
    risk_score = min(risk_score + 10, 100) # Base 10 for environmental shifts
    
    if risk_score > 70:
        level = "🔴 CRITICAL"
    elif risk_score > 40:
        level = "🟡 MODERATE"
    else:
        level = "🟢 LOW"
        suggestions = ["Weather conditions are optimal for outdoor activities. Maintain standard hydration."]

    return risk_score, level, " ".join(suggestions[:2]) # Returns top 2 suggestions

# =============================
# 1️⃣ Setup & Environment
# =============================
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

ist = pytz.timezone("Asia/Kolkata")
now = datetime.now(ist)
current_time = now.strftime("%H:%M")
today_date = now.strftime("%Y-%m-%d")

# =============================
# 2️⃣ Process Users
# =============================
response = supabase.table("users").select("*").execute()
users = response.data

for user in users:
    alert_time = user["alert_time"][:5]
    
    # Check if time is matched (or passed) and not sent today
    if current_time >= alert_time and user.get("last_sent_date") != today_date:
        
        # 3️⃣ Fetch 24h Forecast
        api_key = os.getenv("OPENWEATHER_API_KEY")
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={user['location']}&appid={api_key}&units=metric"
        
        res = requests.get(forecast_url).json()
        if res.get("cod") != "200":
            continue

        # Calculate averages for the next 24 hours (8 blocks of 3 hours)
        forecast_list = res["list"][:8]
        avg_temp = sum(item["main"]["temp"] for item in forecast_list) / 8
        avg_humidity = sum(item["main"]["humidity"] for item in forecast_list) / 8
        main_condition = forecast_list[0]["weather"][0]["description"]

        # 4️⃣ Generate AI Insights
        risk_val, risk_lvl, health_tip = calculate_health_metrics(avg_temp, avg_humidity, main_condition)

        # 5️⃣ Build Email Body
        subject = f"🚨 Health Risk Alert: {risk_lvl} ({user['location']})"
        body = f"""
Daily Health & Weather Intelligence Report

LOCATION: {user['location']}
24H AVG TEMP: {avg_temp:.1f}°C
HUMIDITY: {int(avg_humidity)}%
CONDITION: {main_condition.capitalize()}

---------------------------------------------
AI HEALTH RISK SCORE: {risk_val}/100
RISK LEVEL: {risk_lvl}
---------------------------------------------

HEALTH SUGGESTION:
{health_tip}

Note: This is an AI-generated assessment based on environmental data. 
If you have underlying conditions, please consult your physician.

Stay safe,
Your AI Weather Assistant
"""

        # 6️⃣ Send & Update
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = os.getenv("EMAIL_USER")
        msg["To"] = user["email"]

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
                server.send_message(msg)
            
            # Mark as sent in Supabase
            supabase.table("users").update({"last_sent_date": today_date}).eq("id", user["id"]).execute()
            print(f"Success: Health report sent to {user['email']}")
        except Exception as e:
            print(f"Failed to send to {user['email']}: {e}")

print("Workflow complete.")
