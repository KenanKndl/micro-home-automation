; =============================================================================
; BOARD #2 - Curtain & Sensors (PIC16F877A)
; DÜZELTME: Gece/Gündüz algılama mantığı tersine çevrildi (BTFSS -> BTFSC).
;           Artık aydınlıkta Gündüz Modu (Kilit Açık) düzgün çalışacak.
; =============================================================================

        LIST    P=16F877A
        #include <p16f877a.inc>

        __CONFIG _CP_OFF & _WDT_OFF & _PWRTE_ON & _XT_OSC & _LVP_OFF & _BODEN_ON

; ---------------------------
; PROTOCOL COMMANDS
; ---------------------------
CMD_CUR_GET_DESIRED_FRAC      EQU b'00000001'
CMD_CUR_GET_DESIRED_INT       EQU b'00000010'
CMD_CUR_GET_OUTDOOR_TEMP_FRAC EQU b'00000011'
CMD_CUR_GET_OUTDOOR_TEMP_INT  EQU b'00000100'
CMD_CUR_GET_PRESSURE_FRAC     EQU b'00000101'
CMD_CUR_GET_PRESSURE_INT      EQU b'00000110'
CMD_CUR_GET_LIGHT_FRAC        EQU b'00000111'
CMD_CUR_GET_LIGHT_INT         EQU b'00001000'

MASK_SET_FRAC_HEADER          EQU b'10000000'
MASK_SET_INT_HEADER           EQU b'11000000'
MASK_DATA_6BIT                EQU 0x3F

SPBRG_VAL EQU .25

; ---------------------------
; RAM VARIABLES
; ---------------------------
        CBLOCK  0x20
    cmd_byte
    rx_tmp
    set_int_6
    
    ; Sensor & Status Values
    cur_percentage ; Mevcut Hedef Yüzde (0-50 Skalası)
    adc_val        ; ADC Okuma Degeri
    
    ; --- OTOMASYON DEĞİŞKENLERİ ---
    is_night_mode  ; 1=Gece (Kilitli), 0=Gunduz (Acik)
    saved_usr_pos  ; Gece olmadan onceki son kullanici konumu
    
    ; --- 16-BIT MOTOR VARIABLES ---
    pos_L       ; Mevcut Konum (Low Byte)
    pos_H       ; Mevcut Konum (High Byte)
    tgt_L       ; Hedef Konum (Low Byte)
    tgt_H       ; Hedef Konum (High Byte)
    
    ; Matematik Gecici
    math_tmp_L
    math_tmp_H
    
    mot_phase     
    d1, d2        
    lux_int       ; LDR hesaplama icin
        ENDC

; =============================================================================
        ORG 0x0000
        GOTO INIT

; =============================================================================
; INIT
; =============================================================================
INIT:
        ; PORTB (Motor Output)
        BANKSEL TRISB
        CLRF    TRISB
        BANKSEL PORTB
        CLRF    PORTB
        
        ; PORTA (ADC Input)
        BANKSEL TRISA
        BSF     TRISA, 0        ; RA0 (LDR)
        BSF     TRISA, 1        ; RA1
        BSF     TRISA, 2        ; RA2
        
        BANKSEL ADCON1
        MOVLW   b'00000000'     ; Left Justified
        MOVWF   ADCON1

        BANKSEL ADCON0
        MOVLW   b'01000001'     ; ADC On
        MOVWF   ADCON0

        ; Reset Variables
        BANKSEL pos_L
        CLRF    pos_L
        CLRF    pos_H
        CLRF    tgt_L
        CLRF    tgt_H
        CLRF    cur_percentage
        CLRF    mot_phase
        
        ; Otomasyonu Sifirla
        CLRF    is_night_mode
        CLRF    saved_usr_pos

        CALL    UART_Init

; =============================================================================
; MAIN LOOP
; =============================================================================
MAIN_LOOP:
        ; 1. OTOMATİK GECE/GÜNDÜZ KONTROLÜ
        CALL CHECK_LDR_AUTOMATION

        ; 2. MOTOR GÖREVİ
        CALL MOTOR_TASK

        ; 3. UART KONTROLÜ
        BANKSEL PIR1
        BTFSS   PIR1, RCIF
        GOTO    MAIN_LOOP

        CALL    UART_Read_Byte_Safe
        MOVWF   cmd_byte

        ; --- HEADER KONTROLÜ ---
        MOVF    cmd_byte, W
        ANDLW   b'11000000'
        XORLW   b'10000000'
        BTFSC   STATUS, Z
        GOTO    HANDLE_SET_FRAC

        MOVF    cmd_byte, W
        ANDLW   b'11000000'
        XORLW   b'11000000'
        BTFSC   STATUS, Z
        GOTO    HANDLE_SET_INT

        GOTO    HANDLE_GET

; =============================================================================
; OTOMASYON MANTIĞI (DÜZELTİLDİ)
; =============================================================================
CHECK_LDR_AUTOMATION:
        ; LDR Değerini Oku (AN0)
        CALL    ReadADC_AN0
        
        ; ADC Değeri (adc_val) elimizde.
        ; GECE EŞİĞİ: 30
        ; GÜNDÜZ EŞİĞİ: 60

        ; --- GECE KONTROLÜ ---
        MOVLW   .30
        SUBWF   adc_val, W      ; W = adc_val - 30
        
        ; DÜZELTME BURADA: BTFSC (Skip if Clear) kullanıldı.
        ; Eğer adc < 30 ise (Sonuç Negatif) -> Borrow oluşur -> C=0 (Clear).
        ; C=0 ise SKIP JUMP -> Gece Koduna Gir.
        ; C=1 ise (adc >= 30) -> JUMP -> Gündüz Kontrolüne Git.
        BTFSC   STATUS, C       
        GOTO    TRY_DAY_MODE
        
        ; BURASI GECE BÖLGESİ (< 30)
        ; Zaten gece modunda mıyız?
        BTFSC   is_night_mode, 0
        RETURN  ; Evet, zaten gece.

        ; HAYIR, Gecenin ilk anı!
        ; 1. Modu Gece yap
        BSF     is_night_mode, 0
        
        ; 2. Mevcut kullanıcı ayarını sakla
        MOVF    cur_percentage, W
        MOVWF   saved_usr_pos
        
        ; 3. Perdeyi TAM KAPAT (%100 -> Kodda 50)
        MOVLW   .50
        CALL    FORCE_MOVE_TO_W
        RETURN

TRY_DAY_MODE:
        ; --- GÜNDÜZ KONTROLÜ ---
        MOVLW   .60
        SUBWF   adc_val, W      ; W = adc_val - 60
        BTFSC   STATUS, C       ; Eğer adc_val >= 60 ise (Carry=1) -> GÜNDÜZ
        GOTO    ACTIVATE_DAY
        RETURN  ; 30-60 arası, işlem yapma.

ACTIVATE_DAY:
        ; Zaten gündüz modunda mıyız?
        BTFSS   is_night_mode, 0
        RETURN  ; Evet, zaten gündüz.
        
        ; HAYIR, Gün doğumu!
        ; 1. Modu Gündüz yap (KİLİDİ AÇ)
        BCF     is_night_mode, 0
        
        ; 2. Saklanan konumu geri yükle
        MOVF    saved_usr_pos, W
        CALL    FORCE_MOVE_TO_W
        RETURN

; Yardımcı Fonksiyon: W'deki yüzdeye git
FORCE_MOVE_TO_W:
        MOVWF   cur_percentage      
        MOVWF   set_int_6           
        GOTO    CALCULATE_STEPS     

; =============================================================================
; MOTOR TASK
; =============================================================================
MOTOR_TASK:
        ; Hedefe ulaşıldı mı?
        MOVF    pos_H, W
        SUBWF   tgt_H, W
        BTFSS   STATUS, Z
        GOTO    CHECK_DIRECTION
        MOVF    pos_L, W
        SUBWF   tgt_L, W
        BTFSC   STATUS, Z
        RETURN

CHECK_DIRECTION:
        ; Yön Belirleme
        MOVF    pos_H, W
        SUBWF   tgt_H, W
        BTFSS   STATUS, Z
        GOTO    CHECK_CARRY_H
        MOVF    pos_L, W
        SUBWF   tgt_L, W
        BTFSS   STATUS, C
        GOTO    MOVE_BACKWARD
        GOTO    MOVE_FORWARD

CHECK_CARRY_H:
        BTFSS   STATUS, C
        GOTO    MOVE_BACKWARD
        GOTO    MOVE_FORWARD

MOVE_FORWARD:
        INCF    pos_L, F
        BTFSC   STATUS, Z
        INCF    pos_H, F
        INCF    mot_phase, F
        GOTO    APPLY_STEP

MOVE_BACKWARD:
        MOVF    pos_L, W
        BTFSC   STATUS, Z
        DECF    pos_H, F
        DECF    pos_L, F
        DECF    mot_phase, F
        GOTO    APPLY_STEP

APPLY_STEP:
        MOVF    mot_phase, W
        ANDLW   b'00000011'
        MOVWF   mot_phase
        CALL    GET_STEP_PATTERN
        BANKSEL PORTB
        MOVWF   PORTB
        CALL    DELAY_MOTOR
        RETURN

GET_STEP_PATTERN:
        ADDWF   PCL, F
        RETLW   b'00000001'
        RETLW   b'00000010'
        RETLW   b'00000100'
        RETLW   b'00001000'

DELAY_MOTOR:
        MOVLW   .10
        MOVWF   d1
DL1:    MOVLW   .50
        MOVWF   d2
DL2:    DECFSZ  d2, F
        GOTO    DL2
        DECFSZ  d1, F
        GOTO    DL1
        RETURN

; =============================================================================
; HANDLE SET
; =============================================================================
HANDLE_SET_INT:
        ; --- KİLİT KONTROLÜ ---
        ; Gece (1) ise, PC komutunu YOK SAY.
        ; Gündüz (0) ise, devam et.
        BTFSC   is_night_mode, 0
        GOTO    MAIN_LOOP

        MOVF    cmd_byte, W
        ANDLW   MASK_DATA_6BIT
        MOVWF   set_int_6
        
        ; PC'den geleni kaydet
        MOVF    set_int_6, W
        MOVWF   cur_percentage  

CALCULATE_STEPS:
        ; Gelen * 20 hesabı
        MOVF    set_int_6, W
        MOVWF   math_tmp_L
        CLRF    math_tmp_H
        
        ; x4
        BCF     STATUS, C
        RLF     math_tmp_L, F
        RLF     math_tmp_H, F   ; *2
        BCF     STATUS, C
        RLF     math_tmp_L, F
        RLF     math_tmp_H, F   ; *4
        
        ; TGT = x4
        MOVF    math_tmp_L, W
        MOVWF   tgt_L
        MOVF    math_tmp_H, W
        MOVWF   tgt_H
        
        ; x16
        BCF     STATUS, C
        RLF     math_tmp_L, F
        RLF     math_tmp_H, F   ; *8
        BCF     STATUS, C
        RLF     math_tmp_L, F
        RLF     math_tmp_H, F   ; *16
        
        ; Topla
        MOVF    math_tmp_L, W
        ADDWF   tgt_L, F
        BTFSC   STATUS, C
        INCF    tgt_H, F
        MOVF    math_tmp_H, W
        ADDWF   tgt_H, F
        
        GOTO    MAIN_LOOP

HANDLE_SET_FRAC:
        GOTO    MAIN_LOOP

; =============================================================================
; HANDLE GET
; =============================================================================
HANDLE_GET:
        MOVF    cmd_byte, W
        XORLW   CMD_CUR_GET_DESIRED_INT
        BTFSC   STATUS, Z
        GOTO    SEND_CUR_PERCENTAGE

        MOVF    cmd_byte, W
        XORLW   CMD_CUR_GET_DESIRED_FRAC
        BTFSC   STATUS, Z
        GOTO    SEND_ZERO

        MOVF    cmd_byte, W
        XORLW   CMD_CUR_GET_OUTDOOR_TEMP_INT
        BTFSC   STATUS, Z
        GOTO    UPDATE_TEMP_AND_SEND_INT
        MOVF    cmd_byte, W
        XORLW   CMD_CUR_GET_OUTDOOR_TEMP_FRAC
        BTFSC   STATUS, Z
        GOTO    UPDATE_TEMP_AND_SEND_FRAC

        MOVF    cmd_byte, W
        XORLW   CMD_CUR_GET_PRESSURE_INT
        BTFSC   STATUS, Z
        GOTO    UPDATE_PRESS_AND_SEND_INT
        MOVF    cmd_byte, W
        XORLW   CMD_CUR_GET_PRESSURE_FRAC
        BTFSC   STATUS, Z
        GOTO    UPDATE_PRESS_AND_SEND_FRAC

        MOVF    cmd_byte, W
        XORLW   CMD_CUR_GET_LIGHT_INT
        BTFSC   STATUS, Z
        GOTO    UPDATE_LIGHT_AND_SEND_INT
        MOVF    cmd_byte, W
        XORLW   CMD_CUR_GET_LIGHT_FRAC
        BTFSC   STATUS, Z
        GOTO    UPDATE_LIGHT_AND_SEND_FRAC

        GOTO    MAIN_LOOP

