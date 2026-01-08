import customtkinter as ctk
from tkinter import messagebox
import sys
import os
import threading
import time
from datetime import datetime

# ==============================================================================
# PROJE: NEXUS CONTROL HUB - ARAYÜZ KATMANI (GUI)
# YAZAR: Suude Kaynak - 152120211110
# TARİH: 2025
# AÇIKLAMA: Bu dosya projenin görsel arayüzünü (Dashboard) oluşturur.
#           CustomTkinter kütüphanesi kullanılarak modern bir görünüm sağlanmıştır.
# ==============================================================================

# --- PATH AYARI ---
# Python'un diğer modülleri (api, config) bulabilmesi için çalışma dizini ayarlanır.
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Kendi yazdığımız modüllerin içe aktarılması
from automation_api import AirConditionerSystemConnection, CurtainControlSystemConnection
import config as cfg

# --- TEMA VE RENK PALETİ AYARLARI ---
# Arayüzün genel renk şeması burada tanımlanır. Değişiklikler buradan tüm uygulamaya yansır.
THEME = {
    "bg_main": "#1a1c20",  # Uygulamanın ana arka plan rengi (Çok koyu gri)
    "bg_panel": "#22252a",  # Panellerin (Klima, Perde vb.) arka planı
    "bg_card": "#2b2f36",  # Kartların (Sayısal değer kutuları) rengi
    "bg_sidebar": "#1e2024",  # Sol menü çubuğunun rengi

    # VURGU VE DURUM RENKLERİ (PASTEL TONLAR)
    "primary": "#c084fc",  # Ana Vurgu Rengi (Soft Mor) - Başlıklar için
    "secondary": "#6ee7b7",  # İkincil Renk (Soft Nane) - Sensörler ve barlar için
    "action": "#6366f1",  # Buton Rengi (İndigo)
    "action_hov": "#4f46e5",  # Butonun üzerine gelinceki rengi (Hover)

    "danger": "#f87171",  # Hata/Offline durumu (Kırmızı)
    "success": "#4ade80",  # Başarılı/Online durumu (Yeşil)
    "text_main": "#e2e8f0",  # Ana metin rengi (Beyazımsı)
    "text_sub": "#94a3b8",  # Alt bilgi metin rengi (Gri)
    "border": "#374151"  # İnce kenarlık çizgilerinin rengi
}

# CustomTkinter genel ayarları
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ModernHomeAutomationGUI:
    """
    Ev otomasyon sistemi için ana grafik arayüz sınıfı.
    Tüm pencereleri, butonları ve seri haberleşme işlemlerini yönetir.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("NEXUS CONTROL HUB v6.0")
        self.root.geometry("1280x820")
        self.root.configure(fg_color=THEME["bg_main"])

        # --- API BAĞLANTILARI (NESNE OLUŞTURMA) ---
        # Henüz portlar açılmadı, sadece nesneler tanımlandı.
        self.ac_api = AirConditionerSystemConnection(com_port=cfg.AC_BOARD_PORT)
        self.curtain_api = CurtainControlSystemConnection(com_port=cfg.CURTAIN_BOARD_PORT)

        # Durum değişkenleri
        self.ac_connected = False  # Klima kartı bağlı mı?
        self.curtain_connected = False  # Perde kartı bağlı mı?
        self.running = True  # Uygulama çalışıyor mu?
        self.last_ambient = 0.0  # Trend okları için son sıcaklık hafızası

        # --- GRID DÜZENİ (LAYOUT) ---
        # Ekranı ikiye bölüyoruz: Sol (Sidebar - Sabit), Sağ (Main Area - Esnek)
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Arayüz elemanlarını yerleştir
        self.setup_ui()

        # Başlangıçta butonları kilitle (Bağlantı yokken basılamasın)
        self.toggle_controls(enable=False)

        # --- ARKA PLAN İŞLEMLERİ (THREADING) ---
        # Seri porttan veri okurken arayüz donmasın diye ayrı bir iş parçacığı başlatıyoruz.
        self.thread = threading.Thread(target=self.background_data_loop, daemon=True)
        self.thread.start()

        # Arayüzü periyodik olarak güncelleme döngüsünü başlat
        self.update_gui_loop()

        # Başlangıç logu
        self.log_message("Sistem Hazır. Bağlantı Bekleniyor...", "info")

    def setup_ui(self):
        """
        Ana arayüz iskeletini kuran fonksiyon.
        Sidebar ve Ana Alanı çağırır.
        """
        # 1. Sol Menü (Sidebar)
        self.create_sidebar()

        # 2. Ana İçerik Alanı (Main Area)
        self.main_area = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)

        # Ana alanın grid yapılandırması
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        # Alt bileşenleri oluştur
        self.create_header()  # Üst Başlık ve Saat
        self.create_dashboard()  # Paneller (Klima, Perde)
        self.create_terminal()  # Alt Log Ekranı

        # Pencere kapatılınca çalışacak fonksiyon
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_sidebar(self):
        """
        Sol taraftaki navigasyon menüsünü, logoyu ve bağlantı butonunu oluşturur.
        """
        sidebar = ctk.CTkFrame(self.root, fg_color=THEME["bg_sidebar"], width=260, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)  # Boyutun içeriğe göre değişmesini engelle

        # --- LOGO ALANI ---
        logo_box = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_box.pack(fill="x", padx=25, pady=(40, 30))

        # Sol taraftaki renkli dikey çubuk (Estetik detay)
        bar = ctk.CTkFrame(logo_box, width=5, height=44, fg_color=THEME["primary"], corner_radius=2)
        bar.pack(side="left", padx=(0, 12))

        text_box = ctk.CTkFrame(logo_box, fg_color="transparent")
        text_box.pack(side="left")

        # Marka İsmi
        ctk.CTkLabel(text_box, text="NEXUS", font=ctk.CTkFont(family="Arial", size=28, weight="bold"),
                     text_color="white", height=30).pack(anchor="w", pady=(0, 0))
        ctk.CTkLabel(text_box, text="ENTERPRISE", font=ctk.CTkFont(size=11, weight="bold", family="Arial"),
                     text_color=THEME["primary"], height=14).pack(anchor="w", pady=(0, 0))

        # --- MENÜ BUTONLARI ---
        nav_lbl = ctk.CTkLabel(sidebar, text="MAIN MENU", font=ctk.CTkFont(size=11, weight="bold"),
                               text_color=THEME["text_sub"])
        nav_lbl.pack(anchor="w", padx=25, pady=(0, 10))

        # Aktif Buton (Dashboard)
        btn_dash = ctk.CTkButton(sidebar, text="  Dashboard", anchor="w", fg_color=THEME["bg_card"], text_color="white",
                                 hover=False, height=42, corner_radius=8, font=ctk.CTkFont(weight="bold"))
        btn_dash.pack(fill="x", padx=15, pady=4)

        # Pasif Butonlar (Görsel amaçlı)
        ctk.CTkButton(sidebar, text="  Analytics", anchor="w", fg_color="transparent", text_color=THEME["text_sub"],
                      hover_color=THEME["bg_panel"], height=42, corner_radius=8).pack(fill="x", padx=15, pady=2)
        ctk.CTkButton(sidebar, text="  Configuration", anchor="w", fg_color="transparent", text_color=THEME["text_sub"],
                      hover_color=THEME["bg_panel"], height=42, corner_radius=8).pack(fill="x", padx=15, pady=2)

        # --- MODÜL DURUM GÖSTERGELERİ ---
        ctk.CTkFrame(sidebar, height=1, fg_color=THEME["border"]).pack(fill="x", padx=25, pady=25)  # Ayırıcı Çizgi

        ctk.CTkLabel(sidebar, text="MODULE STATUS", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=THEME["text_sub"]).pack(anchor="w", padx=25, pady=(0, 12))

        # Modül durumlarını tutan referanslar (Daha sonra rengini değiştirmek için)
        self.mod_ac_frame = self.create_module_status_row(sidebar, "AC Unit Controller")
        self.mod_cur_frame = self.create_module_status_row(sidebar, "Curtain & Sensors")

        # --- BAĞLANTI PANELİ (ALT KISIM) ---
        spacer = ctk.CTkLabel(sidebar, text="")
        spacer.pack(expand=True)  # Alta itmek için boşluk

        conn_box = ctk.CTkFrame(sidebar, fg_color=THEME["bg_panel"], corner_radius=12)
        conn_box.pack(fill="x", padx=15, pady=20)

        # Bağlantı Butonu
        self.btn_connect = ctk.CTkButton(conn_box, text="BAĞLANTIYI BAŞLAT", command=self.connect_system,
                                         fg_color=THEME["action"], hover_color=THEME["action_hov"], text_color="white",
                                         height=48, font=ctk.CTkFont(weight="bold"), corner_radius=8)
        self.btn_connect.pack(fill="x", padx=10, pady=10)

        # Port Bilgisi Gösterimi
        info_grid = ctk.CTkFrame(conn_box, fg_color="transparent")
        info_grid.pack(fill="x", padx=10, pady=(0, 10))

        self.lbl_port_ac = ctk.CTkLabel(info_grid, text=f"AC: COM{cfg.AC_BOARD_PORT}",
                                        font=ctk.CTkFont(size=10, weight="bold"), text_color=THEME["text_sub"])
        self.lbl_port_ac.pack(side="left", padx=5)

        self.lbl_port_cur = ctk.CTkLabel(info_grid, text=f"CUR: COM{cfg.CURTAIN_BOARD_PORT}",
                                         font=ctk.CTkFont(size=10, weight="bold"), text_color=THEME["text_sub"])
        self.lbl_port_cur.pack(side="right", padx=5)

    def create_module_status_row(self, parent, title):
        """Yardımcı Fonksiyon: Sidebar'daki 'Active/Offline' satırlarını oluşturur."""
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=25, pady=5)

        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=12), text_color="#d1d5db").pack(side="left")

        # Durum Label (Başlangıçta OFFLINE)
        lbl = ctk.CTkLabel(f, text="OFFLINE", font=ctk.CTkFont(size=10, weight="bold"), text_color=THEME["text_sub"])
        lbl.pack(side="right")

        dot = ctk.CTkLabel(f, text="●", font=ctk.CTkFont(size=10), text_color=THEME["text_sub"])
        dot.pack(side="right", padx=(0, 6))

        return {"label": lbl, "dot": dot}

    def update_sidebar_status(self, ac_online, cur_online):
        """Bağlantı durumuna göre sidebar'daki renkleri (Yeşil/Kırmızı) günceller."""

        def set_status(widget_dict, is_online):
            if is_online:
                widget_dict["label"].configure(text="ACTIVE", text_color=THEME["success"])
                widget_dict["dot"].configure(text_color=THEME["success"])
            else:
                widget_dict["label"].configure(text="OFFLINE", text_color=THEME["danger"])
                widget_dict["dot"].configure(text_color=THEME["danger"])

        set_status(self.mod_ac_frame, ac_online)
        set_status(self.mod_cur_frame, cur_online)

    def create_header(self):
        """Sağ taraftaki ana başlık ve saat göstergesini oluşturur."""
        head = ctk.CTkFrame(self.main_area, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        ctk.CTkLabel(head, text="Kontrol Paneli", font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=THEME["text_main"]).pack(side="left")

        self.lbl_time = ctk.CTkLabel(head, text="--:--:--", font=ctk.CTkFont(family="Consolas", size=20, weight="bold"),
                                     text_color=THEME["primary"])
        self.lbl_time.pack(side="right")

    def create_dashboard(self):
        """Dashboard grid yapısını oluşturur (Klima ve Perde panelleri için yer açar)."""
        self.dash_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.dash_frame.grid(row=1, column=0, sticky="nsew")

        # 2 sütunlu yapı
        self.dash_frame.grid_columnconfigure(0, weight=1)
        self.dash_frame.grid_columnconfigure(1, weight=1)
        self.dash_frame.grid_rowconfigure(0, weight=1)

        self.create_ac_panel(0, 0)  # Sol Panel: Klima
        self.create_curtain_panel(0, 1)  # Sağ Panel: Perde

    def create_ac_panel(self, r, c):
        """Klima (AC) Kontrol Panelini Oluşturur."""
        frame = ctk.CTkFrame(self.dash_frame, fg_color=THEME["bg_panel"], corner_radius=16, border_width=1,
                             border_color=THEME["border"])
        frame.grid(row=r, column=c, sticky="nsew", padx=(0, 12), pady=0)
        frame.grid_rowconfigure(1, weight=1)

        # Başlık
        h = ctk.CTkFrame(frame, fg_color="transparent")
        h.pack(fill="x", padx=25, pady=20)
        ctk.CTkLabel(h, text="İKLİMLENDİRME (AC)", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=THEME["primary"]).pack(side="left")
        ctk.CTkLabel(h, text="BOARD #1", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_sub"]).pack(
            side="right")

        # Büyük Sıcaklık Göstergesi
        main_disp = ctk.CTkFrame(frame, fg_color="transparent")
        main_disp.pack(fill="both", expand=True, padx=25)

        temp_card = ctk.CTkFrame(main_disp, fg_color=THEME["bg_card"], corner_radius=12)
        temp_card.pack(fill="x", pady=(10, 20))

        ctk.CTkLabel(temp_card, text="GÜNCEL SICAKLIK", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=THEME["text_sub"]).pack(pady=(15, 0))
        val_box = ctk.CTkFrame(temp_card, fg_color="transparent")
        val_box.pack(pady=10)

        self.lbl_ac_ambient = ctk.CTkLabel(val_box, text="--.--",
                                           font=ctk.CTkFont(family="Arial", size=60, weight="bold"),
                                           text_color=THEME["text_main"])
        self.lbl_ac_ambient.pack(side="left")
        ctk.CTkLabel(val_box, text="°C", font=ctk.CTkFont(size=20), text_color=THEME["primary"]).pack(side="left",
                                                                                                      padx=(5, 0),
                                                                                                      pady=(12, 0))
        # Trend Oku (Artıyor/Azalıyor)
        self.lbl_trend_ac = ctk.CTkLabel(val_box, text="", font=ctk.CTkFont(size=24))
        self.lbl_trend_ac.pack(side="left", padx=(15, 0))

        # Metrikler (Fan Hızı ve Hedef Sıcaklık Barları)
        metrics = ctk.CTkFrame(frame, fg_color="transparent")
        metrics.pack(fill="x", padx=25, pady=10)
        self.bar_fan = self.create_metric_row(metrics, "Fan Hızı", "RPS", THEME["primary"])
        self.bar_target = self.create_metric_row(metrics, "Hedef Sıcaklık", "°C", THEME["text_sub"])

        # Kontrol (Input) Alanı
        ctrl = ctk.CTkFrame(frame, fg_color=THEME["bg_card"], corner_radius=12)
        ctrl.pack(fill="x", padx=25, pady=25)

        ctk.CTkLabel(ctrl, text="Hedef Sıcaklık Ayarı", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=THEME["text_sub"]).pack(anchor="w", padx=20, pady=(15, 5))
        inp = ctk.CTkFrame(ctrl, fg_color="transparent")
        inp.pack(fill="x", padx=20, pady=(0, 20))

        self.entry_temp = ctk.CTkEntry(inp, width=85, height=40, justify="center",
                                       font=ctk.CTkFont(size=18, weight="bold"), fg_color=THEME["bg_main"],
                                       border_color=THEME["border"])
        self.entry_temp.insert(0, "25.0")
        self.entry_temp.pack(side="left", padx=(0, 12))

        self.btn_set_temp = ctk.CTkButton(inp, text="AYARLA GÖNDER", command=self.cmd_set_temp, height=40,
                                          fg_color=THEME["action"], hover_color=THEME["action_hov"], text_color="white",
                                          font=ctk.CTkFont(weight="bold"))
        self.btn_set_temp.pack(side="left", fill="x", expand=True)

    def create_curtain_panel(self, r, c):
        """Perde ve Sensörler (Board 2) Panelini Oluşturur."""
        frame = ctk.CTkFrame(self.dash_frame, fg_color=THEME["bg_panel"], corner_radius=16, border_width=1,
                             border_color=THEME["border"])
        frame.grid(row=r, column=c, sticky="nsew", padx=(0, 0), pady=0)

        # Sensörleri grid yapısına oturtmak için konfigürasyon
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        # Başlık
        h = ctk.CTkFrame(frame, fg_color="transparent")
        h.grid(row=0, column=0, columnspan=2, sticky="ew", padx=25, pady=20)
        ctk.CTkLabel(h, text="SENSÖRLER & PERDE", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=THEME["secondary"]).pack(side="left")
        ctk.CTkLabel(h, text="BOARD #2", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_sub"]).pack(
            side="right")

        # Sensör Kutucukları (Grid Yerleşimi)
        self.lbl_cur_temp = self.create_sensor_box(frame, 1, 0, "Dış Sıcaklık", "°C")
        self.lbl_cur_press = self.create_sensor_box(frame, 1, 1, "Hava Basıncı", "hPa")
        self.lbl_cur_light = self.create_sensor_box(frame, 2, 0, "Işık Şiddeti", "Lux")
        self.lbl_cur_stat = self.create_sensor_box(frame, 2, 1, "Perde Açıklığı", "%", color=THEME["secondary"])

        # --- Perde Kontrol Alanı (Slider)
        ctrl = ctk.CTkFrame(frame, fg_color=THEME["bg_card"], corner_radius=12)
        ctrl.grid(row=4, column=0, columnspan=2, sticky="ew", padx=25, pady=25)

        ctk.CTkLabel(ctrl, text="Perde Pozisyon Kontrolü", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=THEME["text_sub"]).pack(anchor="w", padx=20, pady=(15, 5))

        # Slider container
        self.curtain_slider_wrap = ctk.CTkFrame(ctrl, fg_color="transparent")
        self.curtain_slider_wrap.pack(fill="x", padx=20, pady=10)

        self.slider_curtain = ctk.CTkSlider(self.curtain_slider_wrap, from_=0, to=100, number_of_steps=100, height=20,
                                            progress_color=THEME["secondary"], button_color="white",
                                            button_hover_color=THEME["secondary"])
        self.slider_curtain.set(0)
        self.slider_curtain.pack(fill="x")

        # “Blur/engel” overlay (CustomTkinter gerçek blur yapmaz; ama opak panel ile aynı etki)
        self.curtain_lock_overlay = ctk.CTkFrame(
            self.curtain_slider_wrap,
            fg_color=THEME["bg_panel"],  # koyu bir katman
            corner_radius=10
        )
        self.curtain_lock_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.lbl_curtain_lock = ctk.CTkLabel(
            self.curtain_lock_overlay,
            text="GÜNDÜZ MODU: Perde kontrolü kilitli\n(Gece olunca aktif olur)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["text_sub"],
            justify="center"
        )
        self.lbl_curtain_lock.pack(expand=True)

        self.btn_set_curtain = ctk.CTkButton(ctrl, text="POZİSYONU UYGULA", command=self.cmd_set_curtain, height=40,
                                             fg_color=THEME["action"], hover_color=THEME["action_hov"],
                                             text_color="white", font=ctk.CTkFont(weight="bold"))
        self.btn_set_curtain.pack(fill="x", padx=20, pady=(0, 20))

    def create_terminal(self):
        """Alt kısımdaki Log/Terminal ekranını oluşturur."""
        term_frame = ctk.CTkFrame(self.main_area, fg_color=THEME["bg_panel"], height=130, corner_radius=12,
                                  border_width=1, border_color=THEME["border"])
        term_frame.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        term_frame.pack_propagate(False)

        top = ctk.CTkFrame(term_frame, fg_color="transparent", height=24)
        top.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(top, text="> SİSTEM GÜNLÜĞÜ", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                     text_color=THEME["primary"]).pack(side="left")

        self.log_box = ctk.CTkTextbox(term_frame, fg_color="#0a0a0a", font=ctk.CTkFont(family="Consolas", size=11),
                                      text_color="#d4d4d4", corner_radius=8)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_box.configure(state="disabled")  # Kullanıcı elle yazamasın

        # Log renklendirme etiketleri
        self.log_box.tag_config("info", foreground=THEME["secondary"])
        self.log_box.tag_config("error", foreground=THEME["danger"])
        self.log_box.tag_config("cmd", foreground=THEME["primary"])

    def create_metric_row(self, parent, title, unit, color):
        """Yardımcı Fonksiyon: Progress bar içeren metrik satırı oluşturur."""
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=6)

        head = ctk.CTkFrame(f, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkLabel(head, text=title, text_color=THEME["text_sub"], font=ctk.CTkFont(size=12)).pack(side="left")
        val_lbl = ctk.CTkLabel(head, text=f"-- {unit}", font=ctk.CTkFont(size=12, weight="bold"), text_color=color)
        val_lbl.pack(side="right")

        prog = ctk.CTkProgressBar(f, height=6, progress_color=color, fg_color=THEME["bg_card"], corner_radius=3)
        prog.set(0)
        prog.pack(fill="x", pady=(6, 5))
        return {"label": val_lbl, "prog": prog, "unit": unit}

    def create_sensor_box(self, parent, r, c, title, unit, color="white"):
        """Yardımcı Fonksiyon: Sensör verisi gösteren kare kutucuk oluşturur."""
        f = ctk.CTkFrame(parent, fg_color=THEME["bg_card"], corner_radius=12)
        f.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_sub"]).pack(
            anchor="w", padx=20, pady=(18, 0))
        lbl = ctk.CTkLabel(f, text="--", font=ctk.CTkFont(size=26, weight="bold"), text_color=color)
        lbl.pack(anchor="w", padx=20, pady=(0, 18))
        return {"label": lbl, "unit": unit}

    def toggle_controls(self, enable):
        """
        Bağlantı durumuna göre butonları ve girişleri Aktif/Pasif yapar.
        Bağlantı yoksa kullanıcı komut gönderemez.
        """
        state = "normal" if enable else "disabled"
        self.entry_temp.configure(state=state)
        self.btn_set_temp.configure(state=state)
        self.slider_curtain.configure(state=state)
        self.btn_set_curtain.configure(state=state)

        if enable:
            self.btn_connect.configure(text="SİSTEM BAĞLI", state="disabled", fg_color=THEME["bg_card"],
                                       text_color=THEME["success"])
        else:
            self.btn_connect.configure(text="BAĞLANTIYI BAŞLAT", state="normal", fg_color=THEME["action"],
                                       text_color="white")

    def log_message(self, msg, tag="info"):
        """Ekrana log basar. Otomatik timestamp ve renk ekler."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")  # Yazmak için kilidi aç
        self.log_box.insert("end", f"[{timestamp}] {msg}\n", tag)
        self.log_box.see("end")  # En sona kaydır
        self.log_box.configure(state="disabled")  # Tekrar kilitle

    def background_data_loop(self):
        """
        ARKA PLAN THREAD:
        Seri porttan veri okuma işlemlerini burada yaparız ki arayüz donmasın.
        """
        while self.running:
            try:
                if self.ac_connected: self.ac_api.update()
                if self.curtain_connected: self.curtain_api.update()
                time.sleep(0.5)  # İşlemciyi yormamak için kısa bekleme
            except:
                pass

    def update_gui_loop(self):
        """
        ANA THREAD DÖNGÜSÜ:
        Arka planda (API'de) güncellenen verileri ekrana (Label'lara) yazar.
        Tkinter'da GUI güncellemeleri SADECE ana thread'de yapılmalıdır.
        """
        if not self.running: return
        self.lbl_time.configure(text=datetime.now().strftime("%H:%M:%S"))

        try:
            # --- KLIMA VERİLERİNİ GÜNCELLE ---
            if self.ac_connected:
                temp = self.ac_api.getAmbientTemp()
                self.lbl_ac_ambient.configure(text=f"{temp:.2f}")

                # Trend oku mantığı
                if temp > self.last_ambient:
                    self.lbl_trend_ac.configure(text="▲", text_color=THEME["danger"])
                elif temp < self.last_ambient:
                    self.lbl_trend_ac.configure(text="▼", text_color=THEME["secondary"])
                else:
                    self.lbl_trend_ac.configure(text="", text_color=THEME["text_sub"])
                self.last_ambient = temp

                fan = self.ac_api.getFanSpeed()
                self.bar_fan["label"].configure(text=f"{fan} RPS")
                self.bar_fan["prog"].set(fan / 255)  # Progress bar 0-1 arası çalışır

                targ = self.ac_api.getDesiredTemp()
                self.bar_target["label"].configure(text=f"{targ:.1f} °C")
                self.bar_target["prog"].set(targ / 50)

                # --- PERDE VERİLERİNİ GÜNCELLE ---
                if self.curtain_connected:
                    self.lbl_cur_temp["label"].configure(
                        text=f"{self.curtain_api.getOutdoorTemp():.1f} {self.lbl_cur_temp['unit']}")
                    self.lbl_cur_press["label"].configure(
                        text=f"{self.curtain_api.getOutdoorPress():.1f} {self.lbl_cur_press['unit']}")
                    self.lbl_cur_light["label"].configure(
                        text=f"{self.curtain_api.getLightIntensity():.1f} {self.lbl_cur_light['unit']}")

                    cur_val = self.curtain_api.curtainStatus
                    self.lbl_cur_stat["label"].configure(text=f"%{cur_val:.0f}")

                    lux = self.curtain_api.getLightIntensity()

                    is_night = lux < 12.0

                    if not hasattr(self, "_last_lux"):
                        self._last_lux = lux

                    if abs(lux - self._last_lux) >= 0.1:
                        self.log_message(f"LDR Lux güncellendi: {lux:.1f} Lux", "info")
                        self._last_lux = lux

                    # Gece ise KİLİTLE (Disabled), Gündüz ise AÇ (Normal)

                    if is_night:
                        # GECE MODU -> KULLANICI KİLİTLİ
                        self.slider_curtain.configure(state="disabled")
                        self.btn_set_curtain.configure(state="disabled")

                        # Kullanıcıya neden kilitli olduğunu söyleyen yazıyı göster
                        self.curtain_lock_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
                        self.lbl_curtain_lock.configure(text="GECE MODU AKTİF\nOtomatik Kapatıldı\nKontrol Kilitli")

                    else:
                        # GÜNDÜZ MODU -> KULLANICI SERBEST
                        self.slider_curtain.configure(state="normal")
                        self.btn_set_curtain.configure(state="normal")

                        # Kilitleme yazısını kaldır
                        self.curtain_lock_overlay.place_forget()


        except Exception as e:
            print(f"GUI Update Hatası: {e}")

        # 200 ms sonra bu fonksiyonu tekrar çağır (Sonsuz Döngü)
        self.root.after(200, self.update_gui_loop)

    def connect_system(self):
        """Bağlantıyı Başlat butonuna basılınca çalışır."""
        self.log_message("Bağlantı başlatılıyor...", "cmd")
        self.root.update()
        try:
            # Seri portları açmayı dene
            ok_ac = self.ac_api.open()
            ok_cur = self.curtain_api.open()

            self.ac_connected = ok_ac
            self.curtain_connected = ok_cur

            # Sidebar'daki renkleri güncelle
            self.update_sidebar_status(ok_ac, ok_cur)

            if ok_ac or ok_cur:
                self.toggle_controls(enable=True)
                self.log_message(f"Bağlantı Başarılı (AC:{ok_ac}, CUR:{ok_cur})", "info")
            else:
                self.log_message("HATA: Portlara erişilemedi.", "error")
                messagebox.showerror("Bağlantı Hatası", "Portlar açılamadı.")
        except Exception as e:
            self.log_message(f"Kritik Hata: {e}", "error")

    def cmd_set_temp(self):
        """Klima 'Ayarla Gönder' butonu işlevi."""
        try:
            val = float(self.entry_temp.get())
            if 10 <= val <= 50:
                self.ac_api.setDesiredTemp(val)
                self.log_message(f"AC Komut: {val}°C", "cmd")
            else:
                messagebox.showwarning("Limit", "10-50 arası giriniz.")
        except:
            messagebox.showerror("Hata", "Sayı giriniz.")

    def cmd_set_curtain(self):
        """Perde 'Pozisyonu Uygula' butonu işlevi."""
        val = self.slider_curtain.get()
        self.curtain_api.setCurtainStatus(val)
        self.log_message(f"Perde Komut: %{val:.0f}", "cmd")

    def on_closing(self):
        """Pencere kapatılırken portları temizler ve thread'i durdurur."""
        self.running = False
        if self.ac_connected: self.ac_api.close()
        if self.curtain_connected: self.curtain_api.close()
        self.root.destroy()
        sys.exit()


if __name__ == "__main__":
    print("Lütfen 'main.py' dosyasını çalıştırın.")