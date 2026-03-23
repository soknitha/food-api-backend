import csv
import webbrowser
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLineEdit, QMessageBox, QFileDialog, QMenu, QApplication, QInputDialog
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from services.api_client import APIClient

class UsersWorker(QThread):
    data_loaded = pyqtSignal(list)
    def run(self):
        data = APIClient.get_users()
        self.data_loaded.emit(data or [])

class UsersPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("👥 គ្រប់គ្រងអតិថិជន (Customer Management)")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)

        # ---------------- Form សម្រាប់បន្ថែមអតិថិជន ---------------- #
        form_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("ឈ្មោះអតិថិជន...")
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("លេខទូរស័ព្ទ...")
        
        btn_add = QPushButton("➕ បន្ថែមអតិថិជន")
        btn_add.setStyleSheet("background-color: #3498db; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        btn_add.clicked.connect(self.add_user)

        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.phone_input)
        form_layout.addWidget(btn_add)
        layout.addLayout(form_layout)

        # ---------------- តារាងបង្ហាញអតិថិជន ---------------- #
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Telegram ID", "ឈ្មោះ", "លេខទូរស័ព្ទ", "ទីតាំង (Plus Code)", "ពិន្ទុសន្សំ"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background-color: white; border-radius: 5px;")
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

        # ---------------- ប៊ូតុងបញ្ជា ---------------- #
        btn_layout = QHBoxLayout()
        btn_delete = QPushButton("🗑️ លុបអតិថិជន")
        btn_delete.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        btn_delete.clicked.connect(self.delete_user)
        
        btn_msg = QPushButton("💬 ផ្ញើសារផ្ទាល់")
        btn_msg.setStyleSheet("background-color: #9b59b6; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        btn_msg.clicked.connect(self.send_direct_message)
        
        self.btn_refresh = QPushButton("🔄 ធ្វើបច្ចុប្បន្នភាព")
        self.btn_refresh.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_refresh.clicked.connect(self.load_users)
        
        btn_export = QPushButton("📥 ទាញយកជា Excel (CSV)")
        btn_export.setStyleSheet("background-color: #f1c40f; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        btn_export.clicked.connect(self.export_excel)
        
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_msg)
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(btn_export)
        layout.addLayout(btn_layout)

        self.load_users()

    def load_users(self):
        if hasattr(self, 'worker') and self.worker.isRunning(): return
        self.btn_refresh.setText("⏳ កំពុងទាញយក...")
        self.worker = UsersWorker()
        self.worker.data_loaded.connect(self.populate_table)
        self.worker.start()

    def populate_table(self, data):
        self.btn_refresh.setText("🔄 ធ្វើបច្ចុប្បន្នភាព")
        self.table.setRowCount(0)
        self.table.setRowCount(len(data))
        for row, user in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(str(user.get("id", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(user.get("name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(user.get("phone", "N/A")))
            
            location_item = QTableWidgetItem(user.get("location", ""))
            location_item.setToolTip("ចុចពីរដង (Double-click) ដើម្បីបើក Google Map")
            self.table.setItem(row, 3, location_item)
            
            self.table.setItem(row, 4, QTableWidgetItem(str(user.get("points", 0))))
        
        self.table.cellDoubleClicked.connect(self.open_location_in_map)

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if item and item.column() == 3: # ជួរឈរទីតាំង
            menu = QMenu()
            copy_action = menu.addAction("📋 Copy Plus Code")
            action = menu.exec_(self.table.mapToGlobal(pos))
            if action == copy_action:
                QApplication.clipboard().setText(item.text())
                QMessageBox.information(self, "ជោគជ័យ", "បានចម្លងកូដទីតាំង (Plus Code) រួចរាល់!")

    def add_user(self):
        # កន្លែងនេះសរសេរកូដសម្រាប់បញ្ជូនទិន្នន័យអតិថិជនថ្មីទៅ API
        name = self.name_input.text()
        phone = self.phone_input.text()
        
        if not name or not phone:
            QMessageBox.warning(self, "ជូនដំណឹង", "សូមបំពេញឈ្មោះ និងលេខទូរស័ព្ទ!")
            return
            
        if APIClient.add_user({"name": name, "phone": phone}):
            self.name_input.clear()
            self.phone_input.clear()
            self.load_users()
        else:
            QMessageBox.critical(self, "កំហុស", "មិនអាចភ្ជាប់ទៅកាន់ Server បានទេ!")

    def delete_user(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "ជូនដំណឹង", "សូមជ្រើសរើសអតិថិជនក្នុងតារាងជាមុនសិន ដើម្បីលុប!")
            return
        
        user_id = self.table.item(current_row, 0).text()
        if APIClient.delete_user(user_id):
            self.load_users()
        else:
            QMessageBox.critical(self, "កំហុស", "មិនអាចលុបអតិថិជនបានទេ!")

    def send_direct_message(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "ជូនដំណឹង", "សូមជ្រើសរើសអតិថិជនក្នុងតារាងជាមុនសិន ដើម្បីផ្ញើសារ!")
            return
        
        chat_id = self.table.item(current_row, 0).text()
        customer_name = self.table.item(current_row, 1).text()
        
        if not chat_id or "manual" in chat_id.lower():
            QMessageBox.warning(self, "កំហុស", "អតិថិជននេះមិនមានគណនី Telegram ត្រឹមត្រូវទេ (អាចជាអតិថិជនដែលអ្នកបញ្ចូលដោយដៃ)!")
            return
            
        text, ok = QInputDialog.getMultiLineText(self, "ផ្ញើសារផ្ទាល់", f"វាយសារដែលអ្នកចង់ផ្ញើទៅកាន់ {customer_name}:")
        if ok and text.strip():
            if APIClient.send_crm_reply(chat_id, text.strip()):
                QMessageBox.information(self, "ជោគជ័យ", f"សារត្រូវបានផ្ញើទៅកាន់ {customer_name} រួចរាល់!")
            else:
                QMessageBox.critical(self, "កំហុស", "មានបញ្ហាក្នុងការផ្ញើសារ (សូមពិនិត្យមើលការតភ្ជាប់អ៊ីនធឺណិត ឬ API)!")

    def open_location_in_map(self, row, column):
        if column == 3: # ជួរឈរទីតាំង
            item = self.table.item(row, column)
            if item and item.text():
                webbrowser.open(f"https://www.google.com/maps/search/?api=1&query={item.text()}")

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "រក្សាទុកជា Excel", "", "CSV Files (*.csv)")
        if path:
            try:
                # ប្រើ utf-8-sig ដើម្បីអោយ Excel ស្គាល់អក្សរខ្មែរ (Unicode)
                with open(path, 'w', newline='', encoding='utf-8-sig') as stream:
                    writer = csv.writer(stream)
                    
                    # ទាញយកក្បាលតារាង (Headers)
                    headers = []
                    for column in range(self.table.columnCount()):
                        item = self.table.horizontalHeaderItem(column)
                        headers.append(item.text() if item else "")
                    writer.writerow(headers)
                    
                    # ទាញយកទិន្នន័យពីតារាង
                    for row in range(self.table.rowCount()):
                        row_data = []
                        for column in range(self.table.columnCount()):
                            item = self.table.item(row, column)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)
                        
                QMessageBox.information(self, "ជោគជ័យ", "ទិន្នន័យត្រូវបានទាញយកដោយជោគជ័យ!")
            except Exception as e:
                QMessageBox.critical(self, "កំហុស", f"មានបញ្ហាក្នុងការរក្សាទុកឯកសារ៖ {e}")
