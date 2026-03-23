import PyInstaller.__main__
import os
import shutil
import time

def build_app():
    print("🚀 កំពុងចាប់ផ្តើម Build កម្មវិធី FoodAdmin...")
    start_time = time.time()

    # សម្អាត Folder ចាស់ៗចោលដើម្បីកុំឱ្យមានបញ្ហាសរសេរជាន់គ្នា
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            print(f"🧹 កំពុងលុប {folder} ចាស់...")
            shutil.rmtree(folder)

    # កំណត់រចនាសម្ព័ន្ធ PyInstaller មូលដ្ឋាន
    pyinstaller_args = [
        'admin_app.py',                 # ឯកសារគោល
        '--name=FoodAdmin',             # ឈ្មោះកម្មវិធី
        '--windowed',                   # លាក់ផ្ទាំង Console ពណ៌ខ្មៅ (ដំណើរការជា GUI សុទ្ធ)
        '--noconfirm',                  # យល់ព្រមសរសេរជាន់លើ File ចាស់ដោយស្វ័យប្រវត្តិ
        # បញ្ចូលឯកសារ និង Folder ចាំបាច់ (សម្រាប់ Windows ប្រើសញ្ញា ; បំបែក)
        '--add-data=views;views',
        '--add-data=services;services',
        '--add-data=config.py;.',
        # កាត់បន្ថយទំហំកម្មវិធីឱ្យស្រាល និងដើរលឿនបំផុត ដោយបិទ Module ដែលមិនចាំបាច់ (Optimization)
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=scipy',
        '--exclude-module=tkinter'
    ]

    # បន្ថែមឯកសារផ្សេងៗ ប្រសិនបើវាពិតជាមាននៅក្នុង Folder
    if os.path.exists('app_icon.ico'): pyinstaller_args.append('--icon=app_icon.ico')
    if os.path.exists('logo.png'): pyinstaller_args.append('--add-data=logo.png;.')
    if os.path.exists('notification.wav'): pyinstaller_args.append('--add-data=notification.wav;.')
    if os.path.exists('aba_qr.jpg'): pyinstaller_args.append('--add-data=aba_qr.jpg;.')

    # ដំណើរការ PyInstaller
    PyInstaller.__main__.run(pyinstaller_args)

    print(f"\n✅ ការ Build ទទួលបានជោគជ័យ! ចំណាយពេលសរុប {round(time.time() - start_time, 2)} វិនាទី។")
    print("📁 សូមចូលទៅកាន់ Folder 'dist/FoodAdmin' ហើយចុចបើក 'FoodAdmin.exe' ដើម្បីដំណើរការកម្មវិធី។")

if __name__ == "__main__":
    build_app()