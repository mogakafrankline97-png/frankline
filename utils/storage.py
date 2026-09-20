import json
import os

from config import Config


def load_json_data(data_file=None):
    data_file = data_file or Config.DATA_FILE
    try:
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as handle:
                return json.load(handle)
    except Exception as exc:
        print(f'Error loading JSON: {exc}')
    return {'products': [], 'orders': [], 'order_queue': []}


def save_json_data(data, data_file=None):
    data_file = data_file or Config.DATA_FILE
    try:
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        with open(data_file, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, indent=2, default=str)
        return True
    except Exception as exc:
        print(f'Error saving JSON: {exc}')
        return False
