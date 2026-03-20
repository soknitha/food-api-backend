import sys
import os
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtGui import QIcon

# បន្ថែម Folder ធំ (Root) ទៅក្នុង Path ដើម្បីឱ្យ Python រក Files ផ្សេងៗឃើញ
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from views.main_window import AdminDashboard
from views.login_page import LoginWindow

def main():
    app = QApplication(sys.argv)
    
    app.setQuitOnLastWindowClosed(False) # អនុញ្ញាតឱ្យកម្មវិធីលាក់ខ្លួនក្នុង Tray
    
    # ដាក់រូបតំណាង (Icon) ឱ្យកម្មវិធី
    icon_path = os.path.join(os.path.dirname(__file__), 'app_icon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # បើកផ្ទាំង Login មុនគេ
    login = LoginWindow()
    if login.exec_() == QDialog.Accepted:
        # បើកផ្ទាំងសរុប (Admin Desktop App) លុះត្រាតែ Login ត្រឹមត្រូវ
        admin_app = AdminDashboard()
        admin_app.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()