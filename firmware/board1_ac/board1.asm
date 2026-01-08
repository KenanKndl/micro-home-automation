;=============================================================================
; PROJECT: BOARD #1 - HOME AC SYSTEM - BANK FIXED & CUSTOM DISPLAY
; NOTES:
; - BANKSEL kullanilarak 302 hatalari giderildi.
; - WAIT_KEY_RELEASE eksigi giderildi.
; - Ekran dongusu: I (Initial) -> S (Speed) -> C (Current) -> d (Desired)
;=============================================================================

#include <p16f877a.inc>

    __CONFIG _FOSC_XT & _WDTE_OFF & _PWRTE_OFF & _BOREN_OFF & _LVP_OFF & _CP_OFF

;----------------------------- RAM MAP (CBLOCK) ------------------------------
    CBLOCK 0x20
        ; Display / keypad
        D1, D2, D3, D4
        T1, T2, T3, T4
        ENTRY_MODE
        KEY_VAL

        ; System
        ADC_L, ADC_H
        TEMP_VAL
        TARGET_TEMP
        RPM_VAL

        ; Conversions / display cache
        TEMP_100, TEMP_10, TEMP_1
        USER_D1, USER_D2, USER_D3, USER_D4
        DISP_ACTIVE

        ; Counters / timing
        LOOP_COUNT
        DELAY_VAR
        KEY_DELAY
        SAMPLE_TIME
        TEMP_CALC

        ; UART data registers
        DESIRED_TEMP_FRAC
        DESIRED_TEMP_INT
        AMBIENT_TEMP_FRAC
        AMBIENT_TEMP_INT
        FAN_SPEED
        UART_TEMP
    ENDC

    ORG 0x00
    GOTO START

    ORG 0x04
    RETFIE ; Interrupt kullanilmiyor ama vektor bos kalmasin

;-------------------------- 7-SEGMENT LOOKUP TABLE --------------------------
GET_SEG:
    ADDWF   PCL, F
    RETLW   B'00111111' ; 0
    RETLW   B'00000110' ; 1
    RETLW   B'01011011' ; 2
    RETLW   B'01001111' ; 3
    RETLW   B'01100110' ; 4
    RETLW   B'01101101' ; 5
    RETLW   B'01111101' ; 6
    RETLW   B'00000111' ; 7
    RETLW   B'01111111' ; 8
    RETLW   B'01101111' ; 9
    RETLW   B'01110111' ; A (10)
    RETLW   B'01111100' ; B (11)
    RETLW   B'00111001' ; C (12) - Current Temp icin
    RETLW   B'01011110' ; d (13) - Desired Temp icin
    RETLW   B'00001000' ; _ (14)
    RETLW   B'01110001' ; F (15)
    RETLW   B'00000110' ; I (16) - Initial/Ambient (1 gibi gorunur)
    RETLW   B'01101101' ; S (17) - Speed (5 gibi gorunur)

;=============================================================================
; INIT (BANKSEL KULLANILARAK DUZELTILDI)
;=============================================================================
START:
    ; --- Bank 1 Ayarlari ---
    BANKSEL TRISD
    CLRF    TRISD           ; D portu cikis (Segmentler)

    BANKSEL TRISA
    MOVLW   B'00010000'     ; RA4 Giris (Tach), Digerleri Cikis (Digit Secimi)
    MOVWF   TRISA

    BANKSEL TRISE
    BSF     TRISE, 0        ; RE0 Giris (Analog)

    BANKSEL TRISC
    BCF     TRISC, 0        ; Heater LED
    BCF     TRISC, 1        ; Cooler LED
    BCF     TRISC, 6        ; TX
    BSF     TRISC, 7        ; RX

    BANKSEL TRISB
    MOVLW   0xF0            ; Keypad: RB4-7 Giris, RB0-3 Cikis
    MOVWF   TRISB

    BANKSEL OPTION_REG
    MOVLW   B'00101000'     ; TMR0 Counter Mode (RA4 pininden sayar)
    MOVWF   OPTION_REG

    BANKSEL ADCON1
    MOVLW   B'10000000'     ; Sağa yasla, Analog girisler
    MOVWF   ADCON1

    ; UART Baud Rate
    BANKSEL SPBRG
    MOVLW   D'25'
    MOVWF   SPBRG
    BANKSEL TXSTA
    BCF     TXSTA, SYNC
    BSF     TXSTA, BRGH
    BSF     TXSTA, TXEN

    ; --- Bank 0 Ayarlari ---
    BANKSEL ADCON0
    MOVLW   B'10101001'     ; Fosc/32, CH5 (AN5), ADON=1
    MOVWF   ADCON0

    BANKSEL RCSTA
    BSF     RCSTA, SPEN
    BSF     RCSTA, CREN

    ; Degiskenleri Sifirla
    BANKSEL PORTC
    CLRF    PORTC
    CLRF    D1
    CLRF    D2
    CLRF    D3
    CLRF    D4
    CLRF    ENTRY_MODE
    CLRF    DISP_ACTIVE

    CLRF    DESIRED_TEMP_INT
    CLRF    DESIRED_TEMP_FRAC
    CLRF    AMBIENT_TEMP_INT
    CLRF    AMBIENT_TEMP_FRAC
    CLRF    FAN_SPEED

    ; Varsayilan Kullanici Hedefi (25.0)
    MOVLW   D'2'
    MOVWF   USER_D1
    MOVLW   D'5'
    MOVWF   USER_D2
    MOVLW   D'10' ; . (nokta) yerine A harfi veya bosluk
    MOVWF   USER_D3
    MOVLW   D'0'
    MOVWF   USER_D4

    CALL    WAIT_KEY_RELEASE

