import sys
import os
import torch
import traceback
import json
import multiprocess
import threading
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QCheckBox, QSlider, QFrame, QStackedWidget,
                             QComboBox, QTreeWidget, QTreeWidgetItem, QSizePolicy, QMessageBox, QSpinBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QIcon, QFont, QColor, QPainter, QBrush, QPen, QPolygon

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from stockfish_bot import StockfishBot
from overlay import run as run_overlay

# Translations
TRANSLATIONS = {
    "en": {
        "title": "UmbrellaChess",
        "general": "General",
        "legit": "Legitimization",
        "visuals": "Visuals",
        "open_browser": "Open Browser",
        "opening": "Opening...",
        "browser_open": "Browser Open",
        "enable_bot": "Enable Bot",
        "usage": "Usage (Model)",
        "visibility": "Visibility",
        "invis": "Work in Invisibility (Mouseless)",
        "topmost": "Window on Top",
        "chance": "Chance of Triggering",
        "delay": "Additional Delay",
        "info": "Lower accuracy and higher delay make the bot appear more human.",
        "moves": "Match Moves",
        "col_num": "#",
        "col_white": "White",
        "col_black": "Black",
        "language": "Language",
        "automation": "Automation",
        "auto_match": "Auto Match",
        "auto_puzzle": "Auto Puzzle",
        "force_solid": "Force Solid Openings",
        "err_browser": "Please open the browser first!",
    },
    "ru": {
        "title": "UmbrellaChess",
        "general": "Общее",
        "legit": "Легитимизация",
        "visuals": "Визуал",
        "open_browser": "Открыть браузер",
        "opening": "Открываю...",
        "browser_open": "Браузер открыт",
        "enable_bot": "Включить бота",
        "usage": "Использование (Модель)",
        "visibility": "Видимость",
        "invis": "Работа в невидимости (Без мыши)",
        "topmost": "Поверх всех окон",
        "chance": "Шанс срабатывания",
        "delay": "Доп. задержка",
        "info": "Низкая точность и задержка делают бота более похожим на человека.",
        "moves": "Ходы матча",
        "col_num": "№",
        "col_white": "Белые",
        "col_black": "Черные",
        "language": "Язык",
        "automation": "Автоматизация",
        "auto_match": "Авто-Поиск Игры",
        "auto_puzzle": "Авто-Пазлы",
        "force_solid": "Сильные дебюты",
        "err_browser": "Сначала откройте браузер!",
    }
}

DEFAULT_CONFIG = {
    "model": "rapid",
    "accuracy": 100,
    "latency": 0.1,
    "mouseless": False,
    "manual": False,
    "bot_elo": 1500,
    "opp_elo": 1500,
    "topmost": True,
    "language": "en",
    "auto_match": False,

    "auto_puzzle": False,
    "force_solid": True
}

