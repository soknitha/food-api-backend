import os
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTabWidget
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt

from views.dashboard_page import DashboardPage
from views.orders_page import OrdersPage
from views.menu_page import MenuPage
from views.users_page import UsersPage
from views.crm_page import CRMPage
from views.settings_page import SettingsPage

class AdminDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_lang = "KM"
        self.setWindowTitle("ប្រព័ន្ធគ្រប់គ្រងហាង | FoodAdmin")
        self.resize(1100, 750)
        self.init_ui()
        
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ---------------- ផ្នែកកំណត់ភាសាប្រព័ន្ធ (Language Switcher) ---------------- #
        top_bar = QHBoxLayout()
        self.lbl_lang = QLabel("🌐 ភាសាប្រព័ន្ធ (System Language):")
        self.lbl_lang.setFont(QFont("Arial", 11, QFont.Bold))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["KM - ភាសាខ្មែរ", "ZH - 中文", "EN - English"])
        self.combo_lang.setFont(QFont("Arial", 11))
        self.combo_lang.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        self.combo_lang.currentIndexChanged.connect(self.change_language)
        
        top_bar.addWidget(self.lbl_lang)
        top_bar.addWidget(self.combo_lang)
        top_bar.addStretch()
        layout.addLayout(top_bar)
        
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Arial", 11, QFont.Bold))
        self.tabs.setStyleSheet("""
            QTabBar::tab { background: #ecf0f1; color: #2c3e50; padding: 12px 20px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px; }
            QTabBar::tab:selected { background: #3498db; color: white; }
            QTabWidget::pane { border-top: 2px solid #3498db; }
        """)
        
        self.tabs.addTab(DashboardPage(), "📊 របាយការណ៍")
        self.tabs.addTab(OrdersPage(), "🛒 ការកុម្ម៉ង់ (Orders)")
        self.tabs.addTab(MenuPage(), "🍕 មុខម្ហូប (Menu)")
        self.tabs.addTab(UsersPage(), "👥 អតិថិជន (Users)")
        self.tabs.addTab(CRMPage(), "💬 ទំនាក់ទំនង (CRM)")
        
        if os.environ.get("CURRENT_USER", "admin") == "admin":
            self.tabs.addTab(SettingsPage(), "⚙️ ការកំណត់ (Settings)")
            
        layout.addWidget(self.tabs)
        self.update_ui_texts()

    def change_language(self, index):
        langs = ["KM", "ZH", "EN"]
        self.current_lang = langs[index]
        self.update_ui_texts()
        
    def update_ui_texts(self):
        texts = {
            "KM": {
                "win": "ប្រព័ន្ធគ្រប់គ្រងហាង | FoodAdmin", "lang": "🌐 ភាសាប្រព័ន្ធ (Language):",
                "t0": "📊 របាយការណ៍", "t1": "🛒 ការកុម្ម៉ង់", "t2": "🍕 មុខម្ហូប", "t3": "👥 អតិថិជន", "t4": "💬 ទំនាក់ទំនង", "t5": "⚙️ ការកំណត់"
            },
            "ZH": {
                "win": "高级管理系统 | FoodAdmin", "lang": "🌐 系统语言 (Language):",
                "t0": "📊 数据报表", "t1": "🛒 订单管理", "t2": "🍕 菜品管理", "t3": "👥 客户管理", "t4": "💬 客服联系", "t5": "⚙️ 系统设置"
            },
            "EN": {
                "win": "Store Management System | FoodAdmin", "lang": "🌐 System Language:",
                "t0": "📊 Dashboard", "t1": "🛒 Orders", "t2": "🍕 Menu", "t3": "👥 Customers", "t4": "💬 CRM", "t5": "⚙️ Settings"
            }
        }
        t = texts[self.current_lang]
        self.setWindowTitle(t["win"])
        self.lbl_lang.setText(t["lang"])
        
        self.tabs.setTabText(0, t["t0"])
        self.tabs.setTabText(1, t["t1"])
        self.tabs.setTabText(2, t["t2"])
        self.tabs.setTabText(3, t["t3"])
        self.tabs.setTabText(4, t["t4"])
        if self.tabs.count() > 5:
            self.tabs.setTabText(5, t["t5"])