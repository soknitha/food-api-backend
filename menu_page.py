from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLineEdit, QMessageBox, QApplication, QFileDialog, QGroupBox, QGridLayout
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
import os
import requests
import urllib3
from config import API_BASE_URL
from services.api_client import APIClient

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # បិទសារព្រមានការរំលង SSL

class MenuWorker(QThread):
    data_loaded = pyqtSignal(list)
    def run(self):
        data = APIClient.get_menu()
        self.data_loaded.emit(data or [])

# Memory សម្រាប់ផ្ទុករូបភាពដែលទាញរួចកុំឱ្យវាទាញចុះទាញឡើងនាំឱ្យយឺត
IMAGE_CACHE = {}

class ImageDownloader(QThread):
    image_loaded = pyqtSignal(int, bytes)
    def __init__(self, item_id, url):
        super().__init__()
        self.item_id, self.url = item_id, url
    def run(self):
        if self.url in IMAGE_CACHE:
            self.image_loaded.emit(self.item_id, IMAGE_CACHE[self.url])
            return
        try: 
            res = requests.get(self.url, timeout=10, verify=False).content
            IMAGE_CACHE[self.url] = res
        except Exception:
            res = b""
        self.image_loaded.emit(self.item_id, res)

# ---------------- តារាងដែលអាចអូសទម្លាក់បាន (Drag & Drop Table) ---------------- #
class MenuTableWidget(QTableWidget):
    order_changed = pyqtSignal(list)

    def __init__(self, rows, cols, parent=None):
        super().__init__(rows, cols, parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setDragDropMode(QTableWidget.InternalMove)

    def dropEvent(self, event):
        super().dropEvent(event)
        new_order = []
        for row in range(self.rowCount()):
            item_id_widget = self.item(row, 0)
            if item_id_widget:
                try: new_order.append({"id": int(item_id_widget.text()), "sort_order": row})
                except ValueError: pass
        self.order_changed.emit(new_order)

class MenuPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.editing_item_id = None
        self.editing_image_url = ""

        title = QLabel("🍕 គ្រប់គ្រងមុខម្ហូប (Menu Management)")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)

        # ---------------- Form សម្រាប់បន្ថែមមុខម្ហូបទំនើប (3 ភាសា & Upload) ---------------- #
        self.group_box = QGroupBox("🍽️ បន្ថែមមុខម្ហូបថ្មី (Add New Menu Item)")
        self.group_box.setFont(QFont("Arial", 12, QFont.Bold))
        self.group_box.setStyleSheet("QGroupBox { border: 2px solid #3498db; border-radius: 8px; margin-top: 10px; padding-top: 15px; } QGroupBox::title { color: #3498db; }")
        
        grid = QGridLayout()
        
        self.txt_name_km = QLineEdit()
        self.txt_name_km.setPlaceholderText("ឈ្មោះខ្មែរ (ឧ. ភីហ្សា)")
        self.txt_name_km.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.txt_name_zh = QLineEdit()
        self.txt_name_zh.setPlaceholderText("ឈ្មោះចិន (ឧ. 比萨)")
        self.txt_name_zh.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.txt_name_en = QLineEdit()
        self.txt_name_en.setPlaceholderText("ឈ្មោះអង់គ្លេស (ឧ. Pizza)")
        self.txt_name_en.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.txt_price = QLineEdit()
        self.txt_price.setPlaceholderText("តម្លៃស្តង់ដារ ($)...")
        self.txt_price.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        
        img_layout = QHBoxLayout()
        self.txt_image_path = QLineEdit()
        self.txt_image_path.setPlaceholderText("ជ្រើសរើសរូបភាព (png/jpg < 5MB)...")
        self.txt_image_path.setReadOnly(True)
        self.txt_image_path.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px; background-color: #ecf0f1;")
        
        self.btn_browse = QPushButton("📁 ស្វែងរក (Browse)")
        self.btn_browse.setStyleSheet("background-color: #7f8c8d; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_browse.clicked.connect(self.browse_image)
        
        self.img_preview = QLabel("គ្មានរូប")
        self.img_preview.setFixedSize(40, 40)
        self.img_preview.setStyleSheet("border: 1px dashed #aaa; border-radius: 4px; background-color: white;")
        self.img_preview.setAlignment(Qt.AlignCenter)
        self.img_preview.setScaledContents(True)

        img_layout.addWidget(self.txt_image_path)
        img_layout.addWidget(self.btn_browse)
        img_layout.addWidget(self.img_preview)
        
        action_layout = QHBoxLayout()
        self.btn_submit = QPushButton("➕ បន្ថែមមុខម្ហូបថ្មី (Add)")
        self.btn_submit.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; border-radius: 4px; font-weight: bold;")
        self.btn_submit.clicked.connect(self.submit_form)
        
        self.btn_cancel = QPushButton("❌ បោះបង់ (Cancel)")
        self.btn_cancel.setStyleSheet("background-color: #95a5a6; color: white; padding: 10px; border-radius: 4px; font-weight: bold;")
        self.btn_cancel.clicked.connect(self.clear_form)
        self.btn_cancel.hide() # លាក់សិន វានឹងលោតចេញពេលចុចកំណត់ (Edit)
        
        action_layout.addWidget(self.btn_submit)
        action_layout.addWidget(self.btn_cancel)
        
        grid.addWidget(QLabel("🇰🇭 ភាសាខ្មែរ:"), 0, 0)
        grid.addWidget(self.txt_name_km, 0, 1)
        grid.addWidget(QLabel("🇨🇳 中文:"), 0, 2)
        grid.addWidget(self.txt_name_zh, 0, 3)
        grid.addWidget(QLabel("🇬🇧 English:"), 1, 0)
        grid.addWidget(self.txt_name_en, 1, 1)
        grid.addWidget(QLabel("💲 តម្លៃ (Price):"), 1, 2)
        grid.addWidget(self.txt_price, 1, 3)
        grid.addWidget(QLabel("🖼️ រូបភាព (<5MB):"), 2, 0)
        grid.addLayout(img_layout, 2, 1, 1, 3)
        grid.addLayout(action_layout, 3, 0, 1, 4)
        
        self.group_box.setLayout(grid)
        layout.addWidget(self.group_box)
        layout.addSpacing(10)

        # ---------------- ប្រអប់ស្វែងរកមុខម្ហូប (Live Search) ---------------- #
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 ស្វែងរកមុខម្ហូប:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("វាយឈ្មោះមុខម្ហូប ដើម្បីស្វែងរកលឿន (Live Search)...")
        self.search_input.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # ---------------- តារាងបង្ហាញមុខម្ហូប ---------------- #
        self.table = MenuTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["លេខកូដ (ID)", "រូបភាព", "ឈ្មោះមុខម្ហូប", "តម្លៃ ($)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background-color: white; border-radius: 5px;")
        self.table.setAlternatingRowColors(True) # តារាងឆ្លាស់ពណ៌ ងាយស្រួលមើល
        self.table.setIconSize(QSize(50, 50))
        self.table.order_changed.connect(self.save_new_order)
        layout.addWidget(self.table)

        # ---------------- ប៊ូតុងបញ្ជា ---------------- #
        btn_layout = QHBoxLayout()
        btn_delete = QPushButton("🗑️ លុបមុខម្ហូបដែលបានជ្រើសរើស")
        btn_delete.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        btn_delete.clicked.connect(self.delete_item)
        
        # បិទសិទ្ធិមិនឱ្យ staff លុបមុខម្ហូបបាន (ឃើញប៊ូតុង តែចុចមិនបាន)
        if os.environ.get("CURRENT_USER", "admin") != "admin":
            btn_delete.setEnabled(False)
            self.btn_submit.setEnabled(False)

        self.btn_refresh = QPushButton("🔄 ធ្វើបច្ចុប្បន្នភាព")
        self.btn_refresh.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_refresh.clicked.connect(self.load_menu)
        
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(self.btn_refresh)
        layout.addLayout(btn_layout)
        
        # ចុចលើតារាងដើម្បីទាញទិន្នន័យមកបំពេញក្នុង Form
        self.table.itemClicked.connect(self.populate_inputs)

        self.image_threads = []
        self.load_menu()

    def load_menu(self):
        self.btn_refresh.setText("⏳ កំពុងទាញយក...")
        self.btn_refresh.setEnabled(False)
        self.worker = MenuWorker()
        self.worker.data_loaded.connect(self.populate_table)
        self.worker.start()

    def populate_table(self, data):
        self.btn_refresh.setText("🔄 ធ្វើបច្ចុប្បន្នភាព")
        self.btn_refresh.setEnabled(True)
        self.search_input.clear()
        self.table.setRowCount(0)
        self._current_menu_data = data # រក្សាទុកក្នុង Memory ដើម្បីងាយស្រួលទាញមក Edit
        self.table.setRowCount(len(data))
        self.table.verticalHeader().setDefaultSectionSize(60) # ពង្រីកកម្ពស់ជួរដេក ដើម្បីដាក់រូបភាពបាន
        for row, item in enumerate(data):
            item_id = item.get("id", "")
            self.table.setItem(row, 0, QTableWidgetItem(str(item_id)))
            
            # ទាញយករូបភាពមកបង្ហាញ
            img_url = item.get("image_url", "")
            img_item = QTableWidgetItem()
            img_item.setTextAlignment(Qt.AlignCenter)
            if img_url:
                img_item.setText("⏳ ទាញ...")
                t = ImageDownloader(item_id, img_url)
                t.image_loaded.connect(self.set_image_to_cell)
                self.image_threads.append(t)
                t.start()
            else:
                img_item.setText("គ្មានរូប")
            self.table.setItem(row, 1, img_item)
            
            self.table.setItem(row, 2, QTableWidgetItem(item.get("name", "")))
            self.table.setItem(row, 3, QTableWidgetItem(f"${item.get('price', 0.0):.2f}"))

    def set_image_to_cell(self, item_id, img_data):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) and self.table.item(row, 0).text() == str(item_id):
                item = self.table.item(row, 1)
                if item and img_data:
                    pixmap = QPixmap()
                    if pixmap.loadFromData(img_data):
                        icon = QIcon(pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        item.setIcon(icon)
                        item.setText("")
                    else:
                        item.setText("⚠️ Error")
                break

    def save_new_order(self, reordered_items):
        if not reordered_items: return
        success, msg = APIClient.reorder_menu(reordered_items)
        if not success:
            QMessageBox.warning(self, "កំហុស", f"មិនអាចរក្សាទុកលេខរៀងថ្មីបានទេ!\nបញ្ហា: {msg}")
            self.load_menu()

    def filter_table(self, text):
        search_text = text.lower()
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 2)
            if name_item:
                self.table.setRowHidden(row, search_text not in name_item.text().lower())

    def browse_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "ជ្រើសរើសរូបភាពផលិតផល", "", "Images (*.png *.jpg *.jpeg)", options=options)
        if file_name:
            file_size = os.path.getsize(file_name)
            max_size_mb = 5
            if file_size > max_size_mb * 1024 * 1024:
                QMessageBox.warning(self, "ជូនដំណឹង", f"ទំហំរូបភាពធំជាង {max_size_mb}MB!\nសូមជ្រើសរើសរូបតូចជាងនេះ។")
                return
            self.selected_image_path = file_name
            self.txt_image_path.setText(file_name)
            # បង្ហាញរូបភាពជា Preview
            pixmap = QPixmap(file_name)
            self.img_preview.setPixmap(pixmap)

    def clear_form(self):
        self.txt_name_km.clear()
        self.txt_name_zh.clear()
        self.txt_name_en.clear()
        self.txt_price.clear()
        if hasattr(self, 'txt_image_path'):
            self.txt_image_path.clear()
        self.img_preview.clear()
        self.img_preview.setText("គ្មានរូប")
        self.selected_image_path = None
        self.editing_item_id = None
        self.editing_image_url = ""
        self.btn_submit.setText("➕ បន្ថែមមុខម្ហូបថ្មី (Add)")
        self.btn_submit.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; border-radius: 4px; font-weight: bold;")
        self.btn_cancel.hide()
        self.table.clearSelection()

    def submit_form(self):
        km = self.txt_name_km.text().strip()
        zh = self.txt_name_zh.text().strip()
        en = self.txt_name_en.text().strip()
        price_str = self.txt_price.text().strip()
        
        if not all([km, price_str]):
            QMessageBox.warning(self, "ជូនដំណឹង", "សូមបំពេញឈ្មោះ (យ៉ាងហោចណាស់ភាសាខ្មែរ) និងតម្លៃជាមុនសិន!")
            return
            
        try:
            price = float(price_str)
        except ValueError:
            QMessageBox.warning(self, "ជូនដំណឹង", "តម្លៃត្រូវតែជាលេខ (ឧទាហរណ៍: 2.50)!")
            return

        parts = [p for p in [km, zh, en] if p]
        full_name = " | ".join(parts)
        image_url = self.editing_image_url

        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        # Upload Image if selected
        if hasattr(self, 'selected_image_path') and self.selected_image_path:
            image_url = APIClient.upload_image(self.selected_image_path)
            if not image_url:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(self, "Upload Failed", "បរាជ័យក្នុងការ Upload រូបភាព! សូមពិនិត្យមើលការភ្ជាប់ Network ឬ Server។")
                return

        if self.editing_item_id:
            # កំពុងស្ថិតក្នុងទម្រង់កែប្រែ (Update Mode)
            success = APIClient.update_menu_item(self.editing_item_id, full_name, price, image_url)
            QApplication.restoreOverrideCursor()
            if success:
                QMessageBox.information(self, "ជោគជ័យ", "មុខម្ហូបត្រូវបានកែប្រែដោយជោគជ័យ!")
                self.clear_form()
                self.load_menu()
            else:
                QMessageBox.critical(self, "បរាជ័យ", "មានបញ្ហាក្នុងការកែប្រែមុខម្ហូប។")
        else:
            # កំពុងស្ថិតក្នុងទម្រង់បន្ថែម (Add Mode)
            success, error_msg = APIClient.add_menu_item({"name": full_name, "price": price, "image_url": image_url})
            QApplication.restoreOverrideCursor()
            if success:
                QMessageBox.information(self, "ជោគជ័យ", "បានបន្ថែមមុខម្ហូបថ្មីដោយជោគជ័យ!")
                self.clear_form()
                self.load_menu()
            else:
                QMessageBox.critical(self, "បរាជ័យ", f"មិនអាចបន្ថែមមុខម្ហូបបានទេ!\n\n{error_msg}")

    def delete_item(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "ជូនដំណឹង", "សូមចុចជ្រើសរើសមុខម្ហូបណាមួយក្នុងតារាងជាមុនសិន ដើម្បីលុប!")
            return
        
        item_id = self.table.item(current_row, 0).text()
        if APIClient.delete_menu_item(item_id):
            self.load_menu()
        else:
            QMessageBox.critical(self, "កំហុស", "មិនអាចលុបមុខម្ហូបបានទេ!")

    def populate_inputs(self, item):
        row = item.row()
        item_id_widget = self.table.item(row, 0)
        if not item_id_widget or not hasattr(self, '_current_menu_data'): return
        
        try: item_id = int(item_id_widget.text())
        except ValueError: return
        
        data = next((m for m in self._current_menu_data if m["id"] == item_id), None)
        if not data:
            return
        
        # បំបែកឈ្មោះជា ៣ ភាសាដើម្បីបំពេញចូលប្រអប់
        name_parts = [p.strip() for p in data.get("name", "").replace("/", "|").split("|")]
        self.txt_name_km.setText(name_parts[0] if len(name_parts) > 0 else "")
        self.txt_name_zh.setText(name_parts[1] if len(name_parts) > 1 else "")
        self.txt_name_en.setText(name_parts[2] if len(name_parts) > 2 else "")
        
        self.txt_price.setText(str(data.get("price", "")))
        self.txt_image_path.setText("រក្សារូបភាពចាស់ (Keep old image)")
        self.selected_image_path = None
        
        self.editing_item_id = item_id
        self.editing_image_url = data.get("image_url", "")
        self.btn_submit.setText("💾 រក្សាទុកការកែប្រែ (Save)")
        self.btn_submit.setStyleSheet("background-color: #f39c12; color: white; padding: 10px; border-radius: 4px; font-weight: bold;")
        self.btn_cancel.show()