;=============================================================================
; MAIN LOOP
;=============================================================================
MAIN_LOOP:
    CALL    SHOW_DISPLAY
    CALL    UART_Check

    CALL    SCAN_KEYPAD
    MOVWF   KEY_VAL

    XORLW   0xFF
    BTFSC   STATUS, Z
    GOTO    MAIN_LOOP

    MOVLW   D'50'
    MOVWF   LOOP_COUNT
DEBOUNCE:
    CALL    SHOW_DISPLAY
    DECFSZ  LOOP_COUNT, F
    GOTO    DEBOUNCE

    ; 'A' Tusu -> Giris Modu
    MOVF    KEY_VAL, W
    XORLW   0x0A
    BTFSS   STATUS, Z
    GOTO    CHECK_HASH

    BSF     DISP_ACTIVE, 0
    MOVLW   1
    MOVWF   ENTRY_MODE
    CLRF    T1
    CLRF    T2
    CLRF    T3
    CLRF    T4
    CLRF    PORTC
    GOTO    RELEASE_WAIT

CHECK_HASH:
    ; '#' Tusu -> Kaydet
    MOVF    KEY_VAL, W
    XORLW   0x0F
    BTFSS   STATUS, Z
    GOTO    CHECK_NUM

    BTFSS   ENTRY_MODE, 0
    GOTO    RELEASE_WAIT

    ; Basit Kayit Mantigi
    MOVF    T1, W
    MOVWF   USER_D1
    MOVF    T2, W
    MOVWF   USER_D2
    MOVF    T3, W
    MOVWF   USER_D3
    MOVF    T4, W
    MOVWF   USER_D4

    ; Kontrol icin Integer kismi hesapla (Onlar * 10 + Birler)
    CLRF    DESIRED_TEMP_INT
    MOVF    T1, W
    MOVWF   LOOP_COUNT
    MOVF    LOOP_COUNT, F
    BTFSC   STATUS, Z
    GOTO    SKIP_TENS
CALC_TENS:
    MOVLW   D'10'
    ADDWF   DESIRED_TEMP_INT, F
    DECFSZ  LOOP_COUNT, F
    GOTO    CALC_TENS
SKIP_TENS:
    MOVF    T2, W
    ADDWF   DESIRED_TEMP_INT, F
    MOVF    T4, W
    MOVWF   DESIRED_TEMP_FRAC

    CLRF    ENTRY_MODE
    GOTO    ALTERNATE_LOOP

TURN_OFF_SCREEN:
    CLRF    DISP_ACTIVE
    CLRF    ENTRY_MODE
    CLRF    PORTD
    GOTO    MAIN_LOOP

CHECK_NUM:
    BTFSS   ENTRY_MODE, 0
    GOTO    RELEASE_WAIT

    ; '*' Tusu -> Kaydirma
    MOVF    KEY_VAL, W
    XORLW   0x0E
    BTFSC   STATUS, Z
    GOTO    DO_SHIFT

    ; Rakam Kontrol (0-9)
    MOVLW   0x0A
    SUBWF   KEY_VAL, W
    BTFSC   STATUS, C
    GOTO    RELEASE_WAIT

DO_SHIFT:
    MOVF    T2, W
    MOVWF   T1
    MOVF    T3, W
    MOVWF   T2
    MOVF    T4, W
    MOVWF   T3
    MOVF    KEY_VAL, W
    MOVWF   T4

    MOVF    T1, W
    MOVWF   D1
    MOVF    T2, W
    MOVWF   D2
    MOVF    T3, W
    MOVWF   D3
    MOVF    T4, W
    MOVWF   D4

RELEASE_WAIT:
    CALL    SHOW_DISPLAY
    CALL    UART_Check
    CALL    SCAN_KEYPAD
    XORLW   0xFF
    BTFSS   STATUS, Z
    GOTO    RELEASE_WAIT
    GOTO    MAIN_LOOP

;=============================================================================
; ALTERNATE DISPLAY LOOP (I -> S -> C -> d)
;=============================================================================
ALTERNATE_LOOP:
    ; ------------------------------------------
    ; 1. SHOW "I" (Initial/Ambient)
    ; ------------------------------------------
    CALL    READ_TEMP_SAFE  ; Ortam sicakligini oku
    
    MOVLW   D'16'           ; 'I' harfi (Tabloda 16. sira)
    MOVWF   D1
    MOVF    TEMP_10, W
    MOVWF   D2
    MOVF    TEMP_1, W
    MOVWF   D3
    MOVLW   D'0'            ; Ondalik 0 (Basitlik icin)
    MOVWF   D4
    
    CALL    DELAY_CHECK_A_2SEC

    ; ------------------------------------------
    ; 2. SHOW "S" (Fan Speed)
    ; ------------------------------------------
    CALL    READ_RPM_AND_CONVERT
    
    MOVLW   D'17'           ; 'S' harfi (Tabloda 17. sira)
    MOVWF   D1
    MOVLW   D'14'           ; '_' Bosluk
    MOVWF   D2
    MOVF    TEMP_100, W     ; Hizin yuzler/onlar basamagi
    MOVWF   D3
    MOVF    TEMP_10, W
    MOVWF   D4
    
    CALL    DELAY_CHECK_A_2SEC

    ; ------------------------------------------
    ; 3. SHOW "C" (Current Temp)
    ; ------------------------------------------
    CALL    READ_TEMP_SAFE
    
    MOVLW   D'12'           ; 'C' harfi
    MOVWF   D1
    MOVF    TEMP_10, W
    MOVWF   D2
    MOVF    TEMP_1, W
    MOVWF   D3
    MOVLW   D'0'
    MOVWF   D4
    
    CALL    DELAY_CHECK_A_2SEC

    ; ------------------------------------------
    ; 4. SHOW "d" (Desired Temp)
    ; ------------------------------------------
    MOVLW   D'13'           ; 'd' harfi
    MOVWF   D1
    MOVF    USER_D1, W
    MOVWF   D2
    MOVF    USER_D2, W
    MOVWF   D3
    MOVF    USER_D4, W      ; Girilen ondalik
    MOVWF   D4
    
    CALL    CONTROL_LEDS    ; Isitici/Fan kontrolu
    CALL    DELAY_CHECK_A_2SEC

    GOTO    ALTERNATE_LOOP

;=============================================================================
; SUBROUTINES
;=============================================================================

READ_RPM_AND_CONVERT:
    CLRF    TMR0
    MOVLW   D'2'
    MOVWF   ADC_H
RPM_L_OUT:
    MOVLW   D'200'
    MOVWF   SAMPLE_TIME
RPM_L_IN:
    CALL    SHOW_DISPLAY
    CALL    UART_Check
    DECFSZ  SAMPLE_TIME, F
    GOTO    RPM_L_IN
    DECFSZ  ADC_H, F
    GOTO    RPM_L_OUT

    MOVF    TMR0, W
    MOVWF   RPM_VAL
    MOVWF   FAN_SPEED

    CLRF    TEMP_100
    CLRF    TEMP_10
    CLRF    TEMP_1
    MOVF    RPM_VAL, W
    MOVWF   TEMP_VAL
    ; Donusum (Binary to Decimal)
    GOTO    CONVERT_DECIMAL

READ_TEMP_SAFE:
    BANKSEL ADCON1
    MOVLW   B'10000000'
    MOVWF   ADCON1
    BANKSEL ADCON0
    BSF     ADCON0, GO
