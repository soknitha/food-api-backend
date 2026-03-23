import json
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFileDialog, QCheckBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from services.api_client import APIClient

CRED_FILE = "credentials.json"

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("⚙️ ការកំណត់ និងប្តូរលេខសម្ងាត់")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)
        layout.addSpacing(20)
        
        layout.addWidget(QLabel("�💳 ការកំណត់គណនីបង់ប្រាក់ (ABA):"))
        aba_layout = QHBoxLayout()
        self.aba_name_input = QLineEdit()
        self.aba_name_input.setPlaceholderText("ឈ្មោះគណនី (ឧ. HEM SINATH)")
        self.aba_name_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        self.aba_number_input = QLineEdit()
        self.aba_number_input.setPlaceholderText("លេខគណនី (ឧ. 086599789)")
        self.aba_number_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        aba_layout.addWidget(self.aba_name_input)
        aba_layout.addWidget(self.aba_number_input)
        layout.addLayout(aba_layout)

        layout.addWidget(QLabel("️ការកំណត់ម៉ាស៊ីនព្រីន POS (WiFi/IP):"))
        self.printer_ip = QLineEdit()
        self.printer_ip.setPlaceholderText("ឧទាហរណ៍: 192.168.1.100")
        self.printer_ip.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(self.printer_ip)

        layout.addWidget(QLabel("📱 ការកំណត់ Mini App (Dynamic Config):"))
        self.banner_input = QLineEdit()
        self.banner_input.setPlaceholderText("Link រូបភាព Banner (URL)...")
        self.banner_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(self.banner_input)
        
        self.is_open_cb = QCheckBox("បើកដំណើរការហាង (អនុញ្ញាតឱ្យភ្ញៀវទិញ)")
        self.is_open_cb.setChecked(True)
        self.is_open_cb.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(self.is_open_cb)

        self.kitchen_group_input = QLineEdit()
        self.kitchen_group_input.setPlaceholderText("លេខ Chat ID ក្រុមចុងភៅផ្ទះបាយ (ឧ. -100123...)")
        self.kitchen_group_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(self.kitchen_group_input)

        layout.addWidget(QLabel("🎁 ការកំណត់ពិន្ទុបញ្ចុះតម្លៃ (Loyalty Program):"))
        reward_layout = QHBoxLayout()
        self.reward_pts_input = QLineEdit()
        self.reward_pts_input.setPlaceholderText("ចំនួនពិន្ទុត្រូវប្តូរ (ឧ. 50)")
        self.reward_pts_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        self.reward_disc_input = QLineEdit()
        self.reward_disc_input.setPlaceholderText("ចំនួនទឹកប្រាក់បញ្ចុះ (ឧ. 5)")
        self.reward_disc_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        reward_layout.addWidget(self.reward_pts_input)
        reward_layout.addWidget(self.reward_disc_input)
        layout.addLayout(reward_layout)

        layout.addWidget(QLabel("🎵 សំឡេងរោទ៍ពេលមានការកុម្ម៉ង់ថ្មី (.wav):"))
        sound_layout = QHBoxLayout()
        self.sound_input = QLineEdit()
        self.sound_input.setPlaceholderText("ជ្រើសរើស File សំឡេង .wav...")
        self.sound_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        btn_browse = QPushButton("📁 ជ្រើសរើស...")
        btn_browse.setStyleSheet("background-color: #34495e; color: white; padding: 10px; border-radius: 5px;")
        btn_browse.clicked.connect(self.browse_sound)
        sound_layout.addWidget(self.sound_input)
        sound_layout.addWidget(btn_browse)
        layout.addLayout(sound_layout)

        layout.addWidget(QLabel("🖼️ រូបតំណាងហាង (Logo):"))
        logo_layout = QHBoxLayout()
        self.logo_input = QLineEdit()
        self.logo_input.setPlaceholderText("ជ្រើសរើស File រូបភាព (.png, .jpg)...")
        self.logo_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        btn_browse_logo = QPushButton("📁 ជ្រើសរើស...")
        btn_browse_logo.setStyleSheet("background-color: #34495e; color: white; padding: 10px; border-radius: 5px;")
        btn_browse_logo.clicked.connect(self.browse_logo)
        logo_layout.addWidget(self.logo_input)
        logo_layout.addWidget(btn_browse_logo)
        layout.addLayout(logo_layout)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("ឈ្មោះគណនីដែលចង់ប្តូរលេខសម្ងាត់...")
        self.username_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(self.username_input)

        self.old_pass = QLineEdit()
        self.old_pass.setPlaceholderText("លេខសម្ងាត់បច្ចុប្បន្ន...")
        self.old_pass.setEchoMode(QLineEdit.Password)
        self.old_pass.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(self.old_pass)

        self.new_pass = QLineEdit()
        self.new_pass.setPlaceholderText("លេខសម្ងាត់ថ្មី...")
        self.new_pass.setEchoMode(QLineEdit.Password)
        self.new_pass.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(self.new_pass)

        btn_save = QPushButton("💾 រក្សាទុកការកំណត់")
        btn_save.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)
        layout.addStretch()
        
        self.load_settings()

    def browse_sound(self):
        path, _ = QFileDialog.getOpenFileName(self, "ជ្រើសរើសសំឡេងរោទ៍", "", "Audio Files (*.wav)")
        if path:
            self.sound_input.setText(path)

    def browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "ជ្រើសរើសរូបតំណាងហាង", "", "Image Files (*.png *.jpg *.jpeg)")
        if path:
            self.logo_input.setText(path)

    def load_settings(self):
        if os.path.exists(CRED_FILE):
            with open(CRED_FILE, "r") as f:
                data = json.load(f)
                self.printer_ip.setText(data.get("printer_ip", ""))
                self.sound_input.setText(data.get("sound_path", ""))
                self.logo_input.setText(data.get("logo_path", ""))
                
        app_cfg = APIClient.get_app_config()
        self.banner_input.setText(app_cfg.get("banner_url", ""))
        self.is_open_cb.setChecked(app_cfg.get("is_open", True))
        self.aba_name_input.setText(app_cfg.get("aba_name", "HEM SINATH"))
        self.aba_number_input.setText(app_cfg.get("aba_number", "086599789"))
        self.kitchen_group_input.setText(app_cfg.get("kitchen_group_id", ""))
        self.reward_pts_input.setText(str(app_cfg.get("reward_points", 50)))
        self.reward_disc_input.setText(str(app_cfg.get("reward_discount", 5.0)))

    def save_settings(self):
        target_user = self.username_input.text().strip()
        old_p = self.old_pass.text()
        new_p = self.new_pass.text()
        p_ip = self.printer_ip.text()
        s_path = self.sound_input.text()
        l_path = self.logo_input.text()
        
        current_data = {"users": {"admin": "12345"}, "printer_ip": "", "sound_path": "", "logo_path": ""}
        if os.path.exists(CRED_FILE):
            try:
                with open(CRED_FILE, "r") as f:
                    file_data = json.load(f)
                    current_data.update(file_data)
                    if "username" in file_data and "password" in file_data and "users" not in file_data:
                        current_data["users"] = {file_data["username"]: file_data["password"]}
            except:
                pass
        
        if old_p or new_p:
            if not target_user:
                QMessageBox.warning(self, "កំហុស", "សូមបញ្ចូលឈ្មោះគណនីដែលអ្នកចង់ប្តូរលេខសម្ងាត់!")
                return
            if target_user not in current_data["users"]:
                QMessageBox.warning(self, "កំហុស", f"រកមិនឃើញគណនីឈ្មោះ '{target_user}' ទេ!")
                return
            if old_p != current_data["users"][target_user]:
                QMessageBox.warning(self, "កំហុស", "លេខសម្ងាត់ចាស់មិនត្រឹមត្រូវទេ!")
                return
            if not new_p:
                QMessageBox.warning(self, "កំហុស", "សូមបញ្ចូលលេខសម្ងាត់ថ្មី!")
                return
            current_data["users"][target_user] = new_p
            
        current_data["printer_ip"] = p_ip
        current_data["sound_path"] = s_path
        current_data["logo_path"] = l_path
        
        with open(CRED_FILE, "w") as f:
            json.dump(current_data, f, indent=4)
            
        pts = int(self.reward_pts_input.text() or 50)
        disc = float(self.reward_disc_input.text() or 5.0)
        APIClient.update_app_config(self.banner_input.text(), self.is_open_cb.isChecked(), self.aba_name_input.text(), self.aba_number_input.text(), self.kitchen_group_input.text(), pts, disc)
        QMessageBox.information(self, "ជោគជ័យ", "ការកំណត់ត្រូវបានរក្សាទុករួចរាល់!")
        self.username_input.clear()
        self.old_pass.clear()
        self.new_pass.clear()