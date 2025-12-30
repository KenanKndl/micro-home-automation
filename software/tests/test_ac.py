# ==============================================================================
# PROJE: NEXUS CONTROL HUB - SİSTEM TESTLERİ (BOARD #1 - AC)
# YAZAR: Suude Kaynak - 152120211110
# TARİH: 2025
# AÇIKLAMA: Board #1 (Klima/AC) modülü için birim testlerini (Unit Tests) içerir.
#           Seri haberleşme protokolünün doğruluğunu (mocking ile) simüle eder.
# ==============================================================================

import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

# Path ayarı
current_dir = os.path.dirname(os.path.abspath(__file__))
software_dir = os.path.dirname(current_dir)
src_dir = os.path.join(software_dir, 'src')
sys.path.insert(0, src_dir)

from automation_api import AirConditionerSystemConnection
import constants as const


class TestAirConditionerSystem(unittest.TestCase):
    """
    Board #1 (Klima) Testleri
    """

    def setUp(self):
        self.port = 3
        self.patcher = patch('serial.Serial')
        self.MockSerial = self.patcher.start()
        self.mock_conn = self.MockSerial.return_value
        self.mock_conn.is_open = True
        self.ac = AirConditionerSystemConnection(self.port)
        # Testler arasında görsel ayrım için boşluk
        print("\n" + "-" * 60)

    def tearDown(self):
        self.patcher.stop()

    def test_set_desired_temp_protocol(self):
        """Sıcaklık Ayarlama Testi"""
        print(f"[TEST SENARYOSU] Klima Hedef Sıcaklık Gönderimi")

        test_val = 25.5
        print(f"   -> Girdi: {test_val} °C")

        self.ac.open()
        self.ac.setDesiredTemp(test_val)

        # Beklenen byte'ları hex formatında yazdır
        print(f"   -> Beklenen Protokol: Ondalık=0x85, Tam=0xD9")

        expected_calls = [
            call(bytes([0x85])),
            call(bytes([0xD9]))
        ]
        self.mock_conn.write.assert_has_calls(expected_calls)
        print("   -> SONUÇ: BAŞARILI [✓]")

    def test_update_routine(self):
        """Veri Okuma Döngüsü Testi"""
        print(f"[TEST SENARYOSU] Klima Veri Okuma Döngüsü (Update)")
        print(f"   -> İşlem: PIC'ten sensör verileri isteniyor...")

        self.ac.open()
        self.mock_conn.read.return_value = b'\x00'

        self.ac.update()

        print("   -> Kontrol: Desired(Int/Frac), Ambient(Int/Frac), FanSpeed komutları yollandı mı?")

        expected_requests = [
            call(bytes([const.CMD_AC_GET_DESIRED_TEMP_INT])),
            call(bytes([const.CMD_AC_GET_DESIRED_TEMP_FRAC])),
            call(bytes([const.CMD_AC_GET_AMBIENT_TEMP_INT])),
            call(bytes([const.CMD_AC_GET_AMBIENT_TEMP_FRAC])),
            call(bytes([const.CMD_AC_GET_FAN_SPEED]))
        ]
        self.mock_conn.write.assert_has_calls(expected_requests)
        print("   -> SONUÇ: BAŞARILI [✓]")


if __name__ == '__main__':
    unittest.main()