class UmbrellaStyle:
    BG_DARK = "#121212"
    BG_PANEL = "#1E1E1E"
    ACCENT_RED = "#D32F2F"
    TEXT_WHITE = "#E0E0E0"
    TEXT_GRAY = "#A0A0A0"
    
    STYLESHEET = f"""
        QMainWindow {{
            background-color: {BG_DARK};
            color: {TEXT_WHITE};
        }}
        QWidget {{
            background-color: {BG_DARK};
            color: {TEXT_WHITE};
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 14px;
        }}
        QFrame#SideBar {{
            background-color: {BG_PANEL};
            border-right: 1px solid #333;
        }}
        QFrame#ContentPanel {{
            background-color: {BG_DARK};
        }}
        QPushButton {{
            background-color: {BG_PANEL};
            border: 1px solid #444;
            border-radius: 5px;
            padding: 8px;
            color: {TEXT_WHITE};
        }}
        QPushButton:hover {{
            background-color: #333;
            border-color: #555;
        }}
        QPushButton:pressed {{
            background-color: {ACCENT_RED};
            border-color: {ACCENT_RED};
        }}
        QPushButton#SidebarBtn {{
            background-color: transparent;
            border: none;
            text-align: left;
            padding: 12px;
            border-radius: 0px;
        }}
        QPushButton#SidebarBtn:checked {{
            background-color: {BG_DARK};
            border-left: 3px solid {ACCENT_RED};
            color: {ACCENT_RED};
        }}
        QPushButton#SidebarBtn:hover {{
            background-color: #252525;
        }}
        QLabel#Header {{
            color: {ACCENT_RED};
            font-weight: bold;
            font-size: 18px;
        }}
        QLabel#SectionHeader {{
            color: {TEXT_GRAY};
            font-weight: bold;
            font-size: 12px;
            padding-bottom: 5px;
        }}
        QSlider::groove:horizontal {{
            border: 1px solid #333;
            height: 8px;
            background: #252525;
            margin: 2px 0;
            border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background: {ACCENT_RED};
            border: 1px solid {ACCENT_RED};
            width: 18px;
            height: 18px;
            margin: -7px 0;
            border-radius: 9px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid #555;
            background: #252525;
        }}
        QCheckBox::indicator:checked {{
            background: {ACCENT_RED};
            border-color: {ACCENT_RED};
        }}
        QTreeWidget {{
            background-color: #1A1A1A;
            border: 1px solid #333;
            color: {TEXT_WHITE};
        }}
        QHeaderView::section {{
            background-color: {BG_PANEL};
            color: {TEXT_WHITE};
            border: none;
            padding: 4px;
        }}
        QComboBox {{
            background-color: {BG_PANEL};
            padding: 5px;
            border: 1px solid #444;
            border-radius: 4px;
        }}
    """

