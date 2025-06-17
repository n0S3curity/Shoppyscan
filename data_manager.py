import json
import os
from datetime import datetime
import logging  # Import logging module

# Define paths for the new database files
SHOPPING_ITEMS_DB = 'databases/shopping_items.json'
PRODUCTS_MASTER_DB = 'databases/products_master.json'
TRACKING_DATA_DB = 'databases/tracking_data.json'
CATEGORIES_DB = 'databases/categories.json'

# Ensure the databases directory exists
if not os.path.exists('databases'):
    os.makedirs('databases')

# --- Logging Setup for Data Manager ---
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

data_manager_logger = logging.getLogger('data_manager_logs')
data_manager_logger.setLevel(logging.INFO)
data_manager_handler = logging.FileHandler(os.path.join(log_dir, 'data_manager_logs.txt'))
data_manager_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
data_manager_handler.setFormatter(data_manager_formatter)
data_manager_logger.addHandler(data_manager_handler)


# Generic function to load data from a specified JSON file
def _load_db(db_path):
    try:
        if not os.path.exists(db_path) or os.stat(db_path).st_size == 0:
            initial_data = {}
            if db_path in [SHOPPING_ITEMS_DB, PRODUCTS_MASTER_DB, TRACKING_DATA_DB]:
                initial_data = {"products": {}}
            elif db_path == CATEGORIES_DB:
                initial_data = {"categories": []}
            _save_db(db_path, initial_data)
            data_manager_logger.info(f"Initialized empty database at {db_path}.")
            return initial_data
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            data_manager_logger.info(f"Successfully loaded data from {db_path}.")
            return data
    except json.JSONDecodeError as e:
        data_manager_logger.error(f"JSON decoding error in {db_path}: {e}. Reinitializing database.", exc_info=True)
        initial_data = {}
        if db_path in [SHOPPING_ITEMS_DB, PRODUCTS_MASTER_DB, TRACKING_DATA_DB]:
            initial_data = {"products": {}}
        elif db_path == CATEGORIES_DB:
            initial_data = {"categories": []}
        _save_db(db_path, initial_data)
        return initial_data
    except Exception as e:
        data_manager_logger.error(f"Error loading database from {db_path}: {e}", exc_info=True)
        return {"products": {}} if db_path in [SHOPPING_ITEMS_DB, PRODUCTS_MASTER_DB, TRACKING_DATA_DB] else {
            "categories": []}


# Generic function to save data to a specified JSON file
def _save_db(db_path, data):
    try:
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        data_manager_logger.info(f"Successfully saved data to {db_path}.")
        return True
    except Exception as e:
        data_manager_logger.error(f"Error saving data to {db_path}: {e}", exc_info=True)
        return False


# --- Categories DB Operations (NEW) ---

def get_all_categories():
    try:
        categories_data = _load_db(CATEGORIES_DB)
        categories = categories_data.get('categories', [])
        data_manager_logger.info("Retrieved all categories.")
        return categories
    except Exception as e:
        data_manager_logger.error(f"Error retrieving all categories: {e}", exc_info=True)
        return []


def add_category_if_not_exists(category_name):
    if not category_name:
        data_manager_logger.warning("Attempted to add an empty category name.")
        return False

    try:
        categories_data = _load_db(CATEGORIES_DB)
        categories_list = categories_data.get('categories', [])

        if category_name not in categories_list:
            categories_list.append(category_name)
            categories_list.sort()
            categories_data['categories'] = categories_list
            if _save_db(CATEGORIES_DB, categories_data):
                data_manager_logger.info(f"Category '{category_name}' added to categories database.")
                return True
            else:
                data_manager_logger.error(f"Failed to save categories after attempting to add '{category_name}'.")
                return False
        else:
            data_manager_logger.info(f"Category '{category_name}' already exists in categories database.")
            return True
    except Exception as e:
        data_manager_logger.error(f"Error adding category '{category_name}': {e}", exc_info=True)
        return False


# --- Shopping Items DB Operations ---

def get_all_shopping_items():
    try:
        data = _load_db(SHOPPING_ITEMS_DB)
        data_manager_logger.info("Retrieved all shopping items.")
        return data
    except Exception as e:
        data_manager_logger.error(f"Error retrieving all shopping items: {e}", exc_info=True)
        return {"products": {}}


