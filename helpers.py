import os
import json


DB_FILE = 'databases/db.json'


# Load shopping list data from JSON
def load_data():
    if not os.path.exists(DB_FILE) or os.stat(DB_FILE).st_size == 0:
        return {"products": {}, "total": 0}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # Handle empty or malformed JSON gracefully
            return {"products": {}, "total": 0}


# Save shopping list data to JSON
def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# Helper function to find a product by its barcode
def find_product_by_barcode(barcode_to_find):
    data = load_data()
    for product_name, details in data['products'].items():
        if details.get('barcode') == barcode_to_find and barcode_to_find:  # Ensure barcode is not empty string
            return product_name, details
    return None, None  # Return None if not found or barcode is empty


def save_tracking_data(data):
    pass

