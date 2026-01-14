from flask import Flask, request, jsonify, render_template_string, Response
from flask_cors import CORS
import os
import requests
import base64
import traceback
import json
from threading import Lock
from database import init_db, create_report, get_report_count
from security import check_authorization_and_rate_limit

app = Flask(__name__)
CORS(app)

# Datenbank initialisieren
init_db(app)

# Mailgun / Zieladresse (in Render als Environment-Variables setzen)
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")         # z.B. sandboxXXXXX.mailgun.org
TO_ADDRESS = os.getenv("TO_ADDRESS")                 # z.B. deine Empfänger-Adresse
FROM_EMAIL = os.getenv("FROM_EMAIL") or f"Gehaltsmelder <mailgun@{MAILGUN_DOMAIN}>"
AUTH_SECRET = os.getenv("GEHALTSMELDER_SECRET")
ADMIN_SECRET = os.getenv("ADMIN_SECRET")

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
    return jsonify({"count": get_report_count()})
    # return jsonify({"count": counter})

@app.route("/admin/dashboard")
def admin_dashboard():
    # 1. 🔑 Einfache Passwort-Abfrage via URL-Parameter
    provided_key = request.args.get("key")
    if not ADMIN_SECRET or provided_secret != ADMIN_SECRET:
        return "🛑 Zugriff verweigert: Ungültiger Admin-Key", 403

    # 2. 📊 Daten aus der DB laden
    from database import get_all_reports
    reports = get_all_reports()

    # 3. 🎨 Minimales HTML-Template (direkt im Code für den Anfang)
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Gehaltsmelder Admin</title>
        <style>
            body { font-family: sans-serif; margin: 40px; background: #f4f4f9; }
            table { width: 100%; border-collapse: collapse; background: white; }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            th { background-color: #007bff; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .screenshot-btn { background: #28a745; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h2>📋 Eingegangene Meldungen ({{ reports|length }})</h2>
        <table>
            <tr>
                <th>Datum</th>
                <th>URL</th>
                <th>Gemeldet am</th>
                <th>Aktionen</th>
            </tr>
            {% for r in reports %}
            <tr>
                <td>{{ r.created_at.strftime('%d.%m.%Y %H:%M') }}</td>
                <td><a href="{{ r.url }}" target="_blank">Link öffnen</a></td>
                <td>{{ r.reported_at }}</td>
                <td>
                    {% if r.screenshot %}
                        <a class="screenshot-btn" href="/admin/screenshot/{{ r.id }}?key={{ key }}" target="_blank">Screenshot</a>
                    {% else %}
                        Kein Bild
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html_template, reports=reports, key=provided_key)

@app.route("/admin/screenshot/<int:report_id>")
def view_screenshot(report_id):
    provided_key = request.args.get("key")
    if provided_key != ADMIN_SECRET:
        return "Unbefugt", 401

    from database import Report
    report = Report.query.get_or_404(report_id)
    
    if not report.screenshot:
        return "Kein Screenshot vorhanden", 404

    return Response(report.screenshot, mimetype='image/png')

@app.route("/report", methods=["POST"])
def report():
    global counter
    try:
        # ----------------------------------------------------
        # 🔑 Aufruf der kombinierten Sicherheitsprüfung
        # Nur AUTH_SECRET wird übergeben
        auth_error = check_authorization_and_rate_limit(AUTH_SECRET)
        if auth_error:
            return auth_error 
        # ----------------------------------------------------

        
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
        img_bytes = None
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
            
        # ✅ HIER: Datenbank-Speicherung
        create_report(
            url=url,
            reported_at=time,
            screenshot=img_bytes if screenshot_data else None
        )
        
        # Mail erfolgreich queued -> Counter erhöhen (threadsafe)
        with _counter_lock:
            counter += 1
            save_counter(counter)

        print("✅ Email queued via Mailgun. Counter:", counter)
        return jsonify({"success": True, "count": get_report_count()})
        #return jsonify({"success": True, "count": counter})

    except Exception as e:
        print("❌ Fehler beim Verarbeiten der Meldung:", e)
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
