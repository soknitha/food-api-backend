from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
from supabase import create_client, Client

app = FastAPI(title="Food E-Commerce API")

# ដាក់ Token របស់ Bot សម្រាប់ផ្ញើសារចេញពី Server ត្រឡប់ទៅអតិថិជនវិញ
BOT_TOKEN = "8704188082:AAEZmCT0yNJ9U3WNKte9E1SuJT0K4t4TOz0"

# ---------------- ការកំណត់ Supabase Database ---------------- #
SUPABASE_URL = os.getenv("SUPABASE_URL", "ដាក់_URL_SUPABASE_របស់អ្នកទីនេះ")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "ដាក់_KEY_SUPABASE_របស់អ្នកទីនេះ")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    USE_SUPABASE = True
except Exception as e:
    USE_SUPABASE = False

# ទិន្នន័យសាកល្បង (Mock Database ក្នុង Memory)
orders_db = [
    {"id": "#001", "customer": "សុខ សាន្ត", "items": "ភីហ្សា x1, កូកា x2", "total": "$15.50", "status": "កំពុងចម្អិន"},
    {"id": "#002", "customer": "ចាន់ ធី", "items": "បឺហ្គឺ x2", "total": "$8.00", "status": "កំពុងដឹកជញ្ជូន"}
]

menu_db = [
    {"id": 1, "name": "ភីហ្សា (Pizza)", "price": 8.50},
    {"id": 2, "name": "បឺហ្គឺ (Burger)", "price": 4.00}
]
menu_id_counter = 3

users_db = [
    {"id": 1, "name": "សុខ សាន្ត", "phone": "012345678", "points": 150},
    {"id": 2, "name": "ចាន់ ធី", "phone": "098765432", "points": 45}
]
user_id_counter = 3

class MenuItem(BaseModel):
    name: str
    price: float
    image_url: str = ""

class UserItem(BaseModel):
    name: str
    phone: str

class OrderCreate(BaseModel):
    customer: str
    items: str
    total: str
    status: str = "ថ្មី (រង់ចាំការបញ្ជាក់)"
    chat_id: str = ""

class OrderStatusUpdate(BaseModel):
    order_id: str
    status: str

class OrderReceipt(BaseModel):
    chat_id: str
    image_url: str

@app.get("/api/orders")
def get_orders():
    if USE_SUPABASE:
        response = supabase.table("orders").select("*").execute()
        return response.data
    return orders_db

@app.post("/api/orders")
def create_order(order: OrderCreate):
    import random
    new_order = {
        "id": f"#{random.randint(1000, 9999)}",
        "customer": order.customer,
        "items": order.items,
        "total": order.total,
        "status": order.status,
        "chat_id": order.chat_id,
        "receipt_url": ""
    }
    if USE_SUPABASE:
        response = supabase.table("orders").insert(new_order).execute()
        return response.data[0]
    orders_db.append(new_order)
    return new_order

@app.put("/api/orders/status")
def update_order_status(status_update: OrderStatusUpdate):
    if USE_SUPABASE:
        response = supabase.table("orders").update({"status": status_update.status}).eq("id", status_update.order_id).execute()
        if response.data:
            order = response.data[0]
            
            if order.get("chat_id"):
                msg_text = f"🔔 **ជម្រាបសួរ {order['customer']}**\nការកុម្ម៉ង់លេខ {order['id']} របស់អ្នកត្រូវបានប្តូរស្ថានភាពទៅជា៖ **{status_update.status}**"
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={"chat_id": order["chat_id"], "text": msg_text, "parse_mode": "Markdown"}
                )
            return {"message": "Status updated successfully", "order": order}
        return {"error": "Order not found"}

    for order in orders_db:
        if order["id"] == status_update.order_id:
            order["status"] = status_update.status
            
            # បាញ់សារទៅប្រាប់អតិថិជនតាម Telegram ពេល Admin ប្តូរស្ថានភាព
            if order.get("chat_id"):
                msg_text = f"🔔 **ជម្រាបសួរ {order['customer']}**\nការកុម្ម៉ង់លេខ {order['id']} របស់អ្នកត្រូវបានប្តូរស្ថានភាពទៅជា៖ **{status_update.status}**"
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={"chat_id": order["chat_id"], "text": msg_text, "parse_mode": "Markdown"}
                )
            return {"message": "Status updated successfully", "order": order}
    return {"error": "Order not found"}

@app.post("/api/orders/receipt")
def upload_receipt(data: OrderReceipt):
    if USE_SUPABASE:
        res = supabase.table("orders").select("*").eq("chat_id", data.chat_id).eq("status", "ថ្មី (រង់ចាំការបញ្ជាក់)").execute()
        if res.data:
            order_id = res.data[-1]['id'] # យករកការកុម្ម៉ង់ចុងក្រោយគេ
            supabase.table("orders").update({"receipt_url": data.image_url}).eq("id", order_id).execute()
            return {"message": "Receipt saved", "order_id": order_id}
        return {"error": "No pending order found"}
    else:
        for order in reversed(orders_db):
            if order.get("chat_id") == data.chat_id and order.get("status") == "ថ្មី (រង់ចាំការបញ្ជាក់)":
                order["receipt_url"] = data.image_url
                return {"message": "Receipt saved", "order_id": order["id"]}
        return {"error": "No pending order found"}

@app.get("/api/menu")
def get_menu():
    if USE_SUPABASE:
        response = supabase.table("menu").select("*").execute()
        return response.data
    return menu_db

@app.post("/api/menu")
def add_menu(item: MenuItem):
    if USE_SUPABASE:
        try:
            response = supabase.table("menu").insert({"name": item.name, "price": item.price, "image_url": item.image_url}).execute()
            return response.data[0] if response.data else {"id": 0, "name": item.name, "price": item.price}
        except Exception as e:
                raise HTTPException(status_code=400, detail=f"Supabase Error: {str(e)}")
    global menu_id_counter
    new_item = {"id": menu_id_counter, "name": item.name, "price": item.price, "image_url": item.image_url}
    menu_db.append(new_item)
    menu_id_counter += 1
    return new_item

@app.delete("/api/menu/{item_id}")
def delete_menu(item_id: int):
    if USE_SUPABASE:
        supabase.table("menu").delete().eq("id", item_id).execute()
        return {"message": "Item deleted successfully"}
    global menu_db
    menu_db = [item for item in menu_db if item["id"] != item_id]
    return {"message": "Item deleted successfully"}

@app.get("/api/users")
def get_users():
    if USE_SUPABASE:
        response = supabase.table("users").select("*").execute()
        return response.data
    return users_db

@app.post("/api/users")
def add_user(user: UserItem):
    if USE_SUPABASE:
        response = supabase.table("users").insert({"name": user.name, "phone": user.phone, "points": 0}).execute()
        return response.data[0]
    global user_id_counter
    new_user = {"id": user_id_counter, "name": user.name, "phone": user.phone, "points": 0}
    users_db.append(new_user)
    user_id_counter += 1
    return new_user

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    if USE_SUPABASE:
        supabase.table("users").delete().eq("id", user_id).execute()
        return {"message": "User deleted successfully"}
    global users_db
    users_db = [user for user in users_db if user["id"] != user_id]
    return {"message": "User deleted successfully"}