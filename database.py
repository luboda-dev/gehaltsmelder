# database.py
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from typing import Optional, List

db = SQLAlchemy()

# --------------------
# Datenbank-Modell
# --------------------

class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Text, nullable=False)
    reported_at = db.Column(db.Text, nullable=False)
    screenshot = db.Column(db.LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "reported_at": self.reported_at,
            "has_screenshot": self.screenshot is not None,
            "created_at": self.created_at.isoformat()
        }

# --------------------
# Initialisierung
# --------------------

def init_db(app):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, "reports.db")

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

# --------------------
# DB-Service-Funktionen
# --------------------

def create_report(
    url: str,
    reported_at: str,
    screenshot: Optional[bytes] = None
) -> Report:
    """
    Erstellt und speichert eine neue Meldung.
    """
    report = Report(
        url=url,
        reported_at=reported_at,
        screenshot=screenshot
    )

    db.session.add(report)
    db.session.commit()
    return report


def get_all_reports() -> List[Report]:
    """
    Gibt alle gespeicherten Meldungen zurück.
    """
    return Report.query.order_by(Report.created_at.desc()).all()


def get_report_count() -> int:
    """
    Gibt die Anzahl der Meldungen zurück.
    """
    return Report.query.count()
