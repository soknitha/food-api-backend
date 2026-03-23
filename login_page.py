import json
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QCheckBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login - FoodAdmin")
        self.setFixedSize(350, 300)
        self.setStyleSheet("background-color: #ffffff;")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("🔐 ចូលប្រើប្រាស់ប្រព័ន្ធ")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("ឈ្មោះគណនី (admin)")
        self.user_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(self.user_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("លេខសម្ងាត់ (12345)")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px;")
        layout.addWidget(self.pass_input)

        self.remember_cb = QCheckBox("ចងចាំគណនី (Remember Me)")
        self.remember_cb.setStyleSheet("color: #555; font-weight: bold;")
        layout.addWidget(self.remember_cb)

        btn_login = QPushButton("ចូល (Login)")
        btn_login.setStyleSheet("background-color: #3498db; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
        btn_login.clicked.connect(self.check_login)
        layout.addWidget(btn_login)

        self.load_session()

    def load_session(self):
        if os.path.exists("session.json"):
            try:
                with open("session.json", "r") as f:
                    data = json.load(f)
                    if data.get("remember"):
                        self.user_input.setText(data.get("username", ""))
                        self.pass_input.setText(data.get("password", ""))
                        self.remember_cb.setChecked(True)
            except:
                pass

    def check_login(self):
        CRED_FILE = "credentials.json"
        valid_users = {"admin": "12345"} # គណនីលំនាំដើម
        
        if os.path.exists(CRED_FILE):
            try:
                with open(CRED_FILE, "r") as f:
                    data = json.load(f)
                    if "username" in data and "password" in data:
                        valid_users[data["username"]] = data["password"]
                    if "users" in data:
                        valid_users.update(data["users"])
            except:
                pass
                
        in_user = self.user_input.text().strip()
        in_pass = self.pass_input.text().strip()

        if in_user in valid_users and valid_users[in_user] == in_pass:
            # រក្សាទុកឈ្មោះគណនីដែលកំពុង Login
            os.environ["CURRENT_USER"] = in_user
            if self.remember_cb.isChecked():
                with open("session.json", "w") as f:
                    json.dump({"remember": True, "username": in_user, "password": in_pass}, f)
            else:
                if os.path.exists("session.json"):
                    os.remove("session.json")
            self.accept()
        else:
            QMessageBox.warning(self, "បរាជ័យ", "ឈ្មោះគណនី ឬលេខសម្ងាត់មិនត្រឹមត្រូវទេ!")