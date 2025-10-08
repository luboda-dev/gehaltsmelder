from flask import Flask, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64
import os

app = Flask(__name__)

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TO_ADDRESS = os.getenv("TO_ADDRESS", "test@example.com")

@app.route("/")
def home():
    return "Job Reporter API läuft ✅"

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    url = data.get("url")
    time = data.get("time")
    screenshot_data = data.get("screenshot")

    if not url or not time:
        return jsonify({"error": "missing data"}), 400

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

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        return jsonify({"success": True})
    except Exception as e:
        print("Fehler beim Senden:", e)
        return jsonify({"success": False, "error": str(e)}), 500
