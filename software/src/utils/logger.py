# ==============================================================================
# PROJE: NEXUS CONTROL HUB - LOGLAMA ALTYAPISI
# YAZAR: Kenan Kandilli - 152120211045
# TARİH: 2025
# AÇIKLAMA: Sistem olaylarını kaydeden, hata takibi yapan ve dosya/konsol
#           çıktılarını yöneten özelleştirilmiş loglama modülüdür.
# ==============================================================================

import logging
from logging.handlers import RotatingFileHandler
import os
import sys

# Logların kaydedileceği klasör
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


def get_logger(name="HomeAutomation"):
    """
    Rotating File Handler kullanan yapılandırılmış logger.
    """
    logger = logging.getLogger(name)

    # Eğer logger daha önce yapılandırıldıysa tekrar ekleme yapma
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Format Belirleme (Zaman | Seviye | Dosya:Satır | Mesaj)
    log_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Dosyaya Yazma (Rotating File Handler)
    # 5 MB'a ulaşınca dosyayı yedekle (app.log.1), en fazla 3 yedek tut.
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "system.log"),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Konsola Yazma
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)  # Konsolda sadece INFO ve üstünü göster

    # Handler'ları ekle
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger