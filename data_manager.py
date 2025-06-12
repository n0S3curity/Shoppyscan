import json
import os
from datetime import datetime

# Define paths for the new database files
SHOPPING_ITEMS_DB = 'databases/shopping_items.json'
PRODUCTS_MASTER_DB = 'databases/products_master.json'
TRACKING_DATA_DB = 'databases/tracking_data.json'

# Ensure the databases directory exists
if not os.path.exists('databases'):
    os.makedirs('databases')


# Generic function to load data from a specified JSON file
def _load_db(db_path):
    if not os.path.exists(db_path) or os.stat(db_path).st_size == 0:
        # Initialize with an empty structure if file doesn't exist or is empty
        _save_db(db_path, {"products": {}})  # Consistent structure for all dbs
        return {"products": {}}
    with open(db_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # Handle malformed JSON gracefully
            _save_db(db_path, {"products": {}})
            return {"products": {}}


# Generic function to save data to a specified JSON file
def _save_db(db_path, data):
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# --- Shopping Items DB Operations ---

def get_all_shopping_items():
    return _load_db(SHOPPING_ITEMS_DB)


def add_shopping_item(name, quantity, category, barcode):
    shopping_data = _load_db(SHOPPING_ITEMS_DB)
    products_master_data = _load_db(PRODUCTS_MASTER_DB)

    # Add/update in shopping_items.json
    if name in shopping_data['products']:
        shopping_data['products'][name]['quantity'] += quantity
        # Ensure category and barcode are consistent if updating existing shopping item
        shopping_data['products'][name]['category'] = category
        shopping_data['products'][name]['barcode'] = barcode
    else:
        shopping_data['products'][name] = {
            'quantity': quantity,
            'category': category,
            'barcode': barcode,
            'done': False
        }
    _save_db(SHOPPING_ITEMS_DB, shopping_data)

    # Add/update in products_master.json (only name and barcode)
    # Check if barcode exists in master, if not, add it
    product_exists_in_master = False
    # Iterate over products_master_data to check for existing barcode
    for p_name, p_details in products_master_data['products'].items():
        if p_details.get('barcode') == barcode and barcode:
            product_exists_in_master = True
            # If product name changed for an existing barcode, update the key in master
            if p_name != name:
                products_master_data['products'][name] = products_master_data['products'].pop(p_name)
            break

    # If the product name doesn't exist in master, or if the barcode is new (and not empty)
    # or if the existing product in master has an empty barcode and a new one is provided
    if name not in products_master_data['products'] or \
            (barcode and not product_exists_in_master) or \
            (barcode and name in products_master_data['products'] and not products_master_data['products'][name].get(
                'barcode')):
        products_master_data['products'][name] = {
            'barcode': barcode
        }
    _save_db(PRODUCTS_MASTER_DB, products_master_data)

    return True


def update_shopping_item(name, quantity=None, done=None):
    shopping_data = _load_db(SHOPPING_ITEMS_DB)
    if name in shopping_data['products']:
        if quantity is not None:
            shopping_data['products'][name]['quantity'] = quantity
        if done is not None:
            shopping_data['products'][name]['done'] = done
        _save_db(SHOPPING_ITEMS_DB, shopping_data)
        return True
    return False


def delete_shopping_item(name):
    shopping_data = _load_db(SHOPPING_ITEMS_DB)
    if name in shopping_data['products']:
        del shopping_data['products'][name]
        _save_db(SHOPPING_ITEMS_DB, shopping_data)
        return True
    return False


def clear_done_shopping_items():
    shopping_data = _load_db(SHOPPING_ITEMS_DB)
    products_to_keep = {}
    for name, details in shopping_data['products'].items():
        if not details.get('done', False):
            products_to_keep[name] = details
    shopping_data['products'] = products_to_keep
    _save_db(SHOPPING_ITEMS_DB, shopping_data)
    return True


# --- Products Master DB Operations ---
# Renamed from get_product_from_master_by_barcode for clarity,
# and simplified to return just the name if found, None otherwise.
def get_product_from_master_by_barcode(barcode):
    products_master_data = _load_db(PRODUCTS_MASTER_DB)
    for name, details in products_master_data['products'].items():
        if details.get('barcode') == barcode and barcode:
            return name, details  # Return name and details (which contains barcode)
    return None  # Return None if not found or barcode is empty/invalid

def get_product_from_master_by_name(name_to_find):
    products_master_data = _load_db(PRODUCTS_MASTER_DB)
    for name, details in products_master_data['products'].items():
        if name == name_to_find:
            return name, details
    return None, None


def get_all_products_from_master():
    products_master_data = _load_db(PRODUCTS_MASTER_DB)
    # Return a list of dictionaries with 'name' and 'barcode' for frontend suggestions
    all_products = []
    for name, details in products_master_data['products'].items():
        all_products.append({"name": name, "barcode": details.get("barcode", "")})
    return {"products": all_products}


# NEW: Function to add or update a product in the master list
def add_product_to_master(product_name, barcode):
    products_master_data = _load_db(PRODUCTS_MASTER_DB)

    # Check if a product with the exact name already exists (case-sensitive as keys)
    if product_name in products_master_data['products']:
        # If it exists, just update its barcode.
        products_master_data['products'][product_name]['barcode'] = barcode
        _save_db(PRODUCTS_MASTER_DB, products_master_data)
        return True
    else:
        # If the product name doesn't exist, add it as a new product.
        products_master_data['products'][product_name] = {"barcode": barcode}
        _save_db(PRODUCTS_MASTER_DB, products_master_data)
        return True
    return False # Should ideally not be reached


# --- Tracking Data DB Operations ---

def record_product_price_entry(name, barcode, price):
    tracking_data_db = _load_db(TRACKING_DATA_DB)

    # Ensure the barcode entry exists in tracking_data_db
    if barcode not in tracking_data_db['products']:
        tracking_data_db['products'][barcode] = {'name': name, 'tracking': {}}
    else:
        # Update the name in case it changed or was not set before
        tracking_data_db['products'][barcode]['name'] = name

    current_date = datetime.now().strftime('%d/%m/%Y')
    tracking_data_db['products'][barcode]['tracking'][current_date] = {"price": float(price)}
    _save_db(TRACKING_DATA_DB, tracking_data_db)
    return True


def get_tracking_history_by_barcode(barcode):
    tracking_data_db = _load_db(TRACKING_DATA_DB)
    product_tracking_info = tracking_data_db['products'].get(barcode, {})

    if 'tracking' in product_tracking_info:
        # Sort tracking data by date for chronological display
        sorted_tracking = sorted(product_tracking_info['tracking'].items(),
                                 key=lambda item: datetime.strptime(item[0], '%d/%m/%Y'))
        return sorted_tracking, product_tracking_info.get('name', 'שם לא ידוע')  # Return name from tracking DB
    return [], 'שם לא ידוע'  # Return empty list and default name if not found


# --- Products Master DB Operations (Existing functions) ---

def delete_product_from_master(name):
    products_master_data = _load_db(PRODUCTS_MASTER_DB)
    if name in products_master_data['products']:
        del products_master_data['products'][name]
        _save_db(PRODUCTS_MASTER_DB, products_master_data)
        return True
    return False


def update_product_in_master(old_name, new_name, new_barcode):
    products_master_data = _load_db(PRODUCTS_MASTER_DB)

    if old_name not in products_master_data['products']:
        return False  # Product not found

    # If the name itself is changing, delete old entry and add new
    if old_name != new_name:
        del products_master_data['products'][old_name]
        products_master_data['products'][new_name] = {'barcode': new_barcode}
    else:
        # Only update barcode if name is the same
        products_master_data['products'][new_name]['barcode'] = new_barcode

    _save_db(PRODUCTS_MASTER_DB, products_master_data)
    return True

