# ==============================================================================
# PROJE: NEXUS CONTROL HUB - OTOMASYON API KATMANI (BACKEND)
# YAZAR: Kenan Kandilli - 152120211045
# TARİH: 2025
# AÇIKLAMA: PC ile PIC16F877A mikrodenetleyicileri arasındaki UART haberleşmesini,
#           veri paketleme protokollerini ve cihaz nesnelerini yöneten modüldür.
# ==============================================================================

"""
Home Automation API Module
--------------------------
Bu modül, PC ile PIC16F877A mikrodenetleyicileri arasındaki UART haberleşmesini
ve veri paketleme protokollerini yönetir.

Proje: Introduction to Microcomputers Term Project

@author: Kenan Kandilli
@date: 2025-11-16
@version: 1.3 (Constants ve Config ayrımı eklendi)
"""

import serial
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import constants as const
import config as cfg

logger = logging.getLogger(__name__)

class HomeAutomationSystemConnection(ABC):
    """
    Ev otomasyon sistemi bağlantıları için soyut temel sınıf (Abstract Base Class).
    Tüm UART iletişim mantığını kapsüller.
    """

    def __init__(self, com_port: int, baud_rate: int = cfg.DEFAULT_BAUDRATE):
        """
        Bağlantı nesnesini başlatır.

        :param com_port: Bağlanılacak COM port numarası (örn: 3).
        :param baud_rate: İletişim hızı (varsayılan: 9600 - config.py'den gelir).
        """
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.serial_conn: Optional[serial.Serial] = None
        self.port_name = f"COM{self.com_port}"

    def open(self) -> bool:
        """
        UART bağlantısını başlatır.

        :return: Bağlantı başarılıysa True, aksi halde False.
        """
        if self.serial_conn and self.serial_conn.is_open:
            logger.warning(f"{self.port_name} zaten açık.")
            return True

        try:
            self.serial_conn = serial.Serial(
                port=self.port_name,
                baudrate=self.baud_rate,
                timeout=cfg.TIMEOUT_READ,
                write_timeout=cfg.TIMEOUT_WRITE
            )
            logger.info(f"Bağlantı Kuruldu: {self.port_name} @ {self.baud_rate}")
            return True
        except serial.SerialException as e:
            logger.error(f"Bağlantı Hatası ({self.port_name}): {e}")
            return False

    def close(self) -> bool:
        """
        Aktif bağlantıyı güvenli bir şekilde kapatır.

        :return: Kapatma başarılıysa True.
        """
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info(f"Bağlantı Kapatıldı: {self.port_name}")
            return True
        return False

    @abstractmethod
    def update(self) -> None:
        """
        Cihazdan sensör ve durum verilerini okuyarak sınıf özelliklerini günceller.
        Alt sınıflar tarafından uygulanmalıdır.
        """
        pass

    def setComPort(self, port: int) -> None:
        """
        İletişim portunu günceller. Bağlantı kapalıyken yapılmalıdır.
        :param port: Yeni port numarası.
        """
        self.com_port = port
        self.port_name = f"COM{port}"

    def setBaudRate(self, rate: int) -> None:
        """
        İletişim hızını günceller.
        :param rate: Yeni baud rate değeri.
        """
        self.baud_rate = rate

    # --- PROTECTED HELPER METHODS ---

    def _send_byte(self, byte_val: int) -> None:
        """
        Seri port üzerinden tek bir byte gönderir.

        :param byte_val: Gönderilecek 0-255 arası tamsayı.
        """
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(bytes([byte_val]))
                # PIC işlem süresi için minimal bekleme
                time.sleep(0.05)
            except serial.SerialTimeoutException:
                logger.warning(f"Timeout: Veri yazılamadı -> {byte_val}")
            except Exception as e:
                logger.error(f"Yazma Hatası: {e}")

    def _read_byte(self) -> int:
        """
        Seri porttan tek bir byte okur.

        :return: Okunan byte değeri (int). Veri okunamazsa 0 döner.
        """
        if self.serial_conn and self.serial_conn.is_open:
            try:
                data = self.serial_conn.read(1)
                if data:
                    return int.from_bytes(data, byteorder='big')
            except serial.SerialException as e:
                logger.error(f"Okuma Hatası: {e}")
        return 0

    def _float_to_parts(self, value: float) -> Tuple[int, int]:
        """
        Float değeri protokol formatına uygun olarak Tam ve Ondalık kısımlara ayırır.

        Örnek: 25.6 -> (25, 6)

        :param value: İşlenecek ondalıklı sayı.
        :return: (tam_kısım, ondalık_kısım) tuple'ı.
        """
        int_part = int(value)
        # Ondalık kısmı al, 10 ile çarp ve yuvarla (Örn: 0.56 -> 5.6 -> 6)
        frac_part = int(round((value - int_part) * 10))

        # Yuvarlama taşması kontrolü (Örn: 25.95 -> 26.0)
        if frac_part == 10:
            int_part += 1
            frac_part = 0

        return int_part, frac_part


