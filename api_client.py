import requests
from config import API_BASE_URL
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# បង្កើត Session ដើម្បីរក្សាការភ្ជាប់ (Connection Pooling) កាត់បន្ថយ Latency ធ្វើឱ្យលឿនជាងមុន ៣ដង
session = requests.Session()

class APIClient:
    @staticmethod
    def get_orders():
        try:
            response = session.get(f"{API_BASE_URL}/orders", timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print("Error API Orders:", e)
        return []

    @staticmethod
    def update_order_status(order_id, status):
        try:
            response = session.put(f"{API_BASE_URL}/orders/status", json={"order_id": order_id, "status": status}, timeout=15)
            return response.status_code == 200
        except Exception as e:
            print("Error API Update Order Status:", e)
            return False

    @staticmethod
    def get_menu():
        try:
            response = session.get(f"{API_BASE_URL}/menu", timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print("Error API Menu:", e)
        return []

    @staticmethod
    def add_menu_item(data):
        try:
            # កំណត់ timeout=30 វិនាទី ការពារ Server Render យឺត (Sleep)
            response = session.post(f"{API_BASE_URL}/menu", json=data, timeout=30)
            if response.ok:
                return True, ""
            
            try:
                err_msg = response.json().get("detail", response.text)
            except:
                err_msg = response.text
            return False, f"កំហុសពី Server ({response.status_code}): {err_msg}"
        except Exception as e:
            print("Error API Add Menu:", e)
            return False, f"សូមរង់ចាំបន្តិច ហើយសាកល្បងម្តងទៀត (Network Timeout):\n{str(e)}"

    @staticmethod
    def update_menu_item(item_id, name, price, image_url=""):
        try:
            response = session.put(f"{API_BASE_URL}/menu/{item_id}", json={
                "name": name,
                "price": float(price),
                "image_url": image_url
            }, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"Error API Update Menu: {e}")
            return False

    @staticmethod
    def delete_menu_item(item_id):
        try:
            response = session.delete(f"{API_BASE_URL}/menu/{item_id}", timeout=15)
            return response.status_code == 200
        except Exception as e:
            print("Error API Delete Menu:", e)
            return False

    @staticmethod
    def get_users():
        try:
            response = session.get(f"{API_BASE_URL}/users", timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print("Error API Users:", e)
        return []

    @staticmethod
    def add_user(data):
        try:
            response = session.post(f"{API_BASE_URL}/users", json=data, timeout=15)
            return response.status_code == 200
        except Exception as e:
            print("Error API Add User:", e)
            return False

    @staticmethod
    def delete_user(user_id):
        try:
            response = session.delete(f"{API_BASE_URL}/users/{user_id}", timeout=15)
            return response.status_code == 200
        except Exception as e:
            print("Error API Delete User:", e)
            return False

    @staticmethod
    def get_crm_messages():
        try:
            res = session.get(f"{API_BASE_URL}/crm/messages", timeout=10)
            if res.status_code == 200: return res.json()
        except: pass
        return []

    @staticmethod
    def send_crm_reply(chat_id, text):
        try:
            res = session.post(f"{API_BASE_URL}/crm/reply", json={"chat_id": chat_id, "user": "Admin", "text": text}, timeout=15)
            return res.status_code == 200
        except: return False

    @staticmethod
    def send_broadcast(target, text):
        try:
            res = session.post(f"{API_BASE_URL}/broadcast", json={"target": target, "text": text}, timeout=30)
            return res.json() if res.status_code == 200 else None
        except: return None

    @staticmethod
    def get_app_config():
        try:
            res = session.get(f"{API_BASE_URL}/config", timeout=15)
            if res.status_code == 200: return res.json()
        except: pass
        return {"banner_url": "", "is_open": True, "aba_name": "HEM SINATH", "aba_number": "086599789", "kitchen_group_id": "", "reward_points": 50, "reward_discount": 5.0}

    @staticmethod
    def update_app_config(banner_url, is_open, aba_name, aba_number, kitchen_group_id, reward_points, reward_discount):
        try:
            res = session.post(f"{API_BASE_URL}/config", json={"banner_url": banner_url, "is_open": is_open, "aba_name": aba_name, "aba_number": aba_number, "kitchen_group_id": kitchen_group_id, "reward_points": reward_points, "reward_discount": reward_discount}, timeout=15)
            return res.status_code == 200
        except: return False

    @staticmethod
    def upload_image(file_path):
        url = f"{API_BASE_URL}/upload"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                # ប្រើ verify=False និង Header ដើម្បីរំលងបញ្ហា SSLEOFError 
                response = requests.post(url, files=files, headers=headers, verify=False, timeout=30)
                
                if response.status_code == 200:
                    return response.json().get("image_url")
                else:
                    print("Upload failed with status:", response.status_code, response.text)
                    return None
        except Exception as e:
            print("Error uploading image:", e)
            return None
