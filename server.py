from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import base64
import traceback
import json
from threading import Lock

app = Flask(__name__)
CORS(app)

# Mailgun / Zieladresse (in Render als Environment-Variables setzen)
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")         # z.B. sandboxXXXXX.mailgun.org
TO_ADDRESS = os.getenv("TO_ADDRESS")                 # z.B. deine Empfänger-Adresse
FROM_EMAIL = os.getenv("FROM_EMAIL") or f"Gehaltsmelder <mailgun@{MAILGUN_DOMAIN}>"

# Counter-Datei (einfacher Persistenz-Mechanismus)
COUNTER_FILE = "counter.json"
_counter_lock = Lock()

def load_counter():
    try:
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("count", 0))
    except Exception as e:
        print("Fehler beim Laden des Counters:", e)
    return 0

def save_counter(value):
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            json.dump({"count": int(value)}, f)
    except Exception as e:
        print("Fehler beim Speichern des Counters:", e)

# globaler Counter (initial laden)
counter = load_counter()

@app.route("/")
def home():
    return "Job Reporter API läuft ✅"

@app.route("/count", methods=["GET"])
def get_count():
    return jsonify({"count": counter})

@app.route("/report", methods=["POST"])
def report():
    global counter
    try:
        data = request.get_json(force=True)
        print("Received data:", {k: (v if k != "screenshot" else "(screenshot)") for k,v in (data or {}).items()})

        url = data.get("url")
        time = data.get("time")
        screenshot_data = data.get("screenshot")

        if not url or not time:
            return jsonify({"error": "missing data"}), 400

        subject = "Meldung einer Jobanzeige ohne Gehaltsangabe"
        body_text = f"""Eine neue Meldung wurde eingereicht.

🕓 Zeitpunkt: {time}
🔗 Link: {url}

-- Diese Nachricht wurde automatisch vom Browser-Addon 'Gehaltsmelder Österreich' erstellt --
"""

        files = None
        if screenshot_data:
            # screenshot_data ist dataURL: "data:image/png;base64,...."
            try:
                img_bytes = base64.b64decode(screenshot_data.split(",",1)[1])
                files = [("attachment", ("screenshot.png", img_bytes, "image/png"))]
            except Exception as e:
                print("Warnung: Konnte screenshot nicht decodieren:", e)

        # Mailgun API-Aufruf
        if not MAILGUN_API_KEY or not MAILGUN_DOMAIN or not TO_ADDRESS:
            print("Mailgun oder Empfänger nicht konfiguriert.")
            return jsonify({"success": False, "error": "mail-not-configured"}), 500

        resp = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": FROM_EMAIL,
                "to": TO_ADDRESS,
                "subject": subject,
                "text": body_text
            },
            files=files
        )

        if resp.status_code not in (200, 201):
            print("Mailgun error:", resp.status_code, resp.text)
            return jsonify({"success": False, "error": resp.text}), resp.status_code

        # Mail erfolgreich queued -> Counter erhöhen (threadsafe)
        with _counter_lock:
            counter += 1
            save_counter(counter)

        print("✅ Email queued via Mailgun. Counter:", counter)
        return jsonify({"success": True, "count": counter})

    except Exception as e:
        print("❌ Fehler beim Verarbeiten der Meldung:", e)
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
