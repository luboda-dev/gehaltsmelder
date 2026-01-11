import unittest
import time
import json
from flask import Flask
from security import check_authorization_and_rate_limit, RATE_LIMIT_STORE

class TestSecurityLogic(unittest.TestCase):

    def setUp(self):
        """Wird vor jedem Test ausgeführt."""
        self.app = Flask(__name__)
        self.secret = "secret-key-for-testing"
        # Speicher für jeden Testlauf leeren
        RATE_LIMIT_STORE.clear()

    def test_auth_success(self):
        """Testet, ob ein korrekter Key akzeptiert wird.""" #docstring
        with self.app.test_request_context(
            headers={"X-Gehaltsmelder-Auth": self.secret},
            environ_base={'REMOTE_ADDR': '127.0.0.1'}
        ):
            result = check_authorization_and_rate_limit(self.secret)
            self.assertIsNone(result, "Erfolgreiche Auth sollte None zurückgeben")

    def test_auth_wrong_key(self):
        """Testet, ob ein falscher Key abgelehnt wird (401)."""
        with self.app.test_request_context(
            headers={"X-Gehaltsmelder-Auth": "falscher-key"},
            environ_base={'REMOTE_ADDR': '127.0.0.1'}
        ):
            response = check_authorization_and_rate_limit(self.secret)
            self.assertIsNotNone(response, "Fehlgeschlagene Auth darf nicht None sein")
            self.assertEqual(response[1], 401)

    def test_minute_rate_limit(self):
        """Testet das Limit von 5 Anfragen pro Minute."""
        with self.app.test_request_context(
            headers={"X-Gehaltsmelder-Auth": self.secret},
            environ_base={'REMOTE_ADDR': '127.0.0.1'}
        ):
            # 5 Anfragen abfeuern (sollten alle None zurückgeben)
            for _ in range(5):
                res = check_authorization_and_rate_limit(self.secret)
                self.assertIsNone(res)
            
            # Die 6. Anfrage muss eine Error-Response liefern
            error_res = check_authorization_and_rate_limit(self.secret)
            self.assertIsNotNone(error_res, "6. Anfrage sollte Error-Response liefern")
            self.assertEqual(error_res[1], 429)

    def test_day_rate_limit_simulation(self):
        """Simuliert das 24h-Limit (50 Anfragen)."""
        client_ip = "127.0.0.1"
        current_time = time.time()
        
        # Wir befüllen den Store manuell mit 50 Einträgen (verteilt über die letzten Stunden)
        # damit das Minuten-Limit (5) nicht triggert, aber das Tages-Limit (50)
        RATE_LIMIT_STORE[client_ip] = [current_time - (i * 200) for i in range(50)]
        
        with self.app.test_request_context(
            headers={"X-Gehaltsmelder-Auth": self.secret},
            environ_base={'REMOTE_ADDR': client_ip}
        ):
            response = check_authorization_and_rate_limit(self.secret)
            self.assertIsNotNone(response, "Anfrage 51 sollte blockiert werden")
            self.assertEqual(response[1], 429, "Das 24h-Limit sollte bei 50 Anfragen greifen")

    def test_different_ips_independent(self):
        """Testet, ob zwei verschiedene IPs eigene Limits haben."""
        # IP 1 braucht ihr Limit auf
        with self.app.test_request_context(
            headers={"X-Gehaltsmelder-Auth": self.secret}, 
            environ_base={'REMOTE_ADDR': '1.1.1.1'}
        ):
            for _ in range(5):
                check_authorization_and_rate_limit(self.secret)
            # Die 6. Anfrage für IP 1 ist 429
            res1 = check_authorization_and_rate_limit(self.secret)
            self.assertEqual(res1[1], 429)

        # IP 2 sollte trotzdem noch anfragen können (bekommt None zurück)
        with self.app.test_request_context(
            headers={"X-Gehaltsmelder-Auth": self.secret}, 
            environ_base={'REMOTE_ADDR': '2.2.2.2'}
        ):
            result = check_authorization_and_rate_limit(self.secret)
            self.assertIsNone(result, "Andere IP sollte nicht blockiert sein")

if __name__ == '__main__':
    unittest.main(verbosity=2)