SEND_CUR_PERCENTAGE:
        MOVF    cur_percentage, W
        CALL    UART_SendByte
        GOTO    MAIN_LOOP

SEND_ZERO:
        MOVLW   0
        CALL    UART_SendByte
        GOTO    MAIN_LOOP

; --- SENSÖRLER ---
UPDATE_TEMP_AND_SEND_INT:
        CALL ReadADC_AN1
        MOVF adc_val, W
        MOVWF rx_tmp
        BCF STATUS, C
        RRF rx_tmp, F
        RRF rx_tmp, F
        MOVF rx_tmp, W
        CALL UART_SendByte
        GOTO MAIN_LOOP

UPDATE_TEMP_AND_SEND_FRAC:
        MOVLW .5
        CALL UART_SendByte
        GOTO MAIN_LOOP

UPDATE_PRESS_AND_SEND_INT:
        CALL ReadADC_AN2
        MOVF adc_val, W
        MOVWF rx_tmp
        BCF STATUS, C
        RRF rx_tmp, F
        MOVF rx_tmp, W
        CALL UART_SendByte
        GOTO MAIN_LOOP

UPDATE_PRESS_AND_SEND_FRAC:
        MOVLW .0
        CALL UART_SendByte
        GOTO MAIN_LOOP

UPDATE_LIGHT_AND_SEND_INT:
        CALL ReadADC_AN0
        MOVF adc_val, W
        MOVWF rx_tmp
        CLRF lux_int
DIV3_L:
        MOVLW .3
        SUBWF rx_tmp, F
        BTFSS STATUS, C
        GOTO DIV3_L_DONE
        INCF lux_int, F
        GOTO DIV3_L
DIV3_L_DONE:
        MOVF lux_int, W
        CALL UART_SendByte
        GOTO MAIN_LOOP

UPDATE_LIGHT_AND_SEND_FRAC:
        MOVLW .0
        CALL UART_SendByte
        GOTO MAIN_LOOP

; =============================================================================
; UART & ADC HELPERS
; =============================================================================
UART_Init:
        BANKSEL TRISC
        BCF     TRISC, 6
        BSF     TRISC, 7
        BANKSEL SPBRG
        MOVLW   SPBRG_VAL
        MOVWF   SPBRG
        BANKSEL TXSTA
        MOVLW   b'00100100'
        MOVWF   TXSTA
        BANKSEL RCSTA
        MOVLW   b'10010000'
        MOVWF   RCSTA
        RETURN

UART_SendByte:
        BANKSEL PIR1
        BTFSS   PIR1, TXIF
        GOTO    $-1
        BANKSEL TXREG
        MOVWF   TXREG
        RETURN

UART_Read_Byte_Safe:
        BANKSEL RCSTA
        BTFSC   RCSTA, OERR
        GOTO    OERR_RESET
        BANKSEL RCREG
        MOVF    RCREG, W
        RETURN
OERR_RESET:
        BCF     RCSTA, CREN
        BSF     RCSTA, CREN
        CLRW
        RETURN

ReadADC_AN0:
        BANKSEL ADCON0
        BCF ADCON0, CHS0
        BCF ADCON0, CHS1
        BCF ADCON0, CHS2
        BSF ADCON0, GO_DONE
        GOTO WAIT_ADC
ReadADC_AN1:
        BANKSEL ADCON0
        BSF ADCON0, CHS0
        BCF ADCON0, CHS1
        BCF ADCON0, CHS2
        BSF ADCON0, GO_DONE
        GOTO WAIT_ADC
ReadADC_AN2:
        BANKSEL ADCON0
        BCF ADCON0, CHS0
        BSF ADCON0, CHS1
        BCF ADCON0, CHS2
        BSF ADCON0, GO_DONE
        GOTO WAIT_ADC
WAIT_ADC:
        BTFSC ADCON0, GO_DONE
        GOTO WAIT_ADC
        BANKSEL ADRESH
        MOVF ADRESH, W
        BANKSEL adc_val
        MOVWF adc_val
        RETURN

        END