def add_shopping_item(name, quantity, category, barcode):
    try:
        shopping_data = _load_db(SHOPPING_ITEMS_DB)

        if name in shopping_data['products']:
            shopping_data['products'][name]['quantity'] += quantity
            shopping_data['products'][name]['category'] = category
            shopping_data['products'][name]['barcode'] = barcode
            data_manager_logger.info(f"Updated shopping item '{name}' (quantity increased, category/barcode updated).")
        else:
            shopping_data['products'][name] = {
                'quantity': quantity,
                'category': category,
                'barcode': barcode,
                'done': False
            }
            data_manager_logger.info(f"Added new shopping item '{name}'.")

        _save_db(SHOPPING_ITEMS_DB, shopping_data)

        # Ensure products_master.json is updated with full details
        add_product_to_master(name, barcode, category)
        data_manager_logger.info(f"Product '{name}' details ensured in master list via shopping item add.")
        return True
    except Exception as e:
        data_manager_logger.error(f"Error adding shopping item '{name}': {e}", exc_info=True)
        return False


def update_shopping_item(name, quantity=None, done=None, category=None):
    try:
        shopping_data = _load_db(SHOPPING_ITEMS_DB)
        if name in shopping_data['products']:
            if quantity is not None:
                shopping_data['products'][name]['quantity'] = quantity
                data_manager_logger.info(f"Updated quantity for shopping item '{name}' to {quantity}.")
            if done is not None:
                shopping_data['products'][name]['done'] = done
                data_manager_logger.info(f"Updated done status for shopping item '{name}' to {done}.")
            if category is not None:
                shopping_data['products'][name]['category'] = category
                data_manager_logger.info(f"Updated category for shopping item '{name}' to '{category}'.")
            _save_db(SHOPPING_ITEMS_DB, shopping_data)
            return True
        else:
            data_manager_logger.warning(f"Attempted to update non-existent shopping item '{name}'.")
            return False
    except Exception as e:
        data_manager_logger.error(f"Error updating shopping item '{name}': {e}", exc_info=True)
        return False


def delete_shopping_item(name):
    try:
        shopping_data = _load_db(SHOPPING_ITEMS_DB)
        if name in shopping_data['products']:
            del shopping_data['products'][name]
            _save_db(SHOPPING_ITEMS_DB, shopping_data)
            data_manager_logger.info(f"Deleted shopping item '{name}'.")
            return True
        else:
            data_manager_logger.warning(f"Attempted to delete non-existent shopping item '{name}'.")
            return False
    except Exception as e:
        data_manager_logger.error(f"Error deleting shopping item '{name}': {e}", exc_info=True)
        return False


def clear_done_shopping_items():
    try:
        shopping_data = _load_db(SHOPPING_ITEMS_DB)
        products_to_keep = {name: details for name, details in shopping_data['products'].items() if
                            not details.get('done', False)}
        shopping_data['products'] = products_to_keep
        _save_db(SHOPPING_ITEMS_DB, shopping_data)
        data_manager_logger.info("Cleared all done shopping items.")
        return True
    except Exception as e:
        data_manager_logger.error(f"Error clearing done shopping items: {e}", exc_info=True)
        return False


# --- Products Master DB Operations ---

def get_product_from_master_by_barcode(barcode):
    try:
        products_master_data = _load_db(PRODUCTS_MASTER_DB)
        for name, details in products_master_data['products'].items():
            if details.get('barcode') == barcode and barcode:
                data_manager_logger.info(f"Found product '{name}' by barcode '{barcode}' in master list.")
                return name, details
        data_manager_logger.info(f"Product not found by barcode '{barcode}' in master list.")
        return None, None
    except Exception as e:
        data_manager_logger.error(f"Error getting product from master by barcode '{barcode}': {e}", exc_info=True)
        return None, None


def get_product_from_master_by_name(name_to_find):
    try:
        products_master_data = _load_db(PRODUCTS_MASTER_DB)
        for name, details in products_master_data['products'].items():
            if name == name_to_find:
                data_manager_logger.info(f"Found product '{name_to_find}' by name in master list.")
                return name, details
        data_manager_logger.info(f"Product '{name_to_find}' not found by name in master list.")
        return None, None
    except Exception as e:
        data_manager_logger.error(f"Error getting product from master by name '{name_to_find}': {e}", exc_info=True)
        return None, None


