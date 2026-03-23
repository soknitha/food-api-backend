import json
import os

CRED_FILE = "credentials.json"

class PrinterService:
    @staticmethod
    def auto_print_receipt(arg1, customer=None, items_str=None, total=None):
        printer_ip = ""
        if os.path.exists(CRED_FILE):
            with open(CRED_FILE, "r") as f:
                data = json.load(f)
                printer_ip = data.get("printer_ip", "")
        
        if not printer_ip:
            print("មិនមានកំណត់ IP ម៉ាស៊ីនព្រីនទេ (No Printer IP configured).")
            return False
            
        try:
            from escpos.printer import Network
            # តភ្ជាប់ទៅម៉ាស៊ីនព្រីនតាម IP (ច្រកលំនាំដើមគឺ 9100)
            printer = Network(printer_ip)
            
            if customer is None and os.path.exists(arg1):
                # ករណីព្រីនជារូបភាព (វិក្កយបត្រថ្មី ឬរបាយការណ៍)
                printer.image(arg1)
                printer.text("\n\n")
            else:
                # ករណីព្រីនជាអក្សរធម្មតា (កូដចាស់)
                order_id = arg1
                printer.set(align='center', bold=True, double_height=True, double_width=True)
                printer.text("FoodAdmin Shop\n")
                printer.set(align='center', normal_text=True)
                printer.text("================================\n")
                printer.set(align='left')
                printer.text(f"Order ID: {order_id}\n")
                printer.text(f"Customer: {customer}\n")
                printer.text("--------------------------------\n")
                items = items_str.split(", ")
                for item in items:
                    printer.text(f"{item}\n")
                printer.text("--------------------------------\n")
                printer.set(align='right', bold=True)
                printer.text(f"Total: {total}\n")
                printer.set(align='center', normal_text=True)
                printer.text("================================\n")
                printer.text("Thank you! Please come again.\n\n\n\n")

            printer.cut() # កាត់ក្រដាសដោយស្វ័យប្រវត្តិ
            return True
        except Exception as e:
            print(f"បញ្ហាម៉ាស៊ីនព្រីន: {e}")
            return False