W_ADC:
    BTFSC   ADCON0, GO
    GOTO    W_ADC
    
    BANKSEL ADRESL
    MOVF    ADRESL, W
    BANKSEL ADC_L
    MOVWF   ADC_L
    BANKSEL ADRESH
    MOVF    ADRESH, W
    BANKSEL ADC_H
    MOVWF   ADC_H
    
    ; Sicaklik hesaplama (Basitlestirilmis)
    BANKSEL ADCON1
    MOVLW   B'00000110'
    MOVWF   ADCON1
    BANKSEL STATUS
    BCF     STATUS, RP0
    
    BCF     STATUS, C
    RRF     ADC_H, F
    RRF     ADC_L, F
    MOVF    ADC_L, W
    MOVWF   TEMP_VAL
    MOVWF   AMBIENT_TEMP_INT
    CLRF    AMBIENT_TEMP_FRAC
    
    CLRF    TEMP_100
    CLRF    TEMP_10
    CLRF    TEMP_1
    
CONVERT_DECIMAL:
C100:
    MOVLW   D'100'
    SUBWF   TEMP_VAL, W
    BTFSS   STATUS, C
    GOTO    C10
    MOVWF   TEMP_VAL
    INCF    TEMP_100, F
    GOTO    C100
C10:
    MOVLW   D'10'
    SUBWF   TEMP_VAL, W
    BTFSS   STATUS, C
    GOTO    C1
    MOVWF   TEMP_VAL
    INCF    TEMP_10, F
    GOTO    C10
C1:
    MOVF    TEMP_VAL, W
    MOVWF   TEMP_1
    RETURN

CONTROL_LEDS:
    CLRF    TARGET_TEMP
    MOVF    USER_D1, W
    MOVWF   LOOP_COUNT
    MOVF    LOOP_COUNT, F
    BTFSC   STATUS, Z
    GOTO    ADD_ONES_LEDS
CALC_TENS_LEDS:
    MOVLW   D'10'
    ADDWF   TARGET_TEMP, F
    DECFSZ  LOOP_COUNT, F
    GOTO    CALC_TENS_LEDS
ADD_ONES_LEDS:
    MOVF    USER_D2, W
    ADDWF   TARGET_TEMP, F

    BCF     PORTC, 0
    BCF     PORTC, 1
    MOVF    AMBIENT_TEMP_INT, W
    SUBWF   TARGET_TEMP, W
    BTFSC   STATUS, Z
    RETURN
    BTFSC   STATUS, C
    GOTO    KEYPAD_BIGGER
    GOTO    KEYPAD_SMALLER
KEYPAD_BIGGER:
    BSF     PORTC, 0 ; Heater
    RETURN
KEYPAD_SMALLER:
    BSF     PORTC, 1 ; Cooler
    RETURN

SHOW_DISPLAY:
    BTFSS   DISP_ACTIVE, 0
    RETURN

    MOVF    D1, W
    CALL    GET_SEG
    MOVWF   PORTD
    BSF     PORTA, 0
    CALL    WAIT_1MS
    BCF     PORTA, 0
    CLRF    PORTD

    MOVF    D2, W
    CALL    GET_SEG
    MOVWF   PORTD
    BSF     PORTA, 1
    CALL    WAIT_1MS
    BCF     PORTA, 1
    CLRF    PORTD

    MOVF    D3, W
    CALL    GET_SEG
    MOVWF   PORTD
    BSF     PORTA, 2
    CALL    WAIT_1MS
    BCF     PORTA, 2
    CLRF    PORTD

    MOVF    D4, W
    CALL    GET_SEG
    MOVWF   PORTD
    BSF     PORTA, 3
    CALL    WAIT_1MS
    BCF     PORTA, 3
    CLRF    PORTD
    RETURN

WAIT_1MS:
    MOVLW   D'200'
    MOVWF   DELAY_VAR
DLY_L:
    DECFSZ  DELAY_VAR, F
    GOTO    DLY_L
    RETURN

; Eksik olan fonksiyon eklendi!
WAIT_KEY_RELEASE:
    CALL    SHOW_DISPLAY
    CALL    SCAN_KEYPAD
    XORLW   0xFF
    BTFSS   STATUS, Z
    GOTO    WAIT_KEY_RELEASE
    RETURN

DELAY_CHECK_A_2SEC:
    MOVLW   D'2'
    MOVWF   ADC_H
