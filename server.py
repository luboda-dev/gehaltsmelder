from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import base64
import traceback

app = Flask(__name__)
CORS(app)  # allow all origins (so your extension can call it)

# Environment variables from Render
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")  # e.g., sandbox123.mailgun.org
TO_ADDRESS = os.getenv("TO_ADDRESS")  # your destination email

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

        # Email content
        subject = "Meldung einer Jobanzeige ohne Gehaltsangabe"
        body = f"""
Eine neue Meldung wurde eingereicht.

🕓 Zeitpunkt: {time}
🔗 Link: {url}

-- Diese Nachricht wurde automatisch vom Browser-Addon 'Job Ad Reporter' erstellt --
"""

        files = None
        if screenshot_data:
            img_bytes = base64.b64decode(screenshot_data.split(",")[1])
            files = [("attachment", ("screenshot.png", img_bytes, "image/png"))]

        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": f"Job Reporter <mailgun@{MAILGUN_DOMAIN}>",
                "to": TO_ADDRESS,
                "subject": subject,
                "text": body,
            },
            files=files
        )

        if response.status_code == 200:
            print("✅ Email sent successfully")
            return jsonify({"success": True, "message": response.json()})
        else:
            print("❌ Mailgun error:", response.text)
            return jsonify({"success": False, "error": response.text}), response.status_code

    except Exception as e:
        print("❌ Fehler beim Senden:", e)
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render provides the port
    app.run(host="0.0.0.0", port=port)