class AirConditionerSystemConnection(HomeAutomationSystemConnection):
    """
    Klima kontrol sistemi (Board #1) için API sınıfı.
    Sıcaklık ve fan hızı kontrolünü yönetir.
    """

    def __init__(self, com_port: int):
        super().__init__(com_port)
        self.desiredTemperature: float = 0.0
        self.ambientTemperature: float = 0.0
        self.fanSpeed: int = 0

    def update(self) -> None:
        """
        Rapor kapsamında tanımlanan okuma komutlarını sırayla gönderir
        ve gelen cevapları işler.
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            return

        try:
            # 1. Hedef Sıcaklık (Desired Temp)
            self._send_byte(const.CMD_AC_GET_DESIRED_TEMP_INT)
            d_int = self._read_byte()

            self._send_byte(const.CMD_AC_GET_DESIRED_TEMP_FRAC)
            d_frac = self._read_byte()

            self.desiredTemperature = d_int + (d_frac / 10.0)

            # 2. Ortam Sıcaklığı (Ambient Temp)
            self._send_byte(const.CMD_AC_GET_AMBIENT_TEMP_INT)
            a_int = self._read_byte()

            self._send_byte(const.CMD_AC_GET_AMBIENT_TEMP_FRAC)
            a_frac = self._read_byte()

            self.ambientTemperature = a_int + (a_frac / 10.0)

            # 3. Fan Hızı (Fan Speed)
            self._send_byte(const.CMD_AC_GET_FAN_SPEED)
            self.fanSpeed = self._read_byte()

        except Exception as e:
            logger.error(f"AC Update Hatası: {e}")

    def setDesiredTemp(self, temp: float) -> bool:
        """
        Yeni hedef sıcaklığı ayarlar ve cihaza gönderir.

        Protokol:
        - Kesirli Kısım Header: 10xxxxxx
        - Tam Kısım Header: 11xxxxxx

        :param temp: İstenen sıcaklık değeri (Float).
        :return: İşlem başarılıysa True.
        """
        int_part, frac_part = self._float_to_parts(temp)

        # 6-bit veri sınırı kontrolü (0-63)
        if int_part > 63:
            int_part = 63
            logger.warning("Sıcaklık değeri 63'e (max) çekildi.")

        if frac_part > 9: frac_part = 9

        # Bitwise Paketleme - Constant kullanımı düzeltildi
        cmd_frac = const.MASK_SET_FRAC_HEADER | (frac_part & const.MASK_DATA_6BIT)
        self._send_byte(cmd_frac)

        cmd_int = const.MASK_SET_INT_HEADER | (int_part & const.MASK_DATA_6BIT)
        self._send_byte(cmd_int)

        logger.info(f"SET TEMP -> {temp} (Int: {int_part}, Frac: {frac_part})")
        return True

    # --- GETTER METHODS (UML Requirement) ---
    def getAmbientTemp(self) -> float: return self.ambientTemperature
    def getFanSpeed(self) -> int: return self.fanSpeed
    def getDesiredTemp(self) -> float: return self.desiredTemperature


class CurtainControlSystemConnection(HomeAutomationSystemConnection):
    """
    Perde kontrol sistemi (Board #2) için API sınıfı.
    Perde pozisyonu, ışık, basınç ve dış sıcaklık verilerini yönetir.
    """

    def __init__(self, com_port: int):
        super().__init__(com_port)
        self.curtainStatus: float = 0.0
        self.outdoorTemperature: float = 0.0
        self.outdoorPressure: float = 0.0
        self.lightIntensity: float = 0.0

    def update(self) -> None:
        """
        Rapor kapsamında tanımlanan sensör verilerini günceller.
        ÖNEMLİ: Perde verisi 0-50 arası gelir, burada 2 ile çarpılıp %0-%100 yapılır.
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            return

        # PIC'in önceki işlemlerden kurtulması için minik bekleme
        time.sleep(0.02)

        # --- 1. Perde Durumu ---
        try:
            self._send_byte(const.CMD_CUR_GET_DESIRED_INT)
            c_int = self._read_byte()
            self._send_byte(const.CMD_CUR_GET_DESIRED_FRAC)
            c_frac = self._read_byte()
            raw_val = c_int + (c_frac / 10.0)
            self.curtainStatus = raw_val * 2.0

        except Exception:
            pass

            # --- 2. Dış Sıcaklık ---
        try:
            self._send_byte(const.CMD_CUR_GET_OUTDOOR_TEMP_INT)
            t_int = self._read_byte()
            self._send_byte(const.CMD_CUR_GET_OUTDOOR_TEMP_FRAC)
            t_frac = self._read_byte()
            self.outdoorTemperature = t_int + (t_frac / 10.0)
        except Exception:
            pass

        # --- 3. Basınç ---
        try:
            self._send_byte(const.CMD_CUR_GET_PRESSURE_INT)
            p_int = self._read_byte()
            self._send_byte(const.CMD_CUR_GET_PRESSURE_FRAC)
            p_frac = self._read_byte()
            self.outdoorPressure = p_int + (p_frac / 10.0)
        except Exception:
            pass

        # --- 4. Işık Şiddeti ---
        try:
            self._send_byte(const.CMD_CUR_GET_LIGHT_INT)
            l_int = self._read_byte()
            time.sleep(0.01)
            self._send_byte(const.CMD_CUR_GET_LIGHT_FRAC)
            l_frac = self._read_byte()

            self.lightIntensity = l_int + (l_frac / 10.0)
            print(f"DEBUG: Işık Okundu -> {self.lightIntensity}")

        except Exception as e:
            logger.error(f"Light Error: {e}")

    def setCurtainStatus(self, status: float) -> bool:
        """
        Perde açıklık oranını ayarlar.

        ÖNEMLİ: 6 bit sınırına (0-63) takılmamak için değeri 2'ye bölüp gönderiyoruz.
        Örnek: %100 -> 50 olarak gider. PIC bunu 20 ile çarpıp 1000 adıma çevirir.
        """
        # Gelen % değerini (örn: 100) yarıya indir (örn: 50)
        status_scaled = status / 2.0

        int_part, frac_part = self._float_to_parts(status_scaled)

        # Maksimum değer 50 olmalı (Orijinal 100'ün yarısı)
        # Çünkü protokolde 6 bit yer var (max 63). 100 gönderirsek taşar.
        if int_part > 50:
            int_part = 50
            logger.warning("Perde değeri ölçekli sınır (50) ile sınırlandırıldı.")

        # Protokol gereği paketleme
        cmd_frac = const.MASK_SET_FRAC_HEADER | (frac_part & const.MASK_DATA_6BIT)
        self._send_byte(cmd_frac)

        cmd_int = const.MASK_SET_INT_HEADER | (int_part & const.MASK_DATA_6BIT)
        self._send_byte(cmd_int)

        logger.info(f"SET CURTAIN -> %{status} (Giden Ham Veri: {int_part})")
        return True

    # --- GETTER METHODS (UML Requirement) ---
    def getOutdoorTemp(self) -> float: return self.outdoorTemperature
    def getOutdoorPress(self) -> float: return self.outdoorPressure
    def getLightIntensity(self) -> float: return self.lightIntensity