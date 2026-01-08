# ==============================================================================
# PROJE: NEXUS CONTROL HUB - SİSTEM KONFİGÜRASYONU
# YAZAR: Kenan Kandilli - 152120211045
# TARİH: 2025
# AÇIKLAMA: COM port numaraları, baud rate hızları, zaman aşımı süreleri ve
#           dosya yolları gibi global ayarları barındırır.
# ==============================================================================

"""
Uygulama Konfigürasyonu.
Port ayarları ve zaman aşımları buradan yönetilir.
"""

# Seri Port Ayarları
DEFAULT_BAUDRATE = 9600
AC_BOARD_PORT = 10 # Varsayılan Board 1 Portu
CURTAIN_BOARD_PORT = 12 # Varsayılan Board 2 Portu

# Bağlantı Ayarları
TIMEOUT_READ = 1.0 # Saniye
TIMEOUT_WRITE = 1.0 # Saniye

# Log Ayarları
LOG_FILE_NAME = "system.log"
LOG_DIR = "logs"