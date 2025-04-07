import json
import os

STORAGE_FILE = "invite_message.json"

def save_invite_message_id(message_id: int):
    with open(STORAGE_FILE, "w") as f:
        json.dump({"message_id": message_id}, f)

def load_invite_message_id():
    if not os.path.exists(STORAGE_FILE):
        return None
    with open(STORAGE_FILE, "r") as f:
        data = json.load(f)
        return data.get("message_id")
