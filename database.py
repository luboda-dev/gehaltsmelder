# database.py

import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy-Instanz (wird in server.py initialisiert)
db = SQLAlchemy()

# --------------------
# Datenbank-Modell
# --------------------

class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)  # automatische ID
    url = db.Column(db.Text, nullable=False)
    reported_at = db.Column(db.Text, nullable=False)  # Zeitstempel vom Client
    screenshot = db.Column(db.LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Hilfsfunktion für JSON-Ausgaben"""
        return {
            "id": self.id,
            "url": self.url,
            "reported_at": self.reported_at,
            "has_screenshot": self.screenshot is not None,
            "created_at": self.created_at.isoformat()
        }

# --------------------
# Hilfsfunktion: DB initialisieren
# --------------------

def init_db(app):
    """
    Verbindet SQLAlchemy mit der Flask-App
    und erstellt alle Tabellen (falls nicht vorhanden).
    """

    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, "reports.db")

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
