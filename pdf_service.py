# pdf_service.py
from playwright.sync_api import sync_playwright
import time

def create_pdf_from_url(url: str) -> bytes:
    """
    Besucht die URL im Hintergrund und erstellt einen PDF-Abdruck.
    """
    with sync_playwright() as p:
        # Browser starten (headless=True ist Standard)
        browser = p.chromium.launch()
        
        # Neues Browser-Fenster öffnen
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        try:
            print(f"🌐 Erstelle PDF für: {url}")
            # Ändere wait_until von 'networkidle' zu 'domcontentloaded'
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Gib der Seite 2 Sekunden Zeit für Bilder/Styles
            time.sleep(2) 
            
            pdf_bytes = page.pdf(format="A4", print_background=True)
            return pdf_bytes
        except Exception as e:
            print(f"❌ Fehler beim PDF-Druck: {e}")
            return None
        finally:
            browser.close()