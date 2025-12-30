# ==============================================================================
# PROJE: NEXUS CONTROL HUB - PORT BAĞLANTI TESTLERİ (INTEGRATION)
# YAZAR: Kenan Kandilli - 152120211045
# TARİH: 2025
# AÇIKLAMA: Mock kullanmadan gerçek COM port erişimini (com0com veya donanım)
#           test eden entegrasyon test modülüdür.
# ==============================================================================

import unittest
import serial
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))  # .../software/tests
software_dir = os.path.dirname(current_dir)  # .../software
src_dir = os.path.join(software_dir, 'src')  # .../software/src
sys.path.insert(0, src_dir)

import config as cfg

class TestRealPortConnections(unittest.TestCase):
    """
    Gerçek Port Bağlantı Testleri (Integration Tests).
    Bu testler 'Mock' KULLANMAZ. Gerçekten portları açmaya çalışır.

    ÖN KOŞUL:
    1. com0com veya gerçek donanım takılı olmalıdır.
    2. Portlar başka bir program (örn: PICSimLab) tarafından meşgul edilmemelidir.
    """

    def test_01_ac_port_connection(self):
        """
        [Board #1] Klima Portu (COM3) Erişim Testi
        """
        port_name = f"COM{cfg.AC_BOARD_PORT}"
        print(f"\n[TEST] {port_name} (Klima) bağlantısı deneniyor...", end=" ")

        try:
            # Gerçek bağlantı denemesi
            ser = serial.Serial(port_name, baudrate=9600, timeout=1)

            # Eğer buraya geldiyse port başarılı açılmıştır
            self.assertTrue(ser.is_open, "Port nesnesi açık görünmüyor.")

            # İşimiz bitince hemen kapatalım ki diğer testler kullanabilsin
            ser.close()
            print("BAŞARILI ✓")

        except serial.SerialException as e:
            print("BAŞARISIZ ✗")
            self.fail(f"\nKRİTİK HATA: {port_name} açılamadı!\n"
                      f"Olası Sebepler:\n"
                      f"1. com0com yüklü değil veya port çifti (3<->4) oluşturulmadı.\n"
                      f"2. Port şu an başka bir program tarafından kullanılıyor.\n"
                      f"3. config.py dosyasındaki port numarası yanlış.\n"
                      f"Sistem Hatası: {e}")

    def test_02_curtain_port_connection(self):
        """
        [Board #2] Perde Portu (COM5) Erişim Testi
        """
        port_name = f"COM{cfg.CURTAIN_BOARD_PORT}"
        print(f"\n[TEST] {port_name} (Perde) bağlantısı deneniyor...", end=" ")

        try:
            ser = serial.Serial(port_name, baudrate=9600, timeout=1)
            self.assertTrue(ser.is_open, "Port nesnesi açık görünmüyor.")
            ser.close()
            print("BAŞARILI ✓")

        except serial.SerialException as e:
            print("BAŞARISIZ ✗")
            self.fail(f"\nKRİTİK HATA: {port_name} açılamadı!\n"
                      f"Olası Sebepler:\n"
                      f"1. com0com yüklü değil veya port çifti (5<->6) oluşturulmadı.\n"
                      f"2. Port şu an başka bir program tarafından kullanılıyor.\n"
                      f"Sistem Hatası: {e}")


if __name__ == '__main__':
    unittest.main()