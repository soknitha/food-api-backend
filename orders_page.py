from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout, QComboBox, QMessageBox, QSystemTrayIcon, QStyle, QDialog, QTextBrowser, QFileDialog, QLineEdit, QDateEdit
from PyQt5.QtCore import Qt, QTimer, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QImage, QPainter
from PyQt5.QtMultimedia import QSound
from services.api_client import APIClient
from services.printer_service import PrinterService
import webbrowser
import os
import re
import datetime

# ផ្ទាំងលោតសម្រាប់បង្ហាញវិក្កយបត្រដែលមានមុខងារ Export និង Print POS
class ReceiptDialog(QDialog):
    def __init__(self, order_id, order_time, customer, items, total, is_paid=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"វិក្កយបត្រ - {order_id}")
        self.resize(520, 750) # ពង្រីកទំហំផ្ទាំងឱ្យធំទូលាយស្ទើរស្មើក្រដាស
        self.setStyleSheet("background-color: white;")
        layout = QVBoxLayout(self)

        self.order_id = order_id
        self.customer = customer
        self.items = items
        self.total = total
        self.is_paid = is_paid
        
        # ទាញយកមុខម្ហូប ដើម្បីស្វែងរកតម្លៃរាយ
        menu_data = APIClient.get_menu()
        self.menu_prices = {m['name'].strip(): m.get('price', 0.0) for m in menu_data}
        
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("📅 កាលបរិច្ឆេទ/ម៉ោង៖"))
        current_datetime_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.date_input = QLineEdit(current_datetime_str)
        self.date_input.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 3px; font-weight: bold;")
        self.date_input.textChanged.connect(self.update_receipt)
        date_layout.addWidget(self.date_input)
        layout.addLayout(date_layout)

        self.text_browser = QTextBrowser()
        self.text_browser.setStyleSheet("border: 1px solid #eee; border-radius: 5px;")
        layout.addWidget(self.text_browser)

        btn_layout = QHBoxLayout()
        
        btn_export = QPushButton("📥 ទាញយក (PNG)")
        btn_export.setStyleSheet("background-color: #3498db; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        btn_export.clicked.connect(self.export_png)
        
        btn_pos = QPushButton("🖨️ ព្រីន POS")
        btn_pos.setStyleSheet("background-color: #9b59b6; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        btn_pos.clicked.connect(self.print_pos)
        
        btn_close = QPushButton("❌ បិទ")
        btn_close.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        btn_close.clicked.connect(self.accept)

        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(btn_pos)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        self.update_receipt()
        
    def update_receipt(self):
        order_time = self.date_input.text()
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logo.png')).replace('\\', '/')
        import json
        if os.path.exists("credentials.json"):
            try:
                with open("credentials.json", "r") as f:
                    c_data = json.load(f)
                    if c_data.get("logo_path") and os.path.exists(c_data.get("logo_path")):
                        logo_path = os.path.abspath(c_data.get("logo_path")).replace('\\', '/')
            except Exception:
                pass
        
        raw_items = self.items.replace('\n', ',').split(',')
        table_rows = ""
        discount_row = ""
        index = 1
        
        for item_str in raw_items:
            item_str = item_str.strip()
            if not item_str:
                continue
            
            if "🎁" in item_str or "ប្រើប្រាស់" in item_str:
                discount_row = item_str
                continue
                
            parts = item_str.rsplit('x', 1)
            if len(parts) == 2:
                name = parts[0].strip()
                qty_str = parts[1].strip()
                
                # ស្វែងរកតម្លៃរាយដែលបង្កប់មកជាមួយ (ឧ. "1 ($1.50)") សម្រាប់ថ្លៃដឹកជញ្ជូន
                price_match = re.search(r'\(\$([\d\.]+)\)', qty_str)
                if price_match:
                    unit_price = float(price_match.group(1))
                    qty_str_clean = re.sub(r'\(\$([\d\.]+)\)', '', qty_str).strip()
                    try:
                        qty = int(qty_str_clean) if qty_str_clean else 1
                    except Exception:
                        qty = 1
                else:
                    try:
                        qty = int(qty_str)
                    except Exception:
                        qty = 1
                    name_clean = re.sub(r'^[០១២៣៤៥៦៧៨៩0-9]+\.\s*', '', name)
                    unit_price = self.menu_prices.get(name_clean, 0.0)
            else:
                name = item_str
                qty = 1
                name_clean = re.sub(r'^[០១២៣៤៥៦៧៨៩0-9]+\.\s*', '', name)
                unit_price = self.menu_prices.get(name_clean, 0.0)
                
            total_price = unit_price * qty
            
            table_rows += f"""
            <tr>
                <td style="border: 1px solid #333; padding: 8px; text-align: center; white-space: nowrap;">{index}</td>
                <td style="border: 1px solid #333; padding: 8px;">{name}</td>
                <td style="border: 1px solid #333; padding: 8px; text-align: center; white-space: nowrap;">{qty}</td>
                <td style="border: 1px solid #333; padding: 8px; text-align: right; white-space: nowrap;">${unit_price:.2f}</td>
                <td style="border: 1px solid #333; padding: 8px; text-align: right; white-space: nowrap;">${total_price:.2f}</td>
            </tr>
            """
            index += 1
            
        discount_html = ""
        if discount_row:
            discount_html = f"""
            <tr>
                <td colspan="4" style="border: 1px solid #333; padding: 8px; text-align: right; font-weight: bold;">កូប៉ុង / Discount:</td>
                <td style="border: 1px solid #333; padding: 8px; text-align: right; color: #e74c3c;">{discount_row}</td>
            </tr>
            """
            
        paid_stamp = ""
        if getattr(self, "is_paid", False):
            paid_stamp = """
            <div style="text-align: center; color: #27ae60; font-size: 16px; font-weight: bold; border: 2px solid #27ae60; margin: 10px 80px; padding: 5px; border-radius: 5px;">
                ✅ PAID / បានទូទាត់ប្រាក់
            </div>
            """
            
        receipt_html = f"""
        <div style="font-family: 'Khmer OS Battambang', Arial, sans-serif; padding: 2px;">
            <div style="text-align: center;">
                <img src="file:///{logo_path}" width="100" />
                <h2 style="margin: 10px 0 5px 0;">小月小吃</h2>
            </div>
            {paid_stamp}
            <hr style="border: 1px dashed #ccc;">
            <p style="margin: 2px 0;"><b>លេខវិក្កយបត្រ៖</b> {self.order_id}</p>
            <p style="margin: 2px 0;"><b>កាលបរិច្ឆេទ៖</b> {order_time}</p>
            <p style="margin: 2px 0;"><b>អតិថិជន៖</b> {self.customer}</p>
            <hr style="border: 1px dashed #ccc;">
            
            <table style="width: 100%; margin: 0; border-collapse: collapse; font-size: 15px; margin-bottom: 15px;">
                <thead style="background-color: #f8f9fa;">
                    <tr>
                        <th colspan="5" style="border: 1px solid #333; padding: 10px; text-align: center; font-size: 16px; background-color: #e9ecef;">មុខម្ហូបដែលបានកុម្ម៉ង់</th>
                    </tr>
                    <tr>
                        <th style="border: 1px solid #333; padding: 8px; width: 1%; text-align: center; white-space: nowrap;">ល.រ</th>
                        <th style="border: 1px solid #333; padding: 8px; width: auto; text-align: left;">ឈ្មោះមុខម្ហូប</th>
                        <th style="border: 1px solid #333; padding: 8px; width: 1%; text-align: center; white-space: nowrap;">ចំនួន</th>
                        <th style="border: 1px solid #333; padding: 8px; width: 1%; text-align: right; white-space: nowrap;">តម្លៃរាយ</th>
                        <th style="border: 1px solid #333; padding: 8px; width: 1%; text-align: right; white-space: nowrap;">តម្លៃសរុប</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                    {discount_html}
                    <tr>
                        <td colspan="4" style="border: 1px solid #333; padding: 8px; text-align: right; font-weight: bold; font-size: 16px;">តម្លៃទូទាត់សរុប:</td>
                        <td style="border: 1px solid #333; padding: 8px; text-align: right; font-weight: bold; color: #27ae60; font-size: 16px;">{self.total}</td>
                    </tr>
                </tbody>
            </table>
            
            <div style="text-align: center; color: #7f8c8d; font-size: 13px; margin-top: 15px;">
                <p>🙏 អរគុណដែលបានគាំទ្រ! 🙏</p>
                <hr style="border: 1px dashed #ccc;">
                <p style="margin: 5px 0; color: #333;"><b>អាសយដ្ឋាន៖</b> ផ្ទះលេខ 346, ផ្លូវ 2004</p>
                <p style="margin: 5px 0; color: #333;"><b>ទូរសព្ទ៖</b> 086 599 789 / 012 525 286</p>
            </div>
        </div>
        """
        self.text_browser.setHtml(receipt_html)

    def get_receipt_image(self):
        doc = self.text_browser.document()
        doc.setTextWidth(self.text_browser.viewport().width())
        size = doc.size().toSize()
        size.setHeight(size.height() + 15)
        
        image = QImage(size, QImage.Format_ARGB32)
        image.fill(Qt.white)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        doc.drawContents(painter)
        
        if getattr(self, "is_paid", False):
            painter.save()
            painter.translate(int(image.width() / 2), int(image.height() / 2))
            painter.rotate(-45)
            font = QFont("Arial", 70, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QColor(46, 204, 113, 50)) # Watermark ព្រាលៗ (Transparent green)
            text_rect = painter.fontMetrics().boundingRect("PAID")
            painter.drawText(int(-text_rect.width() / 2), int(text_rect.height() / 2), "PAID")
            painter.restore()
            
        painter.end()
        return image

    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "រក្សាទុកវិក្កយបត្រជារូបភាព", f"Receipt_{self.order_id}.png", "PNG Files (*.png)")
        if path:
            image = self.get_receipt_image()
            image.save(path, "PNG")
            QMessageBox.information(self, "ជោគជ័យ", f"វិក្កយបត្រត្រូវបានរក្សាទុករួចរាល់នៅ៖\n{path}")

    def print_pos(self):
        temp_path = os.path.abspath("temp_receipt.png")
        image = self.get_receipt_image()
        image.save(temp_path, "PNG")
        
        success = PrinterService.auto_print_receipt(temp_path)
        if success:
            QMessageBox.information(self, "ជោគជ័យ", "បានបញ្ជូនទៅម៉ាស៊ីនព្រីន POS រួចរាល់!")
        else:
            QMessageBox.critical(self, "កំហុស", "មិនអាចភ្ជាប់ទៅម៉ាស៊ីនព្រីនបានទេ!\nសូមពិនិត្យមើលផ្ទាំង 'ការកំណត់' ដើម្បីដាក់ IP ម៉ាស៊ីនព្រីន។")

class OrdersWorker(QThread):
    data_loaded = pyqtSignal(list)
    def run(self):
        data = APIClient.get_orders()
        self.data_loaded.emit(data or [])

# ថ្នាក់សម្រាប់បង្ហាញទំព័រគ្រប់គ្រងការកុម្ម៉ង់ (Orders Page)
class OrdersPage(QWidget):
    def __init__(self):
        super().__init__()
        self.last_order_count = -1
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("បញ្ជីកុម្ម៉ង់ម្ហូបថ្ងៃនេះ (Live Orders)")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet("color: #333;")
        layout.addWidget(title)

        # ---------------- ផ្ទាំងបង្ហាញចំនួនសរុបតាមស្ថានភាព ---------------- #
        summary_layout = QHBoxLayout()
        self.lbl_count_all = QLabel("សរុប: 0")
        self.lbl_count_all.setStyleSheet("padding: 5px 10px; background-color: #ecf0f1; border-radius: 5px; font-weight: bold; color: #2c3e50;")
        self.lbl_count_new = QLabel("🆕 ថ្មី: 0")
        self.lbl_count_new.setStyleSheet("padding: 5px 10px; background-color: white; border: 1px solid #ccc; border-radius: 5px; font-weight: bold;")
        self.lbl_count_cooking = QLabel("🍳 កំពុងចម្អិន: 0")
        self.lbl_count_cooking.setStyleSheet("padding: 5px 10px; background-color: #fff3cd; border-radius: 5px; font-weight: bold;")
        self.lbl_count_delivering = QLabel("🛵 ដឹកជញ្ជូន: 0")
        self.lbl_count_delivering.setStyleSheet("padding: 5px 10px; background-color: #d1ecf1; border-radius: 5px; font-weight: bold;")
        self.lbl_count_completed = QLabel("✅ រួចរាល់: 0")
        self.lbl_count_completed.setStyleSheet("padding: 5px 10px; background-color: #d4edda; border-radius: 5px; font-weight: bold; color: #155724;")
        self.lbl_count_cancelled = QLabel("❌ លុបចោល: 0")
        self.lbl_count_cancelled.setStyleSheet("padding: 5px 10px; background-color: #f8d7da; border-radius: 5px; font-weight: bold; color: #721c24;")
        
        for lbl in [self.lbl_count_all, self.lbl_count_new, self.lbl_count_cooking, self.lbl_count_delivering, self.lbl_count_completed, self.lbl_count_cancelled]:
            summary_layout.addWidget(lbl)
            
        summary_layout.addStretch()
        layout.addLayout(summary_layout)
        layout.addSpacing(10)

        # ---------------- ប្រអប់ស្វែងរក (Search) ---------------- #
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 ស្វែងរក:")
        search_label.setFont(QFont("Arial", 12))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("វាយលេខកូដវិក្កយបត្រ ឬឈ្មោះអតិថិជន ដើម្បីស្វែងរក...")
        self.search_input.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px;")
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        
        # ---------------- ប្រអប់រើសកាលបរិច្ឆេទ (Date Picker) ---------------- #
        date_label = QLabel("📅 ថ្ងៃទី:")
        date_label.setFont(QFont("Arial", 12))
        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True) # អនុញ្ញាតឱ្យចុចលោតប្រតិទិន
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px;")
        self.date_filter.dateChanged.connect(self.filter_table)
        
        btn_clear_date = QPushButton("❌ បង្ហាញទាំងអស់")
        btn_clear_date.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        btn_clear_date.clicked.connect(self.clear_date_filter)
        
        search_layout.addWidget(date_label)
        search_layout.addWidget(self.date_filter)
        search_layout.addWidget(btn_clear_date)
        layout.addLayout(search_layout)

        # បង្កើតតារាង (Table)
        self.table = QTableWidget(0, 75)
        self.table.setHorizontalHeaderLabels(["លេខកូដ", "ម៉ោងកុម្ម៉ង់", "ឈ្មោះអតិថិជន", "មុខម្ហូប", "តម្លៃសរុប", "ស្ថានភាព", "បង់ប្រាក់"])
        
        # កំណត់ទំហំជួរឈរ (Columns) នីមួយៗដោយផ្ទាល់ (គិតជា Pixels)
        self.table.setColumnWidth(0, 90)   # ជួរទី 0: លេខកូដ
        self.table.setColumnWidth(1, 150)  # ជួរទី 1: ម៉ោងកុម្ម៉ង់
        self.table.setColumnWidth(2, 140)  # ជួរទី 2: ឈ្មោះអតិថិជន
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch) # ជួរទី 3: មុខម្ហូប (កំណត់ឱ្យលាតពេញទំហំដែលនៅសល់)
        self.table.setColumnWidth(4, 90)   # ជួរទី 4: តម្លៃសរុប
        self.table.setColumnWidth(5, 140)  # ជួរទី 5: ស្ថានភាព
        self.table.setColumnWidth(6, 120)  # ជួរទី 6: បង់ប្រាក់
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: white; border-radius: 8px; }
            QHeaderView::section { background-color: #3498db; color: white; padding: 5px; font-weight: bold; }
        """)
        layout.addWidget(self.table)

        # ---------------- ផ្ទាំងបញ្ជាខាងក្រោមតារាង ---------------- #
        ctrl_layout = QHBoxLayout()
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["ថ្មី (រង់ចាំការបញ្ជាក់)", "កំពុងចម្អិន", "កំពុងដឹកជញ្ជូន", "✅ រួចរាល់ (បានប្រគល់)", "❌ លុបចោលការកុម្ម៉ង់"])
        self.status_combo.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        
        btn_update = QPushButton("🚀 ប្តូរស្ថានភាព និងលោតសារប្រាប់អតិថិជន")
        btn_update.setStyleSheet("background-color: #f39c12; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        btn_update.clicked.connect(self.update_status)
        
        btn_print = QPushButton("🖨️ បោះពុម្ពវិក្កយបត្រ")
        btn_print.setStyleSheet("background-color: #9b59b6; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        btn_print.clicked.connect(self.print_receipt)
        
        btn_view_receipt = QPushButton("🖼️ មើលរូបបង់ប្រាក់")
        btn_view_receipt.setStyleSheet("background-color: #34495e; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        btn_view_receipt.clicked.connect(self.view_receipt_image)
        
        self.btn_refresh = QPushButton("🔄 ធ្វើបច្ចុប្បន្នភាព")
        self.btn_refresh.setStyleSheet("background-color: #2ecc71; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        self.btn_refresh.clicked.connect(self.load_orders)
        
        ctrl_layout.addWidget(QLabel("ប្តូរស្ថានភាព៖"))
        ctrl_layout.addWidget(self.status_combo)
        ctrl_layout.addWidget(btn_update)
        ctrl_layout.addWidget(btn_print)
        ctrl_layout.addWidget(btn_view_receipt)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(ctrl_layout)

        # រៀបចំប្រព័ន្ធសារលោត Notification (System Tray)
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        self.tray_icon.show()

        # ហៅទិន្នន័យមកបង្ហាញពេលបើកទំព័រនេះដំបូង
        self.load_orders()
        
        # បង្កើត Timer សម្រាប់ទាញយកទិន្នន័យថ្មីដោយស្វ័យប្រវត្តិ (រៀងរាល់ ១៥ វិនាទី)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_orders)
        self.timer.start(15000)

    def clear_date_filter(self):
        self.search_input.clear()
        # កំណត់ Flag មួយដើម្បីកុំអោយវា Filter តាមថ្ងៃពេលចុច "បង្ហាញទាំងអស់"
        self.date_filter.blockSignals(True) 
        self.filter_table(clear_all=True)
        self.date_filter.blockSignals(False)

    def filter_table(self, clear_all=False):
        search_text = self.search_input.text().lower()
        filter_date = self.date_filter.date().toString("yyyy-MM-dd")
        
        count_all = count_new = count_cooking = count_delivering = count_completed = count_cancelled = 0
        
        for row in range(self.table.rowCount()):
            item_id = self.table.item(row, 0)
            item_date = self.table.item(row, 1)
            item_customer = self.table.item(row, 2)
            item_status = self.table.item(row, 5)
            
            if item_id and item_customer and item_date and item_status:
                match_text = search_text in item_id.text().lower() or search_text in item_customer.text().lower()
                match_date = filter_date in item_date.text()
                
                if clear_all or (match_text and match_date):
                    self.table.setRowHidden(row, False)
                    
                    count_all += 1
                    st = item_status.text()
                    if "ថ្មី" in st:
                        count_new += 1
                    elif "ចម្អិន" in st:
                        count_cooking += 1
                    elif "ដឹកជញ្ជូន" in st:
                        count_delivering += 1
                    elif "រួចរាល់" in st:
                        count_completed += 1
                    elif "លុបចោល" in st:
                        count_cancelled += 1
                else:
                    self.table.setRowHidden(row, True)
                    
        if hasattr(self, 'lbl_count_all'):
            self.lbl_count_all.setText(f"សរុប: {count_all}")
            self.lbl_count_new.setText(f"🆕 ថ្មី: {count_new}")
            self.lbl_count_cooking.setText(f"🍳 កំពុងចម្អិន: {count_cooking}")
            self.lbl_count_delivering.setText(f"🛵 ដឹកជញ្ជូន: {count_delivering}")
            self.lbl_count_completed.setText(f"✅ រួចរាល់: {count_completed}")
            self.lbl_count_cancelled.setText(f"❌ លុបចោល: {count_cancelled}")

    def update_status(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "ជូនដំណឹង", "សូមចុចជ្រើសរើសការកុម្ម៉ង់ណាមួយក្នុងតារាងជាមុនសិន!")
            return
        
        order_id = self.table.item(current_row, 0).text()
        new_status = self.status_combo.currentText()
        
        if APIClient.update_order_status(order_id, new_status):
            QMessageBox.information(self, "ជោគជ័យ", f"បានប្តូរស្ថានភាពវិក្កយបត្រ {order_id} និងផ្ញើសារប្រាប់អតិថិជនរួចរាល់!")
            self.load_orders()
        else:
            QMessageBox.critical(self, "កំហុស", "មានបញ្ហាក្នុងការប្តូរស្ថានភាព!")

    def print_receipt(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "ជូនដំណឹង", "សូមចុចជ្រើសរើសការកុម្ម៉ង់ណាមួយក្នុងតារាងជាមុនសិន ដើម្បីបោះពុម្ព!")
            return
        
        order_id = self.table.item(current_row, 0).text()
        order_time = self.table.item(current_row, 1).text()
        customer = self.table.item(current_row, 2).text()
        items = self.table.item(current_row, 3).text()
        total = self.table.item(current_row, 4).text()
        status = self.table.item(current_row, 5).text()
        receipt_col = self.table.item(current_row, 6).text()
        
        is_paid = "មានរូបភាព" in receipt_col or "រួចរាល់" in status
        dialog = ReceiptDialog(order_id, order_time, customer, items, total, is_paid, self)
        dialog.exec() # ប្រើប្រាស់ exec() ស្តង់ដារថ្មី

    def view_receipt_image(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "ជូនដំណឹង", "សូមចុចជ្រើសរើសការកុម្ម៉ង់ណាមួយក្នុងតារាងជាមុនសិន!")
            return
            
        item = self.table.item(current_row, 6)
        url = item.data(Qt.UserRole)
        if url:
            webbrowser.open(url) # បើករូបភាពមើលក្នុង Browser ដោយស្វ័យប្រវត្តិ
        else:
            QMessageBox.information(self, "គ្មានរូបភាព", "អតិថិជនមិនទាន់បានផ្ញើរូបភាពបង់ប្រាក់សម្រាប់ការកុម្ម៉ង់នេះទេ។")

    def load_orders(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            return
        self.btn_refresh.setText("⏳ កំពុងទាញយក...")
        self.worker = OrdersWorker()
        self.worker.data_loaded.connect(self.process_orders_data)
        self.worker.start()
        
    def process_orders_data(self, data):
        self.btn_refresh.setText("🔄 ធ្វើបច្ចុប្បន្នភាព")
        current_count = len(data)
        # លោតសំឡេងបើមានការកុម្ម៉ង់ថ្មី (លើកលែងតែពេលទើបបើកកម្មវិធីដំបូង)
        if self.last_order_count != -1 and current_count > self.last_order_count:
            try:
                # ស្វែងរក File សំឡេងឈ្មោះ notification.wav នៅក្នុង Folder គម្រោង
                sound_path = os.path.join(os.path.dirname(__file__), '..', 'notification.wav')
                    
                # ឆែកមើលក្នុង credentials.json បើ Admin បានដូរ File សំឡេងថ្មី
                import json
                if os.path.exists("credentials.json"):
                    with open("credentials.json", "r") as f:
                        s_data = json.load(f)
                        if s_data.get("sound_path") and os.path.exists(s_data.get("sound_path")):
                            sound_path = s_data.get("sound_path")

                if os.path.exists(sound_path):
                    QSound.play(sound_path)
                
                # បង្ហាញសារលោត (Notification Popup) នៅជ្រុងអេក្រង់
                self.tray_icon.showMessage(
                    "🔔 មានការកុម្ម៉ង់ថ្មី!",
                    "អតិថិជនទើបតែធ្វើការបញ្ជាទិញម្ហូបថ្មី។ សូមពិនិត្យមើលបញ្ជីការកុម្ម៉ង់ឥឡូវនេះ!",
                    QSystemTrayIcon.Information,
                    5000 # បង្ហាញរយៈពេល ៥ វិនាទី
                )
                
                # ទាញយកការកុម្ម៉ង់ថ្មីបំផុតៗដើម្បីព្រីន
                new_orders = data[self.last_order_count:]
                for new_order in new_orders:
                    PrinterService.auto_print_receipt(
                        new_order.get("id", ""),
                        new_order.get("customer", ""),
                        new_order.get("items", ""),
                        new_order.get("total", "")
                    )
            except Exception:
                pass
        self.last_order_count = current_count
        
        self.table.setRowCount(len(data))
        for row, order in enumerate(data):
            item_id = QTableWidgetItem(order["id"])
            self.table.setItem(row, 0, item_id)
            
            # ទាញយកម៉ោងកុម្ម៉ង់ និងកាត់យកត្រឹមវិនាទី
            created_at = order.get("created_at", "")
            if created_at and "T" in created_at:
                created_at = created_at.split(".")[0].replace("T", " ")
            item_date = QTableWidgetItem(created_at)
            self.table.setItem(row, 1, item_date)
            item_customer = QTableWidgetItem(order["customer"])
            self.table.setItem(row, 2, item_customer)
            
            # រៀបចំទម្រង់មុខម្ហូបឱ្យមានលេខរៀង និងចុះបន្ទាត់ (បំប្លែងទៅជាលេខខ្មែរ)
            raw_items = order.get("items", "")
            item_list = raw_items.split(",") if raw_items else []
            formatted_items = []
            khmer_digits = str.maketrans('0123456789', '០១២៣៤៥៦៧៨៩')
            idx_num = 1
            for item in item_list:
                item_str = item.strip()
                if not item_str: continue
                if "🎁" in item_str or "🛵" in item_str:
                    formatted_items.append(f"  {item_str}")
                else:
                    k_num = str(idx_num).translate(khmer_digits)
                    formatted_items.append(f"{k_num}. {item_str}")
                    idx_num += 1
            
            item_items = QTableWidgetItem("\n".join(formatted_items))
            self.table.setItem(row, 3, item_items)
            item_total = QTableWidgetItem(order["total"])
            self.table.setItem(row, 4, item_total)
            item_status = QTableWidgetItem(order["status"])
            self.table.setItem(row, 5, item_status)
            
            # រៀបចំផ្នែកបង្ហាញរូបភាពវិក្កយបត្រ
            receipt_url = order.get("receipt_url", "")
            receipt_item = QTableWidgetItem("✅ មានរូបភាព" if receipt_url else "❌ គ្មាន")
            receipt_item.setForeground(QColor("#2ecc71" if receipt_url else "#e74c3c"))
            receipt_item.setData(Qt.UserRole, receipt_url) # លាក់ URL រូបភាពទុកក្នុង Cell
            self.table.setItem(row, 6, receipt_item)
            
            # ចាក់ពណ៌ផ្ទៃខាងក្រោយតាមស្ថានភាព
            status = order.get("status", "")
            bg_color = QColor("white") # ពណ៌ដើម
            if status == "✅ រួចរាល់ (បានប្រគល់)":
                bg_color = QColor("#d4edda") # បៃតងខ្ចី
            elif status == "❌ លុបចោលការកុម្ម៉ង់":
                bg_color = QColor("#f8d7da") # ក្រហមខ្ចី
            elif status == "កំពុងចម្អិន":
                bg_color = QColor("#fff3cd") # លឿងខ្ចី
            elif status == "កំពុងដឹកជញ្ជូន":
                bg_color = QColor("#d1ecf1") # ខៀវខ្ចី
                
            item_id.setBackground(bg_color)
            item_date.setBackground(bg_color)
            item_customer.setBackground(bg_color)
            item_items.setBackground(bg_color)
            item_total.setBackground(bg_color)
            item_status.setBackground(bg_color)
            
        # ធ្វើឱ្យជួរ (Rows) រីកធំតាមចំនួនបន្ទាត់អក្សរដោយស្វ័យប្រវត្តិដើម្បីងាយស្រួលមើល
        self.table.resizeRowsToContents()
        
        # អនុវត្តការស្វែងរកឡើងវិញ បន្ទាប់ពីទិន្នន័យត្រូវបានធ្វើបច្ចុប្បន្នភាពជារៀងរាល់ ១៥ វិនាទី
        self.filter_table()