def get_all_products_from_master():
    try:
        products_master_data = _load_db(PRODUCTS_MASTER_DB)
        all_products = [{"name": name, "barcode": details.get("barcode", ""), "category": details.get("category", "")}
                        for name, details in products_master_data['products'].items()]
        data_manager_logger.info("Retrieved all products from master list.")
        return {"products": all_products}
    except Exception as e:
        data_manager_logger.error(f"Error retrieving all products from master: {e}", exc_info=True)
        return {"products": []}


def add_product_to_master(product_name, barcode, category=None):
    try:
        products_master_data = _load_db(PRODUCTS_MASTER_DB)

        if product_name in products_master_data['products']:
            master_product = products_master_data['products'][product_name]
            if barcode:
                master_product['barcode'] = barcode
            if category is not None:
                master_product['category'] = category
            data_manager_logger.info(
                f"Updated existing product '{product_name}' in master list (barcode: {barcode}, category: {category}).")
        else:
            products_master_data['products'][product_name] = {
                "barcode": barcode,
                "category": category if category is not None else ""
            }
            data_manager_logger.info(
                f"Added new product '{product_name}' to master list (barcode: {barcode}, category: {category}).")

        if _save_db(PRODUCTS_MASTER_DB, products_master_data):
            return True
        else:
            data_manager_logger.error(f"Failed to save product '{product_name}' to master database.")
            return False
    except Exception as e:
        data_manager_logger.error(f"Error adding/updating product '{product_name}' to master: {e}", exc_info=True)
        return False


def update_product_name_and_category(old_name, new_name, new_category, barcode):
    try:
        products_master_data = _load_db(PRODUCTS_MASTER_DB)
        shopping_data = _load_db(SHOPPING_ITEMS_DB)

        # 1. Update Products Master DB
        if old_name not in products_master_data['products']:
            data_manager_logger.error(
                f"Product '{old_name}' not found in master list for update_product_name_and_category.")
            return False

        if old_name == new_name:
            products_master_data['products'][old_name]['category'] = new_category
            if barcode:
                products_master_data['products'][old_name]['barcode'] = barcode
            data_manager_logger.info(f"Updated category/barcode for master product '{old_name}' (no name change).")
        else:
            old_master_details = products_master_data['products'].pop(old_name)

            if new_name in products_master_data['products']:
                data_manager_logger.error(
                    f"New product name '{new_name}' already exists in master list. Cannot rename '{old_name}'.")
                products_master_data['products'][old_name] = old_master_details  # Re-add to maintain state
                _save_db(PRODUCTS_MASTER_DB, products_master_data)  # Save previous state
                return False

            old_master_details['barcode'] = barcode if barcode else old_master_details.get('barcode', '')
            old_master_details['category'] = new_category
            products_master_data['products'][new_name] = old_master_details
            data_manager_logger.info(f"Renamed and updated master product from '{old_name}' to '{new_name}'.")

        _save_db(PRODUCTS_MASTER_DB, products_master_data)

        # 2. Update Shopping Items DB
        if old_name in shopping_data['products']:
            if old_name == new_name:
                shopping_data['products'][old_name]['category'] = new_category
                if barcode:
                    shopping_data['products'][old_name]['barcode'] = barcode
                data_manager_logger.info(f"Updated category/barcode for shopping item '{old_name}' (no name change).")
            else:
                old_shopping_details = shopping_data['products'].pop(old_name)
                old_shopping_details['category'] = new_category
                old_shopping_details['barcode'] = barcode if barcode else old_shopping_details.get('barcode', '')
                shopping_data['products'][new_name] = old_shopping_details
                data_manager_logger.info(f"Renamed and updated shopping item from '{old_name}' to '{new_name}'.")
            _save_db(SHOPPING_ITEMS_DB, shopping_data)
        else:
            data_manager_logger.warning(
                f"Product '{old_name}' not found in shopping list during update_product_name_and_category; master update proceeded.")

        data_manager_logger.info(
            f"Successfully updated product '{old_name}' to '{new_name}' with category '{new_category}'.")
        return True
    except Exception as e:
        data_manager_logger.error(f"Error updating product name and category for '{old_name}': {e}", exc_info=True)
        return False


# --- Tracking Data DB Operations ---

