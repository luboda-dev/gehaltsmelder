# security.py
import time
from flask import request, jsonify
from typing import Optional, Tuple, Dict, List, Any

# --- Rate Limiter Konfiguration ---

# Speichert: {IP_Adresse: [Zeitstempel_Anfrage_1, Zeitstempel_Anfrage_2, ...]}
# Wir verwenden diese Struktur, um die Anfragen für beide Fenster zu überprüfen.
RATE_LIMIT_STORE: Dict[str, List[float]] = {} 

# Kurzfristiges Limit (pro Minute)
LIMIT_MINUTE_WINDOW = 60  # Sekunden
LIMIT_MINUTE_COUNT = 5    # Max. Anfragen

# Langfristiges Limit (pro 24 Stunden)
LIMIT_DAY_WINDOW = 86400  # Sekunden (24 * 60 * 60)
LIMIT_DAY_COUNT = 50      # Max. Anfragen

# --- Kombinierte Sicherheitsfunktion ---

def _check_limit(timestamps: List[float], window: int, count: int, client_ip: str) -> Optional[Tuple[Any, int]]:
    """Hilfsfunktion zur Prüfung eines einzelnen Rate Limits."""
    current_time = time.time()
    
    # Filtere Zeitstempel, die außerhalb des aktuellen Fensters liegen
    recent_timestamps = [t for t in timestamps if t > current_time - window]
    
    if len(recent_timestamps) >= count:
        # Limit überschritten
        oldest_request_time = recent_timestamps[0]
        # Berechne, wie lange der Client warten muss, bis der älteste Request verfällt
        time_to_wait = int(window - (current_time - oldest_request_time))
        
        print(f"⚠️ RATE LIMIT ({window}s) überschritten für IP {client_ip}. Muss {time_to_wait}s warten.")
        
        # 429 Too Many Requests
        return jsonify({
            "error": "rate-limit-exceeded",
            "message": f"Zu viele Anfragen. Bitte warten Sie {time_to_wait} Sekunden."
        }), 429
    
    return None # Limit nicht überschritten

def check_authorization_and_rate_limit(AUTH_SECRET: str) -> Optional[Tuple[Any, int]]:
    """
    Prüft den Public Key und wendet das zweistufige Rate Limit an.
    
    :param AUTH_SECRET: Der erwartete geheime/öffentliche Schlüssel.
    :return: None bei Erfolg, oder eine (response, status_code) Tuple bei Fehler.
    """
    
    # 1. 🔑 Autorisierungsprüfung (Public Key)
    provided_secret = request.headers.get("X-Gehaltsmelder-Auth")

    if not AUTH_SECRET:
        print("🚨 KRITISCHER FEHLER: AUTH_SECRET fehlt im Backend.")
        return jsonify({"error": "server-misconfiguration"}), 500

    if not provided_secret or provided_secret != AUTH_SECRET:
        print(f"❌ UNBEFUGTER ZUGRIFF! Falscher oder fehlender Public Key von IP {request.remote_addr}.")
        return jsonify({"error": "unauthorized"}), 401 

    # 2. ⏱️ Zweistufiges Rate Limiting Prüfung
    client_ip = request.remote_addr
    current_time = time.time()
    
    if client_ip not in RATE_LIMIT_STORE:
        RATE_LIMIT_STORE[client_ip] = []

    # Leere den Store von allen Zeitstempeln, die älter als 24h sind (größtes Fenster)
    RATE_LIMIT_STORE[client_ip] = [
        t for t in RATE_LIMIT_STORE[client_ip] 
        if t > current_time - LIMIT_DAY_WINDOW
    ]

    # a) Kurzfristige Prüfung (5 pro Minute)
    # Wir filtern die Liste für das 1-Minuten-Fenster *innerhalb* der Prüf-Funktion
    minute_limit_error = _check_limit(
        RATE_LIMIT_STORE[client_ip], LIMIT_MINUTE_WINDOW, LIMIT_MINUTE_COUNT, client_ip
    )
    if minute_limit_error:
        return minute_limit_error

    # b) Langfristige Prüfung (50 pro Tag)
    # Da wir bereits nach 24h gefiltert haben, ist die aktuelle Liste die Grundlage.
    day_limit_error = _check_limit(
        RATE_LIMIT_STORE[client_ip], LIMIT_DAY_WINDOW, LIMIT_DAY_COUNT, client_ip
    )
    if day_limit_error:
        return day_limit_error
    
    # 3. Anfrage protokollieren (nur bei Erfolg)
    RATE_LIMIT_STORE[client_ip].append(current_time)
    
    return None # Erfolg
