# tests/test_database.py

import pytest
from flask import Flask

from database import (
    db,
    init_db,
    create_report,
    get_report_count,
    Report
)

# --------------------
# Test-App Fixture
# --------------------

@pytest.fixture
def app():
    """
    Erstellt eine Flask-App mit In-Memory-SQLite-Datenbank
    für isolierte Unit-Tests.
    """
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


# --------------------
# Tests: Report-Erstellung
# --------------------

def test_create_report_without_screenshot(app):
    """
    Testet das Erstellen eines Reports ohne Screenshot.
    """
    with app.app_context():
        report = create_report(
            url="https://example.com/job1",
            reported_at="2026-01-01T12:00:00",
            screenshot=None
        )

        assert report.id is not None
        assert report.url == "https://example.com/job1"
        assert report.reported_at == "2026-01-01T12:00:00"
        assert report.screenshot is None


def test_create_report_with_screenshot(app):
    """
    Testet das Erstellen eines Reports mit Screenshot.
    """
    with app.app_context():
        fake_image = b"fake-binary-image-data"

        report = create_report(
            url="https://example.com/job2",
            reported_at="2026-01-01T13:00:00",
            screenshot=fake_image
        )

        assert report.id is not None
        assert report.screenshot == fake_image


# --------------------
# Tests: Datenbankinhalte
# --------------------

def test_report_is_persisted(app):
    """
    Prüft, ob ein Report tatsächlich in der Datenbank gespeichert wird.
    """
    with app.app_context():
        create_report(
            url="https://example.com/job3",
            reported_at="2026-01-01T14:00:00"
        )

        reports = Report.query.all()

        assert len(reports) == 1
        assert reports[0].url == "https://example.com/job3"


def test_multiple_reports(app):
    """
    Testet das Speichern mehrerer Reports.
    """
    with app.app_context():
        create_report(
            url="https://example.com/job4",
            reported_at="2026-01-01T15:00:00"
        )
        create_report(
            url="https://example.com/job5",
            reported_at="2026-01-01T16:00:00"
        )

        reports = Report.query.all()

        assert len(reports) == 2


# --------------------
# Tests: Counter-Funktion
# --------------------

def test_get_report_count_empty(app):
    """
    Zählt Reports bei leerer Datenbank.
    """
    with app.app_context():
        assert get_report_count() == 0


def test_get_report_count_after_inserts(app):
    """
    Zählt Reports nach dem Einfügen.
    """
    with app.app_context():
        create_report(
            url="https://example.com/job6",
            reported_at="2026-01-01T17:00:00"
        )
        create_report(
            url="https://example.com/job7",
            reported_at="2026-01-01T18:00:00"
        )

        assert get_report_count() == 2


# --------------------
# Tests: to_dict()
# --------------------

def test_report_to_dict(app):
    """
    Testet die to_dict()-Hilfsfunktion des Modells.
    """
    with app.app_context():
        report = create_report(
            url="https://example.com/job8",
            reported_at="2026-01-01T19:00:00"
        )

        data = report.to_dict()

        assert data["id"] == report.id
        assert data["url"] == report.url
        assert data["reported_at"] == report.reported_at
        assert data["has_screenshot"] is False
        assert "created_at" in data
