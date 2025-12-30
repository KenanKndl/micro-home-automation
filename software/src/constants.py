# ==============================================================================
# PROJE: NEXUS CONTROL HUB - PROTOKOL SABİTLERİ
# YAZAR: Kenan Kandilli - 152120211045
# TARİH: 2025
# AÇIKLAMA: Firmware (PIC) tarafındaki logic ile birebir eşleşen komut
#           adreslerini, bit maskelerini ve protokol sabitlerini içerir.
# ==============================================================================

"""
Protokol sabitlerini içerir.
Bu değerler Firmware (PIC) tarafındaki logic ile birebir eşleşmelidir.
"""

# --- BOARD #1 (KLİMA) KOMUTLARI ---
CMD_AC_GET_DESIRED_TEMP_FRAC = 0b00000001
CMD_AC_GET_DESIRED_TEMP_INT = 0b00000010
CMD_AC_GET_AMBIENT_TEMP_INT = 0b00000100
CMD_AC_GET_AMBIENT_TEMP_FRAC = 0b00000011
CMD_AC_GET_FAN_SPEED = 0b00000101

# --- BOARD #2 (PERDE) KOMUTLARI ---
CMD_CUR_GET_DESIRED_FRAC = 0b00000001
CMD_CUR_GET_DESIRED_INT = 0b00000010
CMD_CUR_GET_OUTDOOR_TEMP_FRAC = 0b00000011
CMD_CUR_GET_OUTDOOR_TEMP_INT = 0b00000100
CMD_CUR_GET_PRESSURE_FRAC = 0b00000101
CMD_CUR_GET_PRESSURE_INT = 0b00000110
CMD_CUR_GET_LIGHT_FRAC = 0b00000111
CMD_CUR_GET_LIGHT_INT = 0b00001000

# --- GENEL MASKELEME ---
MASK_SET_FRAC_HEADER = 0b10000000
MASK_SET_INT_HEADER = 0b11000000
MASK_DATA_6BIT = 0x3F