DL_OUT:
    MOVLW   D'200'
    MOVWF   LOOP_COUNT
DL_IN:
    CALL    SHOW_DISPLAY
    CALL    UART_Check
    CALL    SCAN_KEYPAD
    XORLW   0x0A
    BTFSC   STATUS, Z
    GOTO    RESET_SYSTEM
    DECFSZ  LOOP_COUNT, F
    GOTO    DL_IN
    DECFSZ  ADC_H, F
    GOTO    DL_OUT
    RETURN

RESET_SYSTEM:
    CLRF    PORTC
    GOTO    START

; Keypad & UART functions
SCAN_KEYPAD:
    BANKSEL TRISB
    MOVLW   0xF0
    MOVWF   TRISB
    BANKSEL PORTB
    MOVLW   B'11111110'
    MOVWF   PORTB
    CALL    KEY_WAIT
    BTFSS   PORTB, 4
    RETLW   0x01
    BTFSS   PORTB, 5
    RETLW   0x02
    BTFSS   PORTB, 6
    RETLW   0x03
    BTFSS   PORTB, 7
    RETLW   0x0A
    MOVLW   B'11111101'
    MOVWF   PORTB
    CALL    KEY_WAIT
    BTFSS   PORTB, 4
    RETLW   0x04
    BTFSS   PORTB, 5
    RETLW   0x05
    BTFSS   PORTB, 6
    RETLW   0x06
    BTFSS   PORTB, 7
    RETLW   0x0B
    MOVLW   B'11111011'
    MOVWF   PORTB
    CALL    KEY_WAIT
    BTFSS   PORTB, 4
    RETLW   0x07
    BTFSS   PORTB, 5
    RETLW   0x08
    BTFSS   PORTB, 6
    RETLW   0x09
    BTFSS   PORTB, 7
    RETLW   0x0C
    MOVLW   B'11110111'
    MOVWF   PORTB
    CALL    KEY_WAIT
    BTFSS   PORTB, 4
    RETLW   0x0E
    BTFSS   PORTB, 5
    RETLW   0x00
    BTFSS   PORTB, 6
    RETLW   0x0F
    BTFSS   PORTB, 7
    RETLW   0x0D
    RETLW   0xFF

KEY_WAIT:
    MOVLW   D'50'
    MOVWF   KEY_DELAY
K_LOOP:
    DECFSZ  KEY_DELAY, F
    GOTO    K_LOOP
    RETURN

; ---------------------------------------------------------------------------
; UART_SendByte
;   W register'daki byte'i UART'tan gönderir (TXREG'e yazar).
;   TXIF=1 olana kadar bekler.
; ---------------------------------------------------------------------------
UART_SendByte:
    BANKSEL PIR1
WAIT_TX:
    BTFSS   PIR1, TXIF      ; TXREG boş mu?
    GOTO    WAIT_TX
    BANKSEL TXREG
    MOVWF   TXREG
    RETURN


; ---------------------------------------------------------------------------
; UART_Check
;   UART'tan byte geldiyse okur, komutu çözer.
;
;   PC -> PIC Komutları (constants.py ile aynı) :contentReference[oaicite:2]{index=2}
;     0x01: GET desired frac
;     0x02: GET desired int
;     0x03: GET ambient frac
;     0x04: GET ambient int
;     0x05: GET fan speed
;
;   SET Protokolü (automation_api.py ile aynı) :contentReference[oaicite:3]{index=3}
;     10xxxxxx (0x80|data): set desired frac (0-63)
;     11xxxxxx (0xC0|data): set desired int  (0-63)
; ---------------------------------------------------------------------------
UART_Check:
    BANKSEL PIR1
    BTFSS   PIR1, RCIF
    RETURN

    ; Byte oku
    BANKSEL RCREG
    MOVF    RCREG, W
    BANKSEL UART_TEMP
    MOVWF   UART_TEMP

    ; --- 1) SET komutlarını ayıkla: üst 2 bit'e bak ---
    ; INT header mı? (0xC0..0xFF)
    MOVF    UART_TEMP, W
    ANDLW   0xC0
    XORLW   0xC0
    BTFSC   STATUS, Z
    GOTO    UART_SET_INT

    ; FRAC header mı? (0x80..0xBF)
    MOVF    UART_TEMP, W
    ANDLW   0xC0
    XORLW   0x80
    BTFSC   STATUS, Z
    GOTO    UART_SET_FRAC

    ; --- 2) GET komutlarını işle (0x01..0x05) ---
    MOVF    UART_TEMP, W
    XORLW   0x01
    BTFSC   STATUS, Z
    GOTO    UART_GET_DES_FRAC

    MOVF    UART_TEMP, W
    XORLW   0x02
    BTFSC   STATUS, Z
    GOTO    UART_GET_DES_INT

    MOVF    UART_TEMP, W
    XORLW   0x03
    BTFSC   STATUS, Z
    GOTO    UART_GET_AMB_FRAC

    MOVF    UART_TEMP, W
    XORLW   0x04
    BTFSC   STATUS, Z
    GOTO    UART_GET_AMB_INT

    MOVF    UART_TEMP, W
    XORLW   0x05
    BTFSC   STATUS, Z
    GOTO    UART_GET_FAN

    RETURN

