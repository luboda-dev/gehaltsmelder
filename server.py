from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64
import os
import traceback

app = Flask(__name__)
CORS(app)  # allow all origins (so your extension can call it)

# Environment variables from Render
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TO_ADDRESS = os.getenv("TO_ADDRESS", EMAIL_USER)  # default to same email if not set

@app.route("/")
def home():
    return "Job Reporter API läuft ✅"

@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.get_json()
        print("Received data:", data)

        url = data.get("url")
        time = data.get("time")
        screenshot_data = data.get("screenshot")

        if not url or not time:
            return jsonify({"error": "missing data"}), 400

        # Create email
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = TO_ADDRESS
        msg["Subject"] = "Meldung einer Jobanzeige ohne Gehaltsangabe"

        body = f"""
Eine neue Meldung wurde eingereicht.

🕓 Zeitpunkt: {time}
🔗 Link: {url}

-- Diese Nachricht wurde automatisch vom Browser-Addon 'Job Ad Reporter' erstellt --
"""
        msg.attach(MIMEText(body, "plain"))

        if screenshot_data:
            img_data = base64.b64decode(screenshot_data.split(",")[1])
            part = MIMEBase("application", "octet-stream")
            part.set_payload(img_data)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment; filename=screenshot.png")
            msg.attach(part)

        # Send email via Gmail
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print("✅ Email sent successfully")
        return jsonify({"success": True})

    except Exception as e:
        print("❌ Fehler beim Senden:", e)
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render provides the port
    app.run(host="0.0.0.0", port=port)
