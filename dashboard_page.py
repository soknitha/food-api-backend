from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QMessageBox, QTextBrowser
from PyQt5.QtGui import QFont, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os
import datetime
from services.api_client import APIClient
from services.printer_service import PrinterService

class DashboardWorker(QThread):
    data_loaded = pyqtSignal(list, list, list)
    def run(self):
        orders = APIClient.get_orders()
        users = APIClient.get_users()
        menu = APIClient.get_menu()
        self.data_loaded.emit(orders or [], users or [], menu or [])

class BarChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.data = []
        self.labels = []
        self.setMinimumHeight(250)
        self.setStyleSheet("background-color: white; border-radius: 10px; margin-top: 10px;")
    
    def set_data(self, data, labels):
        self.data = data
        self.labels = labels
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.NoPen)
        painter.drawRect(0, 0, width, height)
        
        if not self.data or max(self.data) == 0:
            painter.setPen(QColor("#7f8c8d"))
            painter.drawText(self.rect(), Qt.AlignCenter, "មិនមានទិន្នន័យចំណូលក្នុងសប្តាហ៍នេះទេ")
            return
            
        max_val = max(self.data)
        margin_x, margin_y = 40, 30
        chart_width = width - 2 * margin_x
        chart_height = height - 2 * margin_y
        bar_width = chart_width / len(self.data) - 15
        
        for i, (val, label) in enumerate(zip(self.data, self.labels)):
            bar_height = (val / max_val) * chart_height
            x = margin_x + i * (bar_width + 15) + 7.5
            y = height - margin_y - bar_height
            painter.setBrush(QColor("#3498db"))
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(bar_height), 5, 5)
            painter.setPen(QColor("#2c3e50"))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(int(x), int(height - margin_y + 20), int(bar_width), 15, Qt.AlignCenter, label)
            painter.drawText(int(x), int(y - 25), int(bar_width), 15, Qt.AlignCenter, f"${val:.1f}")

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📊 ផ្ទាំងសង្ខេបរបាយការណ៍ (Dashboard)")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)
        layout.addSpacing(20)

        # Cards Layout (ផ្ទៃបង្ហាញកាតព័ត៌មាន)
        cards_layout = QHBoxLayout()
        
        self.lbl_orders = self.create_card(cards_layout, "📦 ការកុម្ម៉ង់សរុប", "0", "#3498db")
        self.lbl_revenue = self.create_card(cards_layout, "💰 ចំណូលបានប្រគល់", "$0.00", "#2ecc71")
        self.lbl_users = self.create_card(cards_layout, "👥 អតិថិជនសរុប", "0", "#9b59b6")
        self.lbl_menu = self.create_card(cards_layout, "🍕 មុខម្ហូបសរុប", "0", "#e67e22")

        layout.addLayout(cards_layout)
        
        layout.addSpacing(15)
        chart_title = QLabel("📈 ក្រាហ្វិកចំណូលក្នុងសប្តាហ៍នេះ (៧ ថ្ងៃចុងក្រោយ)")
        chart_title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(chart_title)
        self.chart_widget = BarChartWidget()
        layout.addWidget(self.chart_widget)
        layout.addSpacing(15)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_print = QPushButton("🖨️ បោះពុម្ពរបាយការណ៍ថ្ងៃនេះ")
        btn_print.setStyleSheet("background-color: #9b59b6; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        btn_print.clicked.connect(self.print_report)
        btn_layout.addWidget(btn_print)

        self.btn_refresh = QPushButton("🔄 ធ្វើបច្ចុប្បន្នភាពទិន្នន័យ")
        self.btn_refresh.setStyleSheet("background-color: #34495e; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        self.btn_refresh.clicked.connect(self.load_statistics)
        btn_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(btn_layout)
        layout.addStretch()

        self.load_statistics()

    def create_card(self, layout, title_text, value_text, color):
        card = QFrame()
        card.setStyleSheet(f"background-color: {color}; border-radius: 10px; color: white; padding: 20px;")
        card_layout = QVBoxLayout(card)
        
        title = QLabel(title_text)
        title.setFont(QFont("Arial", 14))
        title.setAlignment(Qt.AlignCenter)
        
        value = QLabel(value_text)
        value.setFont(QFont("Arial", 24, QFont.Bold))
        value.setAlignment(Qt.AlignCenter)
        
        card_layout.addWidget(title)
        card_layout.addWidget(value)
        
        layout.addWidget(card)
        return value

    def load_statistics(self):
        if hasattr(self, 'worker') and self.worker.isRunning(): return
        self.btn_refresh.setText("⏳ កំពុងទាញយកទិន្នន័យ...")
        self.btn_refresh.setEnabled(False)
        self.worker = DashboardWorker()
        self.worker.data_loaded.connect(self.update_ui)
        self.worker.start()

    def update_ui(self, orders, users, menu):
        self.btn_refresh.setText("🔄 ធ្វើបច្ចុប្បន្នភាពទិន្នន័យ")
        self.btn_refresh.setEnabled(True)


        total_orders = len(orders)
        total_users = len(users)
        total_menu = len(menu)
        
        # គណនាចំណូលសរុប (តែការកុម្ម៉ង់ដែល '✅ រួចរាល់ (បានប្រគល់)' ប៉ុណ្ណោះ)
        total_revenue = 0.0
        for order in orders:
            if order.get("status") == "✅ រួចរាល់ (បានប្រគល់)":
                try:
                    val = order.get("total", "$0").replace("$", "")
                    total_revenue += float(val)
                except Exception:
                    pass
        
        # គណនាចំណូល ៧ ថ្ងៃចុងក្រោយសម្រាប់ក្រាហ្វិក
        from datetime import datetime, timedelta
        today = datetime.now()
        days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
        labels = [(today - timedelta(days=i)).strftime("%a") for i in range(6, -1, -1)]
        
        weekly_revenue = {day: 0.0 for day in days}
        for order in orders:
            if order.get("status") == "✅ រួចរាល់ (បានប្រគល់)":
                created_at = order.get("created_at", "")
                if created_at and "T" in created_at:
                    date_part = created_at.split("T")[0]
                    if date_part in weekly_revenue:
                        try:
                            val = float(order.get("total", "$0").replace("$", ""))
                            weekly_revenue[date_part] += val
                        except Exception:
                            pass
                            
        chart_data = [weekly_revenue[day] for day in days]
        khmer_days = {"Mon": "ច័ន្ទ", "Tue": "អង្គារ", "Wed": "ពុធ", "Thu": "ព្រហស្បតិ៍", "Fri": "សុក្រ", "Sat": "សៅរ៍", "Sun": "អាទិត្យ"}
        khmer_labels = [khmer_days.get(lbl, lbl) for lbl in labels]
        self.chart_widget.set_data(chart_data, khmer_labels)

        self.lbl_orders.setText(str(total_orders))
        self.lbl_revenue.setText(f"${total_revenue:.2f}")
        self.lbl_users.setText(str(total_users))
        self.lbl_menu.setText(str(total_menu))

    def print_report(self):
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        total_orders = self.lbl_orders.text()
        total_revenue = self.lbl_revenue.text()
        total_users = self.lbl_users.text()
        
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; text-align: center; background-color: white;">
            <h2 style="margin-bottom: 5px;">របាយការណ៍លក់ប្រចាំថ្ងៃ</h2>
            <p style="color: #7f8c8d; margin-top: 0;">កាលបរិច្ឆេទ៖ {date_str}</p>
            <hr style="border: 1px dashed #ccc;">
            <h3 style="text-align: left;">📦 ការកុម្ម៉ង់សរុប៖ <span style="float: right;">{total_orders}</span></h3>
            <h3 style="text-align: left;">👥 អតិថិជនសរុប៖ <span style="float: right;">{total_users}</span></h3>
            <hr style="border: 1px dashed #ccc;">
            <h2 style="text-align: left; color: #27ae60;">💰 ចំណូលសរុប៖ <span style="float: right;">{total_revenue}</span></h2>
            <hr style="border: 1px dashed #ccc;">
            <p style="font-size: 12px; color: #95a5a6;">FoodAdmin System</p>
        </div>
        """
        
        browser = QTextBrowser()
        browser.setHtml(html)
        browser.setFixedSize(400, 400)
        
        temp_path = os.path.abspath("temp_report.png")
        pixmap = browser.grab()
        pixmap.save(temp_path, "PNG")
        
        success = PrinterService.auto_print_receipt(temp_path)
        if success:
            QMessageBox.information(self, "ជោគជ័យ", "បានបញ្ជូនរបាយការណ៍ទៅកាន់ម៉ាស៊ីនព្រីន POS រួចរាល់!")
        else:
            QMessageBox.critical(self, "កំហុស", "មិនអាចភ្ជាប់ទៅម៉ាស៊ីនព្រីនបានទេ!\nសូមពិនិត្យមើលការកំណត់ IP ។")