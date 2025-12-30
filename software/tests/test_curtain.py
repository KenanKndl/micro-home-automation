# ==============================================================================
# PROJE: NEXUS CONTROL HUB - SİSTEM TESTLERİ (BOARD #2 - SENSORS)
# YAZAR: Suude Kaynak - 152120211110
# TARİH: 2025
# AÇIKLAMA: Board #2 (Perde ve Sensörler) modülü için birim testlerini içerir.
#           Veri ayrıştırma (parsing) ve komut gönderim senaryolarını test eder.
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

from automation_api import CurtainControlSystemConnection
import constants as const


class TestCurtainControlSystem(unittest.TestCase):
    """
    Board #2 (Perde) Testleri
    """

    def setUp(self):
        self.port = 5
        self.patcher = patch('serial.Serial')
        self.MockSerial = self.patcher.start()
        self.mock_conn = self.MockSerial.return_value
        self.mock_conn.is_open = True
        self.curtain = CurtainControlSystemConnection(self.port)
        print("\n" + "-" * 60)

    def tearDown(self):
        self.patcher.stop()

    def test_set_curtain_status_protocol(self):
        """Perde Açıklık Ayarı Testi"""
        print(f"[TEST SENARYOSU] Perde Açıklık Ayarı (Set)")

        test_val = 55.5
        print(f"   -> Girdi: %{test_val}")

        self.curtain.open()
        self.curtain.setCurtainStatus(test_val)

        print(f"   -> Beklenen Protokol: Ondalık=0x85, Tam=0xF7")

        expected_calls = [
            call(bytes([0x85])),
            call(bytes([0xF7]))
        ]
        self.mock_conn.write.assert_has_calls(expected_calls)
        print("   -> SONUÇ: BAŞARILI [✓]")

    def test_update_data_parsing(self):
        """Sensör Verisi Ayrıştırma Testi"""
        print(f"[TEST SENARYOSU] Perde/Sensör Verisi Okuma ve Birleştirme")
        print("   -> Simülasyon: PIC'ten parça parça byte'lar geliyor...")

        self.curtain.open()

        # Simüle edilen veriler
        # Curtain: 10.0, Temp: 24.5, Press: 13.2, Light: 50.5
        self.mock_conn.read.side_effect = [
            b'\x0A', b'\x00',  # 10.0
            b'\x18', b'\x05',  # 24.5
            b'\x0D', b'\x02',  # 13.2
            b'\x32', b'\x05'  # 50.5
        ]

        self.curtain.update()

        # Ekrana okunan değerleri bas
        print(f"   -> Okunan Perde: %{self.curtain.curtainStatus} (Beklenen: 10.0)")
        print(f"   -> Okunan Sıcaklık: {self.curtain.getOutdoorTemp()} C (Beklenen: 24.5)")
        print(f"   -> Okunan Basınç: {self.curtain.getOutdoorPress()} hPa (Beklenen: 13.2)")
        print(f"   -> Okunan Işık: {self.curtain.getLightIntensity()} Lux (Beklenen: 50.5)")

        self.assertEqual(self.curtain.curtainStatus, 10.0)
        self.assertEqual(self.curtain.getOutdoorTemp(), 24.5)
        self.assertEqual(self.curtain.getOutdoorPress(), 13.2)
        self.assertEqual(self.curtain.getLightIntensity(), 50.5)

        print("   -> SONUÇ: BAŞARILI [✓]")

    def test_update_routine_commands(self):
        """Perde Komut Testi"""
        print(f"[TEST SENARYOSU] Perde İstek Komutları (Request)")
        self.curtain.open()
        self.mock_conn.read.return_value = b'\x00'
        self.curtain.update()

        print("   -> Kontrol: Tüm sensörler için (Int+Frac) istekleri yollandı mı?")
        expected_requests = [
            # 1. Perde Durumu İsteği (Tam Sayı + Ondalık)
            call(const.CMD_GET_CURTAIN_INT),
            call(const.CMD_GET_CURTAIN_FRAC),

            # 2. Dış Sıcaklık İsteği
            call(const.CMD_GET_OUT_TEMP_INT),
            call(const.CMD_GET_OUT_TEMP_FRAC),

            # 3. Hava Basıncı İsteği
            call(const.CMD_GET_OUT_PRESS_INT),
            call(const.CMD_GET_OUT_PRESS_FRAC),

            # 4. Işık Şiddeti İsteği
            call(const.CMD_GET_LIGHT_INT),
            call(const.CMD_GET_LIGHT_FRAC)
        ]

        self.mock_conn.write.assert_has_calls(expected_requests, any_order=False)
        print("   -> SONUÇ: BAŞARILI [✓]")


if __name__ == '__main__':
    unittest.main()