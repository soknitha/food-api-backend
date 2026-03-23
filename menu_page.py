from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLineEdit, QMessageBox, QApplication, QFileDialog, QGroupBox, QGridLayout
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # បិទសារព្រមានការរំលង SSL
from config import API_BASE_URL
from services.api_client import APIClient

class MenuWorker(QThread):
    data_loaded = pyqtSignal(list)
    def run(self):
        data = APIClient.get_menu()
        self.data_loaded.emit(data or [])

# Memory សម្រាប់ផ្ទុករូបភាពដែលទាញរួចកុំឱ្យវាទាញចុះទាញឡើងនាំឱ្យយឺត
IMAGE_CACHE = {}

class ImageDownloader(QThread):
    image_loaded = pyqtSignal(int, bytes)
    def __init__(self, row, url):
        super().__init__()
        self.row, self.url = row, url
    def run(self):
        if self.url in IMAGE_CACHE:
            self.image_loaded.emit(self.row, IMAGE_CACHE[self.url])
            return
        try: 
            res = requests.get(self.url, timeout=10, verify=False).content
            IMAGE_CACHE[self.url] = res
        except: res = b""
        self.image_loaded.emit(self.row, res)

class MenuPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

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
        img_layout.addWidget(self.txt_image_path)
        img_layout.addWidget(self.btn_browse)
        
        btn_add = QPushButton("✅ បញ្ជាក់ការបន្ថែមមុខម្ហូប (Authorize)")
        btn_add.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; border-radius: 4px; font-weight: bold;")
        btn_add.clicked.connect(self.add_item)
        
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
        grid.addWidget(btn_add, 3, 0, 1, 4)
        
        self.group_box.setLayout(grid)
        layout.addWidget(self.group_box)
        layout.addSpacing(10)

        # ---------------- តារាងបង្ហាញមុខម្ហូប ---------------- #
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["លេខកូដ (ID)", "រូបភាព", "ឈ្មោះមុខម្ហូប", "តម្លៃ ($)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background-color: white; border-radius: 5px;")
        layout.addWidget(self.table)

        # ---------------- ប៊ូតុងបញ្ជា ---------------- #
        btn_layout = QHBoxLayout()
        btn_edit = QPushButton("✏️ កែប្រែ (Edit)")
        btn_edit.setStyleSheet("background-color: #f39c12; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        btn_edit.clicked.connect(self.edit_item)
        
        btn_delete = QPushButton("🗑️ លុបមុខម្ហូបដែលបានជ្រើសរើស")
        btn_delete.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        btn_delete.clicked.connect(self.delete_item)
        
        # បិទសិទ្ធិមិនឱ្យ staff លុបមុខម្ហូបបាន (ឃើញប៊ូតុង តែចុចមិនបាន)
        if os.environ.get("CURRENT_USER", "admin") != "admin":
            btn_edit.setEnabled(False)
            btn_delete.setEnabled(False)

        self.btn_refresh = QPushButton("🔄 ធ្វើបច្ចុប្បន្នភាព")
        self.btn_refresh.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_refresh.clicked.connect(self.load_menu)
        
        btn_layout.addWidget(btn_edit)
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
        self.table.setRowCount(0)
        self._current_menu_data = data # រក្សាទុកក្នុង Memory ដើម្បីងាយស្រួលទាញមក Edit
        self.table.setRowCount(len(data))
        self.table.verticalHeader().setDefaultSectionSize(60) # ពង្រីកកម្ពស់ជួរដេក ដើម្បីដាក់រូបភាពបាន
        for row, item in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(str(item.get("id", ""))))
            
            # ទាញយករូបភាពមកបង្ហាញ
            img_url = item.get("image_url", "")
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignCenter)
            if img_url:
                img_label.setText("⏳ កំពុងទាញ...")
                t = ImageDownloader(row, img_url)
                t.image_loaded.connect(self.set_image_to_cell)
                self.image_threads.append(t)
                t.start()
            else:
                img_label.setText("គ្មានរូប")
            self.table.setCellWidget(row, 1, img_label)
            
            self.table.setItem(row, 2, QTableWidgetItem(item.get("name", "")))
            self.table.setItem(row, 3, QTableWidgetItem(f"${item.get('price', 0.0):.2f}"))

    def set_image_to_cell(self, row, img_data):
        img_label = self.table.cellWidget(row, 1)
        if img_label and img_data:
            pixmap = QPixmap()
            if pixmap.loadFromData(img_data):
                img_label.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                img_label.setText("⚠️ Error")

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

    def add_item(self):
        km = self.txt_name_km.text().strip()
        zh = self.txt_name_zh.text().strip()
        en = self.txt_name_en.text().strip()
        price_str = self.txt_price.text().strip()
        
        if not all([km, zh, en, price_str]):
            QMessageBox.warning(self, "ជូនដំណឹង", "សូមបំពេញឈ្មោះ និងតម្លៃឱ្យបានគ្រប់ជ្រុងជ្រោយ (ទាំង ៣ ភាសា)!")
            return
            
        try:
            price = float(price_str)
        except ValueError:
            QMessageBox.warning(self, "ជូនដំណឹង", "តម្លៃត្រូវតែជាលេខ (ឧទាហរណ៍: 2.50)!")
            return

        full_name = f"{km} | {zh} | {en}"
        image_url = ""

        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        # Upload Image if selected
        if hasattr(self, 'selected_image_path') and self.selected_image_path:
            try:
                with open(self.selected_image_path, "rb") as f:
                    # បន្ថែម verify=False ដើម្បីដោះស្រាយបញ្ហា SSL Error ពី Railway
                    res = requests.post(f"{API_BASE_URL}/upload", files={"file": f}, timeout=30, verify=False)
                    if res.status_code == 200:
                        image_url = res.json().get("image_url", "")
                    else:
                        QApplication.restoreOverrideCursor()
                        QMessageBox.warning(self, "Upload Failed", f"បរាជ័យក្នុងការ Upload រូបភាព! (Server Error: {res.status_code})")
                        return
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(self, "Network Error", f"មិនអាចភ្ជាប់ទៅកាន់ Server ដើម្បី Upload រូបភាពបានទេ: {e}")
                return

        success, error_msg = APIClient.add_menu_item({"name": full_name, "price": price, "image_url": image_url})
        QApplication.restoreOverrideCursor()

        if success:
            self.txt_name_km.clear()
            self.txt_name_zh.clear()
            self.txt_name_en.clear()
            self.txt_price.clear()
            if hasattr(self, 'txt_image_path'):
                self.txt_image_path.clear()
            self.selected_image_path = None
            self.load_menu()
            QMessageBox.information(self, "ជោគជ័យ", "បានបន្ថែមមុខម្ហូបថ្មីដោយជោគជ័យ!")
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
        if not hasattr(self, '_current_menu_data') or row >= len(self._current_menu_data):
            return
        data = self._current_menu_data[row]
        
        # បំបែកឈ្មោះជា ៣ ភាសាដើម្បីបំពេញចូលប្រអប់
        name_parts = [p.strip() for p in data.get("name", "").replace("/", "|").split("|")]
        self.txt_name_km.setText(name_parts[0] if len(name_parts) > 0 else "")
        self.txt_name_zh.setText(name_parts[1] if len(name_parts) > 1 else "")
        self.txt_name_en.setText(name_parts[2] if len(name_parts) > 2 else "")
        
        self.txt_price.setText(str(data.get("price", "")))
        self.txt_image_path.setText("រក្សារូបភាពចាស់ (Keep old image)")
        self.selected_image_path = None

    def edit_item(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "ព្រមាន", "សូមជ្រើសរើសមុខម្ហូបដែលអ្នកចង់កែប្រែជាមុនសិន!")
            return
        
        if not hasattr(self, '_current_menu_data') or current_row >= len(self._current_menu_data):
            return
            
        item_data = self._current_menu_data[current_row]
        item_id = item_data["id"]
        old_image_url = item_data.get("image_url", "")

        km = self.txt_name_km.text().strip()
        zh = self.txt_name_zh.text().strip()
        en = self.txt_name_en.text().strip()
        price_str = self.txt_price.text().strip()
        
        if not all([km, price_str]):
            QMessageBox.warning(self, "ជូនដំណឹង", "សូមបំពេញឈ្មោះ (យ៉ាងហោចណាស់ភាសាខ្មែរ) និងតម្លៃជាមុនសិន!")
            return

        try:
            new_price = float(price_str)
        except ValueError:
            QMessageBox.warning(self, "ជូនដំណឹង", "តម្លៃត្រូវតែជាលេខ (ឧទាហរណ៍: 2.50)!")
            return

        parts = [p for p in [km, zh, en] if p]
        new_name = " | ".join(parts)

        QApplication.setOverrideCursor(Qt.WaitCursor)
        image_url = old_image_url
        
        if hasattr(self, 'selected_image_path') and self.selected_image_path:
            try:
                with open(self.selected_image_path, "rb") as f:
                    res = requests.post(f"{API_BASE_URL}/upload", files={"file": f}, timeout=30, verify=False)
                    if res.status_code == 200:
                        image_url = res.json().get("image_url", "")
                    else:
                        QApplication.restoreOverrideCursor()
                        QMessageBox.warning(self, "Upload Failed", "បរាជ័យក្នុងការ Upload រូបភាពថ្មី!")
                        return
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(self, "Network Error", f"មិនអាចភ្ជាប់ទៅ Server ទេ: {e}")
                return

        if APIClient.update_menu_item(item_id, new_name, new_price, image_url):
            self.load_menu()
            QApplication.restoreOverrideCursor()
            QMessageBox.information(self, "ជោគជ័យ", "មុខម្ហូបត្រូវបានកែប្រែដោយជោគជ័យ!")
        else:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "បរាជ័យ", "មានបញ្ហាក្នុងការកែប្រែមុខម្ហូប។")
