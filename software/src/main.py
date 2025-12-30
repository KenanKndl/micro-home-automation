# ==============================================================================
# PROJE: NEXUS CONTROL HUB - ANA GİRİŞ NOKTASI (MAIN)
# YAZAR: Kenan Kandilli - 152120211045
# TARİH: 2025
# AÇIKLAMA: Uygulamanın tek giriş noktasıdır. Gerekli kütüphaneleri yükler,
#           loglama altyapısını kurar ve Grafik Arayüzü (GUI) başlatır.
# ==============================================================================

"""
Home Automation System - Main Entry Point
-----------------------------------------
Bu dosya projenin TEK giriş noktasıdır.
Gerekli kütüphaneleri yükler ve GUI uygulamasını başlatır.
"""

import customtkinter as ctk
import logging
import sys
import os

# --- PATH AYARLARI ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from gui_app import ModernHomeAutomationGUI
    import config as cfg
except ImportError as e:
    print(f"KRİTİK HATA: Modüller yüklenemedi! {e}")
    sys.exit(1)

# --- LOGGING KURULUMU ---
if not os.path.exists(cfg.LOG_DIR):
    os.makedirs(cfg.LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(cfg.LOG_DIR, cfg.LOG_FILE_NAME), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MainStarter")

def main():
    logger.info("==========================================")
    logger.info("   EV OTOMASYON SİSTEMİ BAŞLATILIYOR...   ")
    logger.info("==========================================")

    try:
        # 1. Ana Pencereyi (Root) Oluştur
        app_root = ctk.CTk()

        # 2. GUI Sınıfını Başlat (gui_app.py içindeki sınıf)
        # Root penceresini parametre olarak gönder
        gui = ModernHomeAutomationGUI(app_root)

        logger.info("Arayüz başarıyla yüklendi.")
        logger.info(f"Ayarlı Portlar -> Klima: COM{cfg.AC_BOARD_PORT}, Perde: COM{cfg.CURTAIN_BOARD_PORT}")

        # 3. Ana Döngüyü (Main Loop) Başlat
        app_root.mainloop()

    except Exception as e:
        logger.critical(f"Beklenmeyen bir hata oluştu: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Program sonlandırıldı.")

if __name__ == "__main__":
    main()