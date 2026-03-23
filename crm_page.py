from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser, QLineEdit, QPushButton, QComboBox, QMessageBox, QFrame
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from services.api_client import APIClient

class CRMWorker(QThread):
    data_loaded = pyqtSignal(list)
    def run(self):
        data = APIClient.get_crm_messages()
        self.data_loaded.emit(data or [])

class CRMPage(QWidget):
    def __init__(self):
        super().__init__()
        self.active_chat_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("💬 Live Chat CRM & Broadcast")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)

        # ---------------- ផ្នែក Broadcast ---------------- #
        bc_frame = QFrame()
        bc_frame.setStyleSheet("background-color: white; border-radius: 8px; padding: 10px;")
        bc_layout = QHBoxLayout(bc_frame)
        
        self.target_combo = QComboBox()
        self.target_combo.addItems(["ផ្ញើទៅកាន់អតិថិជនទាំងអស់ (All)", "អតិថិជនដែលមានក្នុងកន្ត្រក (Pending)"])
        self.target_combo.setStyleSheet("padding: 8px;")
        
        self.bc_input = QLineEdit()
        self.bc_input.setPlaceholderText("វាយសារប្រូម៉ូសិន ឬសេចក្តីជូនដំណឹង...")
        self.bc_input.setStyleSheet("padding: 8px;")
        
        btn_bc = QPushButton("📢 ផ្ញើសារ (Broadcast)")
        btn_bc.setStyleSheet("background-color: #e67e22; color: white; padding: 8px; font-weight: bold;")
        btn_bc.clicked.connect(self.send_broadcast)
        
        bc_layout.addWidget(QLabel("គោលដៅ:"))
        bc_layout.addWidget(self.target_combo)
        bc_layout.addWidget(self.bc_input)
        bc_layout.addWidget(btn_bc)
        layout.addWidget(bc_frame)

        # ---------------- ផ្នែក Live Chat ---------------- #
        chat_layout = QHBoxLayout()
        
        self.chat_display = QTextBrowser()
        self.chat_display.setStyleSheet("background-color: white; border: 1px solid #ccc; border-radius: 8px; padding: 10px; font-size: 14px;")
        chat_layout.addWidget(self.chat_display)
        
        layout.addLayout(chat_layout)

        reply_layout = QHBoxLayout()
        self.chat_id_input = QLineEdit()
        self.chat_id_input.setPlaceholderText("បញ្ចូល Chat ID អតិថិជន...")
        self.chat_id_input.setFixedWidth(150)
        self.chat_id_input.setStyleSheet("padding: 10px;")
        
        self.reply_input = QLineEdit()
        self.reply_input.setPlaceholderText("វាយសារឆ្លើយតបទៅកាន់អតិថិជន...")
        self.reply_input.setStyleSheet("padding: 10px;")
        self.reply_input.returnPressed.connect(self.send_reply)
        
        btn_reply = QPushButton("បញ្ជូន (Send)")
        btn_reply.setStyleSheet("background-color: #3498db; color: white; padding: 10px; font-weight: bold;")
        btn_reply.clicked.connect(self.send_reply)
        
        reply_layout.addWidget(self.chat_id_input)
        reply_layout.addWidget(self.reply_input)
        reply_layout.addWidget(btn_reply)
        layout.addLayout(reply_layout)

        # Auto Refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_messages)
        self.timer.start(5000)
        self.load_messages()

    def send_broadcast(self):
        text = self.bc_input.text().strip()
        if not text: return
        res = APIClient.send_broadcast("all", text)
        if res:
            QMessageBox.information(self, "ជោគជ័យ", f"បានផ្ញើសារទៅកាន់អតិថិជនចំនួន {res.get('sent', 0)} នាក់!")
            self.bc_input.clear()

    def send_reply(self):
        chat_id = self.chat_id_input.text().strip()
        text = self.reply_input.text().strip()
        if not chat_id or not text: return
        
        if APIClient.send_crm_reply(chat_id, text):
            self.reply_input.clear()
            self.load_messages()

    def load_messages(self):
        if hasattr(self, 'worker') and self.worker.isRunning(): return
        self.worker = CRMWorker()
        self.worker.data_loaded.connect(self.update_chat)
        self.worker.start()
        
    def update_chat(self, msgs):
        html = ""
        for m in msgs:
            time_str = m.get("timestamp", "")
            if m.get("is_admin"):
                html += f"<div style='text-align: right; margin-bottom: 10px;'><b style='color: #2980b9;'>Admin:</b> <span style='background-color: #d6eaf8; padding: 5px 10px; border-radius: 10px;'>{m['text']}</span> <br><small style='color: gray;'>{time_str} | ID: {m['chat_id']}</small></div>"
            else:
                html += f"<div style='text-align: left; margin-bottom: 10px;'><b style='color: #27ae60;'>{m['user']}:</b> <span style='background-color: #eaeded; padding: 5px 10px; border-radius: 10px;'>{m['text']}</span> <br><small style='color: gray;'>{time_str} | ID: {m['chat_id']}</small></div>"
        
        # Update only if changed to avoid scrolling jumps
        current_html = self.chat_display.toHtml()
        if len(html) > 10 and html[:100] != current_html[:100]: # Simple heuristic
            self.chat_display.setHtml(html)
            self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())