; ---------------- SET handlers ----------------
UART_SET_INT:
    ; desired int = UART_TEMP & 0x3F
    MOVF    UART_TEMP, W
    ANDLW   0x3F
    MOVWF   DESIRED_TEMP_INT

    ; İstersen ekranda da güncelle (opsiyonel):
    ; DESIRED_TEMP_INT -> USER_D1 USER_D2
    ; (aşağıda opsiyonel bölüm verdim)
    CALL    UART_UpdateUserDigitsFromDesired
    RETURN

UART_SET_FRAC:
    ; desired frac = UART_TEMP & 0x3F
    MOVF    UART_TEMP, W
    ANDLW   0x3F
    MOVWF   DESIRED_TEMP_FRAC

    ; İstersen ekranda da güncelle (opsiyonel):
    CALL    UART_UpdateUserDigitsFromDesired
    RETURN

; ---------------- GET handlers ----------------
UART_GET_DES_FRAC:
    MOVF    DESIRED_TEMP_FRAC, W
    CALL    UART_SendByte
    RETURN

UART_GET_DES_INT:
    MOVF    DESIRED_TEMP_INT, W
    CALL    UART_SendByte
    RETURN

UART_GET_AMB_FRAC:
    MOVF    AMBIENT_TEMP_FRAC, W
    CALL    UART_SendByte
    RETURN

UART_GET_AMB_INT:
    MOVF    AMBIENT_TEMP_INT, W
    CALL    UART_SendByte
    RETURN

UART_GET_FAN:
    MOVF    FAN_SPEED, W
    CALL    UART_SendByte
    RETURN

UART_GET_FAN_SPEED:
    BANKSEL FAN_SPEED
    MOVF    FAN_SPEED, W
    BTFSS   STATUS, Z
    GOTO    SEND_FAN

    ; FAN_SPEED=0 ise test için sabit bir değer yolla (örn 25)
    MOVLW   D'25'

SEND_FAN:
    CALL    UART_SendByte
    RETURN

; ---------------------------------------------------------------------------
; UART_UpdateUserDigitsFromDesired
;   DESIRED_TEMP_INT / DESIRED_TEMP_FRAC -> USER_D1 USER_D2 USER_D3 USER_D4
;   (0..63 varsayımı; USER_D3 sabit 10)
; ---------------------------------------------------------------------------
UART_UpdateUserDigitsFromDesired:
    BANKSEL USER_D3
    MOVLW   D'10'
    MOVWF   USER_D3

    ; int -> tens/ones
    BANKSEL DESIRED_TEMP_INT
    MOVF    DESIRED_TEMP_INT, W
    BANKSEL TEMP_VAL
    MOVWF   TEMP_VAL

    BANKSEL USER_D1
    CLRF    USER_D1

UART_TENS_LOOP:
    BANKSEL TEMP_VAL
    MOVLW   D'10'
    SUBWF   TEMP_VAL, W
    BTFSS   STATUS, C
    GOTO    UART_TENS_DONE
    MOVWF   TEMP_VAL
    BANKSEL USER_D1
    INCF    USER_D1, F
    GOTO    UART_TENS_LOOP

UART_TENS_DONE:
    BANKSEL TEMP_VAL
    MOVF    TEMP_VAL, W
    BANKSEL USER_D2
    MOVWF   USER_D2

    ; frac -> USER_D4
    BANKSEL DESIRED_TEMP_FRAC
    MOVF    DESIRED_TEMP_FRAC, W
    BANKSEL USER_D4
    MOVWF   USER_D4
    RETURN


    END