import sys
import os
import warnings

from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtGui import QIcon, QFont, QFontDatabase

# បន្ថែម Folder ធំ (Root) ទៅក្នុង Path ដើម្បីឱ្យ Python រក Files ផ្សេងៗឃើញ
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from views.main_window import AdminDashboard  # noqa: E402
from views.login_page import LoginWindow  # noqa: E402

# បិទរាល់សារព្រមាន (Warnings) ទាំងអស់កុំឱ្យលោតរំខាន
warnings.filterwarnings("ignore")

def main():
    app = QApplication(sys.argv)
    
    # Load Custom Modern Khmer Font (Noto Sans Khmer) សម្រាប់ Admin App ទាំងមូល
    font_path = os.path.join(os.path.dirname(__file__), 'assets', 'NotoSansKhmer-Regular.ttf')
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                app.setFont(QFont(font_families[0], 10))
    else:
        app.setFont(QFont("Khmer OS Battambang", 10))

    # app.setQuitOnLastWindowClosed(False) # បិទសិន ដើម្បីឱ្យកម្មវិធី Exit ទាំងស្រុងពេលចុចខ្វែង (X)
    
    # ដាក់រូបតំណាង (Icon) ឱ្យកម្មវិធី
    icon_path = os.path.join(os.path.dirname(__file__), 'app_icon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # បើកផ្ទាំង Login មុនគេ
    login = LoginWindow()
    if login.exec() == QDialog.Accepted: # ដកសញ្ញា _ ចេញ ព្រោះវាហួសសម័យ
        # បើកផ្ទាំងសរុប (Admin Desktop App) លុះត្រាតែ Login ត្រឹមត្រូវ
        admin_app = AdminDashboard()
        admin_app.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()