class UmbrellaLogo(QWidget):
    def __init__(self, size=32, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw Octagon Segments
        center = QPoint(self.width() // 2, self.height() // 2)
        radius = min(self.width(), self.height()) // 2
        
        for i in range(8):
            angle_start = i * 45
            angle_end = (i + 1) * 45
            
            # Create triangle polygon
            points = [center]
            # Point 1 (Current Angle)
            import math
            rad1 = math.radians(angle_start)
            x1 = center.x() + radius * math.cos(rad1)
            y1 = center.y() + radius * math.sin(rad1)
            points.append(QPoint(int(x1), int(y1)))
            
            # Point 2 (Next Angle)
            rad2 = math.radians(angle_end)
            x2 = center.x() + radius * math.cos(rad2)
            y2 = center.y() + radius * math.sin(rad2)
            points.append(QPoint(int(x2), int(y2)))
            
            poly = QPolygon(points)
            
            color = QColor("#D32F2F") if i % 2 == 0 else QColor("white")
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(poly)

class SidebarButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("SidebarBtn")
        self.setCheckable(True)
        self.setAutoExclusive(True)

class MoveTree(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = DEFAULT_CONFIG.copy()
        self.load_config()
        self.tr_data = TRANSLATIONS[self.config.get("language", "en")]
        
        self.setWindowTitle(self.tr("title"))
        self.resize(850, 650)
        self.setWindowIcon(QIcon("src/assets/pawn_32x32.png"))
        
        self.running = False
        self.browser_open = False
        self.chrome = None
        self.bot_process = None
        self.overlay_process = None
        self.pipe = None
        self.moves_count = 0
        
        self.setup_ui()
        self.apply_style()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_state_update)
        self.timer.start(100)

    def tr(self, key):
        return self.tr_data.get(key, key)

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("SideBar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 20, 0, 20)
        side_layout.setSpacing(5)

        # Header with Logo
        header_layout = QHBoxLayout()
        header_logo = UmbrellaLogo(32)
        
        header_lbl = QLabel("UmbrellaChess")
        header_lbl.setObjectName("Header")
        
        header_layout.addSpacing(15)
        header_layout.addWidget(header_logo)
        header_layout.addWidget(header_lbl)
        header_layout.addStretch()
        side_layout.addLayout(header_layout)
        side_layout.addSpacing(30)

        # Tabs
        self.btn_general = SidebarButton(f"  {self.tr('general')}")
        self.btn_general.setChecked(True)
        self.btn_general.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        
        self.btn_legit = SidebarButton(f"  {self.tr('legit')}")
        self.btn_legit.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        self.btn_visuals = SidebarButton(f"  {self.tr('visuals')}")
        self.btn_visuals.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        
        side_layout.addWidget(self.btn_general)
        side_layout.addWidget(self.btn_legit)
        side_layout.addWidget(self.btn_visuals)
        side_layout.addStretch()
        
        self.btn_browser = QPushButton(self.tr('open_browser'))
        self.btn_browser.clicked.connect(self.open_browser)
        side_layout.addWidget(self.btn_browser)
        
        # Content
        content_frame = QFrame()
        content_frame.setObjectName("ContentPanel")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 30, 30, 30)

        self.stack = QStackedWidget()
        
        # -- General Tab --
        self.tab_general = QWidget()
        gen_layout = QVBoxLayout(self.tab_general)
        gen_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        lbl_main = QLabel(self.tr('general'))
        lbl_main.setObjectName("Header")
        gen_layout.addWidget(lbl_main)
        gen_layout.addSpacing(20)

        self.chk_enable = QCheckBox(self.tr('enable_bot'))
        self.chk_enable.setFont(QFont("Segoe UI", 12))
        self.chk_enable.clicked.connect(self.toggle_bot)
        gen_layout.addWidget(self.chk_enable)
        gen_layout.addSpacing(20)
        
        gen_layout.addWidget(QLabel(self.tr('usage'), objectName="SectionHeader"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["Rapid", "Blitz", "Bullet", "Ultra Bullet"])
        self.model_combo.setCurrentText(self.config.get("model", "Rapid").capitalize())

        gen_layout.addWidget(self.model_combo)
        
        self.chk_force_solid = QCheckBox(self.tr('force_solid'))
        self.chk_force_solid.setChecked(self.config.get("force_solid", True))
        gen_layout.addWidget(self.chk_force_solid)

        gen_layout.addSpacing(20)
        
        gen_layout.addWidget(QLabel(self.tr('automation'), objectName="SectionHeader"))
        self.chk_automatch = QCheckBox(self.tr('auto_match'))
        self.chk_automatch.setChecked(self.config.get("auto_match", False))
        gen_layout.addWidget(self.chk_automatch)
        
        self.chk_autopuzzle = QCheckBox(self.tr('auto_puzzle'))
        self.chk_autopuzzle.setChecked(self.config.get("auto_puzzle", False))
        gen_layout.addWidget(self.chk_autopuzzle)
        gen_layout.addWidget(self.chk_autopuzzle)
        gen_layout.addSpacing(20)

        gen_layout.addWidget(QLabel("Elo Settings", objectName="SectionHeader"))
        elo_layout = QHBoxLayout()
        
        self.spin_bot_elo = QSpinBox()
        self.spin_bot_elo.setRange(0, 3500)
        self.spin_bot_elo.setValue(self.config.get("bot_elo", 1500))
        self.spin_bot_elo.setPrefix("Bot: ")
        
        self.spin_opp_elo = QSpinBox()
        self.spin_opp_elo.setRange(0, 3500)
        self.spin_opp_elo.setValue(self.config.get("opp_elo", 1500))
        self.spin_opp_elo.setPrefix("Opp: ")

        elo_layout.addWidget(self.spin_bot_elo)
        elo_layout.addWidget(self.spin_opp_elo)
        gen_layout.addLayout(elo_layout)
        gen_layout.addSpacing(20)

        gen_layout.addWidget(QLabel(self.tr('visibility'), objectName="SectionHeader"))
        self.chk_mouseless = QCheckBox(self.tr('invis'))
        self.chk_mouseless.setChecked(self.config.get("mouseless", False))
        gen_layout.addWidget(self.chk_mouseless)
        
        self.chk_topmost = QCheckBox(self.tr('topmost'))
        self.chk_topmost.setChecked(self.config.get("topmost", True))
        self.chk_topmost.toggled.connect(self.toggle_topmost)
        gen_layout.addWidget(self.chk_topmost)

        gen_layout.addSpacing(20)
        gen_layout.addWidget(QLabel(self.tr('language'), objectName="SectionHeader"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Russian"])
        self.lang_combo.setCurrentIndex(0 if self.config.get("language") == "en" else 1)
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        gen_layout.addWidget(self.lang_combo)
        
        self.stack.addWidget(self.tab_general)
        
        # -- Legit Tab --
        self.tab_legit = QWidget()
        leg_layout = QVBoxLayout(self.tab_legit)
        leg_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        lbl_legit = QLabel(self.tr('legit'))
        lbl_legit.setObjectName("Header")
        leg_layout.addWidget(lbl_legit)
        leg_layout.addSpacing(20)
        
        self.lbl_acc_val = QLabel(f"{self.tr('chance')}: {self.config['accuracy']}%")
        leg_layout.addWidget(self.lbl_acc_val)
        self.slider_acc = QSlider(Qt.Orientation.Horizontal)
        self.slider_acc.setRange(0, 100)
        self.slider_acc.setValue(self.config.get("accuracy", 100))
        self.slider_acc.valueChanged.connect(lambda v: self.lbl_acc_val.setText(f"{self.tr('chance')}: {v}%"))
        leg_layout.addWidget(self.slider_acc)
        leg_layout.addSpacing(20)
        
        self.lbl_lat_val = QLabel(f"{self.tr('delay')}: {self.config['latency']} sec")
        leg_layout.addWidget(self.lbl_lat_val)
        self.slider_lat = QSlider(Qt.Orientation.Horizontal)
        self.slider_lat.setRange(0, 50)
        self.slider_lat.setValue(int(self.config.get("latency", 0.1) * 10))
        self.slider_lat.valueChanged.connect(lambda v: self.lbl_lat_val.setText(f"{self.tr('delay')}: {v/10} sec"))
        leg_layout.addWidget(self.slider_lat)
        leg_layout.addSpacing(20)
        
        lbl_info = QLabel(self.tr('info'))
        lbl_info.setStyleSheet(f"color: {UmbrellaStyle.TEXT_GRAY}; font-size: 12px; italic;")
        leg_layout.addWidget(lbl_info)
        
        self.stack.addWidget(self.tab_legit)

        # -- Visuals / Moves Tab --
        self.tab_visuals = QWidget()
        vis_layout = QVBoxLayout(self.tab_visuals)
        vis_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        lbl_vis = QLabel(self.tr('visuals'))
        lbl_vis.setObjectName("Header")
        vis_layout.addWidget(lbl_vis)
        vis_layout.addSpacing(10)
        
        self.tree_moves = MoveTree()
        self.tree_moves.setHeaderLabels([self.tr('col_num'), self.tr('col_white'), self.tr('col_black')])
        self.tree_moves.setColumnWidth(0, 50)
        vis_layout.addWidget(self.tree_moves)
        
        self.stack.addWidget(self.tab_visuals)
        
        content_layout.addWidget(self.stack)
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_frame)

    def apply_style(self):
        self.setStyleSheet(UmbrellaStyle.STYLESHEET)
        self.toggle_topmost(self.chk_topmost.isChecked())

    def change_language(self, index):
        lang_code = "en" if index == 0 else "ru"
        self.config["language"] = lang_code
        self.tr_data = TRANSLATIONS[lang_code]
        # Reload UI Texts
        self.setWindowTitle(self.tr("title"))
        self.btn_general.setText(f"  {self.tr('general')}")
        self.btn_legit.setText(f"  {self.tr('legit')}")
        self.btn_visuals.setText(f"  {self.tr('visuals')}")
        self.btn_browser.setText(self.tr("browser_open") if self.browser_open else self.tr("open_browser"))
        
        # General
        self.chk_enable.setText(self.tr("enable_bot"))
        self.chk_mouseless.setText(self.tr("invis"))
        self.chk_topmost.setText(self.tr("topmost"))
        self.chk_automatch.setText(self.tr("auto_match"))

        self.chk_autopuzzle.setText(self.tr("auto_puzzle"))
        self.chk_force_solid.setText(self.tr("force_solid"))
        
        # Legit
        self.lbl_acc_val.setText(f"{self.tr('chance')}: {self.slider_acc.value()}%")
        self.lbl_lat_val.setText(f"{self.tr('delay')}: {self.slider_lat.value()/10} sec")
        
        # Visuals
        self.tree_moves.setHeaderLabels([self.tr('col_num'), self.tr('col_white'), self.tr('col_black')])

    def toggle_topmost(self, checked):
        flags = self.windowFlags()
        if checked:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        if not self.isHidden():
            self.show()

    def load_config(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    self.config.update(json.load(f))
            except: pass

    def save_config(self):
        self.config["model"] = self.model_combo.currentText().lower()
        self.config["accuracy"] = self.slider_acc.value()
        self.config["latency"] = self.slider_lat.value() / 10.0
        self.config["mouseless"] = self.chk_mouseless.isChecked()
        self.config["topmost"] = self.chk_topmost.isChecked()
        self.config["auto_match"] = self.chk_automatch.isChecked()

        self.config["auto_puzzle"] = self.chk_autopuzzle.isChecked()
        self.config["force_solid"] = self.chk_force_solid.isChecked()
        self.config["bot_elo"] = self.spin_bot_elo.value()
        self.config["opp_elo"] = self.spin_opp_elo.value()
        try:
            with open("config.json", "w") as f:
                json.dump(self.config, f)
        except: pass

    def open_browser(self):
        if self.browser_open: return
        self.btn_browser.setText(self.tr("opening"))
        self.btn_browser.setEnabled(False)
        QApplication.processEvents()
        try:
            print("[DEBUG] Configuring Chrome config...")
            options = webdriver.ChromeOptions()
            options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option('useAutomationExtension', False)
            
            # Use absolute path based on script location, not CWD
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            # Try a fresh profile to avoid corruption/lock issues from previous crashes
            user_data_dir = os.path.join(project_root, "chrome_profile_v2")
            
            print(f"[DEBUG] User Data Dir: {user_data_dir}")
            options.add_argument(f"--user-data-dir={user_data_dir}")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            # options.add_argument("--disable-gpu") # Commented out to match working test_chrome.py
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--remote-debugging-port=9222") # Added for stability
            options.page_load_strategy = 'eager'
            
            print("[DEBUG] Installing/Finding ChromeDriver...")
            driver_path = ChromeDriverManager().install()
            print(f"[DEBUG] Driver Path: {driver_path}")
            
            if os.path.isdir(driver_path):
                chromedriver_path = os.path.join(driver_path, "chromedriver.exe")
            else:
                chromedriver_path = driver_path
                
            # Enable verbose logging
            service_log_path = os.path.join(project_root, "chromedriver_debug.log")
            service = ChromeService(executable_path=chromedriver_path, service_args=["--verbose"], log_path=service_log_path)
            
            print(f"[DEBUG] Starting Chrome Driver Service (Log: {service_log_path})...")
            
            print("[DEBUG] Starting Chrome Driver Service...")
            self.chrome = webdriver.Chrome(service=service, options=options)
            print("[DEBUG] Chrome Driver Started. Navigating...")
            
            self.chrome.get("https://www.chess.com")
            print("[DEBUG] Navigation successful.")
            
            self.browser_open = True
            self.btn_browser.setText(self.tr("browser_open"))
            # Re-enable Start button interaction if it was failing checks
            self.chk_enable.setChecked(False) 
        except Exception as e:
            print("--- BROWSER LAUNCH ERROR --")
            traceback.print_exc()
            print(f"Browser Error Message: {e}")
            self.btn_browser.setText(self.tr("open_browser"))
            self.btn_browser.setEnabled(True)

    def toggle_bot(self):
        if self.chk_enable.isChecked():
            if not self.start_bot():
                self.chk_enable.setChecked(False)
        else:
            self.stop_bot()

    def start_bot(self):
        if not self.browser_open or not self.chrome:
            QMessageBox.critical(self, "Error", self.tr("err_browser"))
            return False

        self.save_config()
        self.moves_count = 0
        self.tree_moves.clear()
        
        parent_conn, child_conn = multiprocess.Pipe()
        self.pipe = parent_conn
        st_ov_queue = multiprocess.Queue()
        
        self.bot_process = StockfishBot(
            chrome_url=self.chrome.service.service_url,
            chrome_session_id=self.chrome.session_id,
            pipe=child_conn,
            overlay_queue=st_ov_queue,
            enable_manual=False,
            enable_autosolve=self.chk_autopuzzle.isChecked(),
            enable_automatch=self.chk_automatch.isChecked(),
            mouse_latency=self.config["latency"],
            maia_model=self.config["model"],

            accuracy=self.config["accuracy"],
            force_solid=self.config.get("force_solid", True),
            bot_elo=self.config.get("bot_elo", 1500),
            opponent_elo=self.config.get("opp_elo", 1500),
        )
        self.bot_process.start()
        
        self.overlay_process = multiprocess.Process(target=run_overlay, args=(st_ov_queue,))
        self.overlay_process.start()
        self.running = True
        return True

    def stop_bot(self):
        if self.bot_process:
            if self.bot_process.is_alive():
                self.bot_process.terminate()
            self.bot_process = None
        if self.overlay_process:
            self.overlay_process.terminate()
            self.overlay_process = None
        if self.pipe:
            self.pipe.close()
            self.pipe = None
        self.running = False

    def check_state_update(self):
        # Watchdogs
        if self.running and self.bot_process and not self.bot_process.is_alive():
            self.chk_enable.setChecked(False)
            self.stop_bot()
            
        if self.browser_open and self.chrome:
            # More robust check
            try:
                # Check if process is still running
                if self.chrome.service.process.poll() is not None:
                    raise Exception("Process died")
                # Try simple title access, but ignore timeouts/temp connection issues
                import  urllib3.exceptions
                try:
                    _ = self.chrome.title
                except (WebDriverException, urllib3.exceptions.MaxRetryError, urllib3.exceptions.NewConnectionError):
                    # Connection might be flaky temporarily, don't kill immediately
                    # unless it persists (implementation detail: for now we just log/pass)
                    # Ideally we would track failures count.
                    pass
            except Exception as e:
                print(f"Browser Lost: {e}")
                self.browser_open = False
                self.btn_browser.setText(self.tr("open_browser"))
                self.btn_browser.setEnabled(True)
                self.chk_enable.setChecked(False)
                self.stop_bot()

        # Pipe Messages
        if self.pipe and self.pipe.poll():
            try:
                msg = self.pipe.recv()
                if msg.startswith("S_MOVE") or msg.startswith("M_MOVE"):
                    raw = msg.replace("S_MOVE", "").replace("M_MOVE", "")
                    moves = raw.split(",") if "," in raw else [raw]
                    for m in moves:
                        if not m: continue
                        self.update_moves_tree(m)
                elif msg == "RESTART":
                    self.tree_moves.clear()
                    self.moves_count = 0
                    self.pipe.send("DELETE")
            except: pass

    def update_moves_tree(self, move):
        self.moves_count += 1
        full_move_num = (self.moves_count + 1) // 2
        
        # If it's White's move (odd count)
        if self.moves_count % 2 != 0:
            item = QTreeWidgetItem([str(full_move_num), move, ""])
            self.tree_moves.addTopLevelItem(item)
            self.tree_moves.scrollToItem(item)
        else:
            # Black's move, update last item
            count = self.tree_moves.topLevelItemCount()
            if count > 0:
                item = self.tree_moves.topLevelItem(count - 1)
                item.setText(2, move)
                self.tree_moves.scrollToItem(item)

    def closeEvent(self, event):
        self.stop_bot()
        self.save_config()
        if self.chrome:
            try: self.chrome.quit()
            except: pass
        event.accept()

if __name__ == "__main__":
    multiprocess.freeze_support()
    # Fix High DPI
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