def record_product_price_entry(name, barcode, price):
    try:
        tracking_data_db = _load_db(TRACKING_DATA_DB)

        if barcode not in tracking_data_db['products']:
            tracking_data_db['products'][barcode] = {'name': name, 'tracking': {}}
            data_manager_logger.info(f"Initialized tracking for new barcode '{barcode}' with product name '{name}'.")
        else:
            tracking_data_db['products'][barcode]['name'] = name  # Update name in case it changed
            data_manager_logger.info(f"Updated name for existing tracking entry of barcode '{barcode}' to '{name}'.")

        current_date = datetime.now().strftime('%d/%m/%Y')
        tracking_data_db['products'][barcode]['tracking'][current_date] = {"price": float(price)}

        if _save_db(TRACKING_DATA_DB, tracking_data_db):
            data_manager_logger.info(
                f"Recorded price '{price}' for product '{name}' (barcode: {barcode}) on {current_date}.")
            return True
        else:
            data_manager_logger.error(f"Failed to save price record for product '{name}' (barcode: {barcode}).")
            return False
    except Exception as e:
        data_manager_logger.error(f"Error recording product price entry for '{name}' (barcode: {barcode}): {e}",
                                  exc_info=True)
        return False


def get_tracking_history_by_barcode(barcode):
    try:
        tracking_data_db = _load_db(TRACKING_DATA_DB)
        product_tracking_info = tracking_data_db['products'].get(barcode, {})

        if 'tracking' in product_tracking_info:
            sorted_tracking = sorted(product_tracking_info['tracking'].items(),
                                     key=lambda item: datetime.strptime(item[0], '%d/%m/%Y'))
            name_from_tracking = product_tracking_info.get('name', 'שם לא ידוע')
            data_manager_logger.info(f"Retrieved tracking history for barcode '{barcode}'.")
            return sorted_tracking, name_from_tracking
        else:
            data_manager_logger.info(f"No tracking history found for barcode '{barcode}'.")
            return [], 'שם לא ידוע'
    except Exception as e:
        data_manager_logger.error(f"Error getting tracking history for barcode '{barcode}': {e}", exc_info=True)
        return [], 'שם לא ידוע'


# --- Products Master DB Operations (Existing functions) ---

def delete_product_from_master(name):
    try:
        products_master_data = _load_db(PRODUCTS_MASTER_DB)
        if name in products_master_data['products']:
            del products_master_data['products'][name]
            _save_db(PRODUCTS_MASTER_DB, products_master_data)
            data_manager_logger.info(f"Deleted product '{name}' from master list.")
            return True
        else:
            data_manager_logger.warning(f"Attempted to delete non-existent product '{name}' from master list.")
            return False
    except Exception as e:
        data_manager_logger.error(f"Error deleting product '{name}' from master list: {e}", exc_info=True)
        return False


def update_product_in_master(old_name, new_name, new_category, new_barcode):
    try:
        products_master_data = _load_db(PRODUCTS_MASTER_DB)

        if old_name not in products_master_data['products']:
            data_manager_logger.error(f"Product '{old_name}' not found in master list for update_product_in_master.")
            return False

        # Get current data for the product before any changes
        current_product_data = products_master_data['products'][old_name]
        current_barcode = current_product_data.get('barcode', '')
        current_category = current_product_data.get('category', '')

        # Determine the barcode to use for the updated product
        barcode_to_use = new_barcode if new_barcode else current_barcode

        # Determine the category to use for the updated product
        # If new_category is provided, use it; otherwise, retain the current category
        category_to_use = new_category if new_category is not None else current_category


        if old_name != new_name:
            if new_name in products_master_data['products']:
                data_manager_logger.error(
                    f"New product name '{new_name}' already exists in master list. Cannot update '{old_name}'.")
                return False

            # Delete the old entry and add the new one with updated details
            del products_master_data['products'][old_name]
            products_master_data['products'][new_name] = {'barcode': barcode_to_use, 'category': category_to_use}
            data_manager_logger.info(
                f"Renamed master product from '{old_name}' to '{new_name}', updated barcode to '{barcode_to_use}', and category to '{category_to_use}'.")
        else:
            # If the name hasn't changed, just update barcode and category in place
            products_master_data['products'][new_name]['barcode'] = barcode_to_use
            products_master_data['products'][new_name]['category'] = category_to_use
            data_manager_logger.info(
                f"Updated barcode to '{barcode_to_use}' and category to '{category_to_use}' for master product '{new_name}'.")


        if _save_db(PRODUCTS_MASTER_DB, products_master_data):
            return True
        else:
            data_manager_logger.error(f"Failed to save updated product '{new_name}' to master database.")
            return False
    except Exception as e:
        data_manager_logger.error(f"Error updating product in master from '{old_name}': {e}", exc_info=True)
        return False
