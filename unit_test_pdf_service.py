import unittest
import os
import webbrowser
import tempfile
from pdf_service import create_pdf_from_url

class TestPdfService(unittest.TestCase):

    def test_pdf_generation_success(self):
        """Testet, ob für eine valide URL ein PDF generiert und geöffnet wird."""
        test_url = "https://example.com"
        print(f"\nTeste PDF-Erstellung für {test_url}...")
        
        pdf_bytes = create_pdf_from_url(test_url)
        
        # 1. Grundlegende Validierung
        self.assertIsNotNone(pdf_bytes, "Das PDF sollte nicht None sein.")
        self.assertIsInstance(pdf_bytes, bytes, "Die Rückgabe muss vom Typ 'bytes' sein.")
        self.assertTrue(pdf_bytes.startswith(b"%PDF"), "Daten entsprechen nicht dem PDF-Format.")
        
        # 2. PDF für den User öffnen
        # Wir erstellen eine temporäre Datei, damit wir sie anschauen können
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = tmp_file.name
        
        print(f"✅ Erfolg: PDF generiert ({len(pdf_bytes)} Bytes).")
        print(f"📂 Öffne PDF zur manuellen Kontrolle: {tmp_path}")
        
        # Öffnet das PDF mit dem Standard-PDF-Viewer des Systems
        webbrowser.open(f"file://{tmp_path}")

    def test_pdf_generation_invalid_url(self):
        """Testet das Verhalten bei einer ungültigen URL (sollte None zurückgeben)."""
        invalid_url = "https://diesewebseiteexistiertsicherlichnicht123.com"
        print(f"\nTeste PDF-Erstellung für ungültige URL {invalid_url}...")
        
        pdf_bytes = create_pdf_from_url(invalid_url)
        
        self.assertIsNone(pdf_bytes, "Bei einer ungültigen URL sollte das Ergebnis None sein.")
        print("✅ Erfolg: Ungültige URL wurde korrekt abgefangen.")

    def test_pdf_content_size(self):
        """Testet, ob das generierte PDF eine plausible Mindestgröße hat."""
        test_url = "https://example.com"
        pdf_bytes = create_pdf_from_url(test_url)
        
        # Ein echtes PDF von example.com sollte deutlich über 5KB groß sein
        self.assertGreater(len(pdf_bytes), 5000, "Das PDF ist verdächtig klein (eventuell leer).")
        print(f"✅ Erfolg: PDF-Größe ist plausibel ({len(pdf_bytes)} Bytes).")

if __name__ == '__main__':
    # Wir setzen verbosity=2 für detaillierte Infos in der Konsole
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPdfService)
    unittest.TextTestRunner(verbosity=2).run(suite)