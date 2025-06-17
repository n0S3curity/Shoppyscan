from flask import Flask, jsonify, render_template, request, redirect, url_for
import data_manager  # Import the new data_manager module
import json
import logging
import os  # Import os module to create directories
from datetime import datetime, timedelta  # Import datetime and timedelta for log parsing and initial log generation

app = Flask(__name__)

# --- Logging Setup ---
# Ensure log directories exist
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Define log file paths based on the logging setup for consistency
SERVER_LOG_FILE_PATH = os.path.join(log_dir, 'server_logs.txt')
SCANNER_LOG_FILE_PATH = os.path.join(log_dir, 'scanner_logs.txt')

# Server Logger
server_logger = logging.getLogger('server_logs')
server_logger.setLevel(logging.INFO)
# --- IMPORTANT CHANGE: Specify encoding='utf-8' for FileHandler ---
server_handler = logging.FileHandler(SERVER_LOG_FILE_PATH, encoding='utf-8')
server_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
server_handler.setFormatter(server_formatter)
# Ensure handlers are not duplicated if the app is reloaded (e.g., with debug=True)
if not server_logger.handlers:
    server_logger.addHandler(server_handler)

# Scanner Logger
scanner_logger = logging.getLogger('scanner_logs')
scanner_logger.setLevel(logging.INFO)
# --- IMPORTANT CHANGE: Specify encoding='utf-8' for FileHandler ---
scanner_handler = logging.FileHandler(SCANNER_LOG_FILE_PATH, encoding='utf-8')
scanner_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
scanner_handler.setFormatter(scanner_formatter)
# Ensure handlers are not duplicated
if not scanner_logger.handlers:
    scanner_logger.addHandler(scanner_handler)


def read_logs_from_file(file_path):
    """
    Reads log entries from a specified file, parses them, and returns them
    as a list of dictionaries, sorted by timestamp (latest first).
    Assumes log format from logging.Formatter: "YYYY-MM-DD HH:MM:SS,ms - LEVELNAME - Message"
    """
    logs = []
    if not os.path.exists(file_path):
        # Using print here as the loggers might not be fully available for this specific error check
        print(f"Warning: Log file not found at {file_path}")
        return []

    try:
        # --- IMPORTANT: Ensure reading with utf-8 encoding as well ---
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    # Expected format example: "2025-06-16 23:42:15,123 - INFO - Server started."
                    # Split into three main parts: timestamp, level, message
                    parts = line.split(' - ', 2)
                    if len(parts) == 3:
                        timestamp_str_with_ms = parts[0]
                        level = parts[1].lower()  # Convert to lowercase for CSS consistency
                        message = parts[2]

                        # Parse timestamp with milliseconds
                        timestamp_obj = datetime.strptime(timestamp_str_with_ms, "%Y-%m-%d %H:%M:%S,%f")

                        logs.append({
                            "timestamp": timestamp_str_with_ms,  # Keep original string for display
                            "level": level,
                            "message": message
                        })
                    else:
                        print(f"Warning: Malformed log line (expected 3 parts separated by ' - '): '{line}'")
                except ValueError as e:
                    print(f"Warning: Could not parse log line timestamp or format: '{line}' - Error: {e}")
                except Exception as e:
                    print(f"Warning: Unexpected error processing log line: '{line}' - Error: {e}")

    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

    # Sort logs by the parsed datetime object in descending order (latest first)
    return sorted(logs, key=lambda x: datetime.strptime(x['timestamp'], "%Y-%m-%d %H:%M:%S,%f"), reverse=True)


def create_initial_logs_if_empty():
    """
    Writes a few initial log entries using the configured loggers
    if the respective log files are empty. This provides immediate content.
    Includes Hebrew characters for testing.
    """

    # Check if the file exists and is empty or has only whitespace
    def is_file_empty(file_path):
        return not os.path.exists(file_path) or os.path.getsize(file_path) == 0 or all(
            line.isspace() for line in open(file_path, 'r', encoding='utf-8'))

    if is_file_empty(SERVER_LOG_FILE_PATH):
        server_logger.info('Initial server log: יישום הופעל בהצלחה (Application started successfully).')
        server_logger.warning('Initial server log: בודק תקינות מערכת (Checking system health).')
        server_logger.debug('Initial server log: מצב איתור באגים פעיל (Debug mode active).')

    if is_file_empty(SCANNER_LOG_FILE_PATH):
        scanner_logger.info('Initial scanner log: מודול הסריקה הופעל (Scanner module initialized).')
        scanner_logger.debug('Initial scanner log: מבצע בדיקה עצמית מהירה (Performing quick self-test).')


# --- Routes for serving HTML pages ---

@app.route('/')
def index():
    server_logger.info('Accessed index page.')
    return render_template('dash.html')


@app.route('/test')
def test():
    server_logger.info('Accessed test endpoint.')
    return jsonify({"response": "success!"})


@app.route('/products')
def products_page():
    server_logger.info('Accessed products page.')
    return render_template('products.html')


@app.route('/tracking')
def tracking_page():
    product_name = request.args.get('name')
    barcode = request.args.get('barcode')

    if barcode:
        server_logger.info(f'Accessed tracking page for product: {product_name} (Barcode: {barcode}).')
        return render_template('tracking.html', show_details=True, product_name=product_name, barcode=barcode)
    else:
        server_logger.info('Accessed general tracking page (no specific barcode provided).')
        return render_template('tracking.html', show_details=False)


@app.route('/scan', methods=['POST'])
def scan_barcode():
    payload = request.json
    barcode = payload.get('barcode')
    if barcode:
        scanner_logger.info(f"Scanned barcode via '/scan' endpoint: {barcode}")
        return jsonify({"success": True, "message": "Barcode logged"}), 200
    scanner_logger.error("Failed to log barcode via '/scan' endpoint: No barcode provided.")
    return jsonify({"error": "No barcode provided"}), 400


# --- API Endpoints SCANNER---

@app.route('/api/scanner/add_product', methods=['POST'])
def scanner_add_product():
    payload = request.json
    barcode = payload.get('barcode')

    if not barcode:
        scanner_logger.error("Failed to add product (scanner): Barcode is missing in payload.")
        return jsonify({"success": False, "error": "Barcode is missing"}), 400

    try:
        product_name_from_master, product_details_from_master = data_manager.get_product_from_master_by_barcode(barcode)

        if product_details_from_master:
            name = product_name_from_master
            category = product_details_from_master.get('category', 'לא מקוטלג')
            quantity = 1

            data_manager.add_shopping_item(name, quantity, category, barcode)
            scanner_logger.info(f"Product '{name}' (barcode: {barcode}) added/updated in shopping list by scanner.")
            return jsonify({"success": True, "message": f"Product '{name}' added/updated in shopping list."})
        else:
            default_name = f"מוצר חדש נסרק באמצעות ברקוד: {barcode}"
            default_category = "לא מקוטלג"

            success_master_add = data_manager.add_product_to_master(default_name, barcode, default_category)

            if not success_master_add:
                scanner_logger.error(
                    f"Failed to add new product '{default_name}' (barcode: {barcode}) to master list by scanner.")
                return jsonify({"success": False, "error": "Failed to add new product to master list."}), 500

            data_manager.add_shopping_item(default_name, 1, default_category, barcode)
            scanner_logger.info(
                f"New product '{default_name}' (barcode: {barcode}) added to master and shopping list by scanner.")
            return jsonify(
                {"success": True, "message": f"New product '{default_name}' added to master and shopping list."})
    except Exception as e:
        scanner_logger.error(f"Error in scanner_add_product for barcode {barcode}: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/scanner/log', methods=['POST'])
def scanner_log():
    payload = request.json
    content = payload.get('content')
    print("content: ", content)

    if not content:
        scanner_logger.error("Failed to log scanner content: No content provided.")
        return jsonify({"success": False, "error": "Content is missing"}), 400
    try:
        scanner_logger.info(f"Scanner custom log: {content}")
        return jsonify({"success": True, "message": "Content logged by scanner."}), 200
    except Exception as e:
        scanner_logger.error(f"Error logging scanner content: {content}. Error: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"An unexpected error occurred: {e}"}), 500


# --- API Endpoints ---

@app.route('/api/shoppinglist')
def get_shopping_list():
    try:
        data = data_manager.get_all_shopping_items()
        server_logger.info("Successfully retrieved shopping list.")
        return jsonify(data)
    except Exception as e:
        server_logger.error(f"Failed to retrieve shopping list: {e}", exc_info=True)
        return jsonify({"error": f"Failed to retrieve shopping list: {e}"}), 500


@app.route('/api/add_product', methods=['POST'])
def add_product():
    payload = request.json
    name = payload.get('name')
    quantity = int(payload.get('quantity', 1))
    category = payload.get('category')
    barcode = payload.get('barcode', '').strip()

    if not name or not category:
        server_logger.error(f"Failed to add product: Missing product name ({name}) or category ({category}).")
        return jsonify({"error": "Missing product name or category"}), 400

    try:
        data_manager.add_category_if_not_exists(category)
        success = data_manager.add_shopping_item(name, quantity, category, barcode)

        if success:
            server_logger.info(
                f"Product '{name}' (Quantity: {quantity}, Category: {category}, Barcode: {barcode}) added/updated successfully.")
            return jsonify({"success": True, "message": "Product added/updated successfully"})
        else:
            server_logger.error(
                f"Failed to add/update product '{name}' (Quantity: {quantity}, Category: {category}, Barcode: {barcode}).")
            return jsonify({"error": "Failed to add/update product"}), 500
    except Exception as e:
        server_logger.error(f"Error adding product '{name}': {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/update_product', methods=['POST'])
def update_product():
    payload = request.json
    name = payload.get('name')

    if not name:
        server_logger.error("Failed to update product: Missing product name.")
        return jsonify({"error": "Missing product name"}), 400

    try:
        # Handle quantity update
        if 'quantity' in payload:
            quantity = payload.get('quantity')
            success = data_manager.update_shopping_item(name, quantity=quantity)
            if not success:
                server_logger.error(f"Failed to update quantity for product '{name}'. Product not found.")
                return jsonify({"error": "Product not found or failed to update quantity"}), 404
            server_logger.info(f"Product '{name}' quantity updated to {quantity}.")
            return jsonify({"success": True, "message": "Product quantity updated"})

        # Handle done status update (and potential price recording)
        if 'done' in payload:
            done_status = payload.get('done')
            price = payload.get('price')

            success = data_manager.update_shopping_item(name, done=done_status)
            if not success:
                server_logger.error(f"Failed to update done status for product '{name}'. Product not found.")
                return jsonify({"error": "Product not found or failed to update status"}), 404

            shopping_data = data_manager.get_all_shopping_items()
            product_in_shopping = shopping_data['products'].get(name)

            if product_in_shopping and product_in_shopping.get('barcode'):
                barcode_for_tracking = product_in_shopping['barcode']
                if done_status and price is not None and price != "":
                    data_manager.record_product_price_entry(name, barcode_for_tracking, price)
                    server_logger.info(
                        f"Product '{name}' marked as done and price '{price}' recorded (Barcode: {barcode_for_tracking}).")
                    return jsonify({"success": True, "message": "Product status and price updated"})
                elif done_status:
                    server_logger.info(f"Product '{name}' marked as done (no price provided).")
                    return jsonify({"success": True, "message": "Product status updated"})
                elif not done_status:
                    server_logger.info(f"Product '{name}' marked as undone.")
                    return jsonify({"success": True, "message": "Product status updated"})
            else:
                server_logger.warning(f"Product '{name}' status updated, but barcode not found for tracking.")
                return jsonify(
                    {"success": True, "message": "Product status updated, but barcode not found for tracking"}), 200

        server_logger.error(f"Failed to update product '{name}': No valid update operation specified.")
        return jsonify({"error": "No valid update operation specified"}), 400
    except Exception as e:
        server_logger.error(f"Error updating product '{name}': {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/delete_product', methods=['POST'])
def delete_product():
    payload = request.json
    name = payload.get('name')
    if not name:
        server_logger.error("Failed to delete product: Missing product name.")
        return jsonify({"error": "Missing product name"}), 400

    try:
        success = data_manager.delete_shopping_item(name)
        if success:
            server_logger.info(f"Product '{name}' deleted successfully from shopping list.")
            return jsonify({"success": True, "message": "Product deleted successfully"})
        else:
            server_logger.error(f"Failed to delete product '{name}' from shopping list. Product not found.")
            return jsonify({"error": "Product not found or failed to delete"}), 404
    except Exception as e:
        server_logger.error(f"Error deleting product '{name}': {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/clear_done_products', methods=['POST'])
def clear_done_products():
    try:
        success = data_manager.clear_done_shopping_items()
        if success:
            server_logger.info("Successfully cleared all done products from shopping list.")
            return jsonify({"success": True, "message": "Done products cleared successfully"})
        else:
            server_logger.error("Failed to clear done products.")
            return jsonify({"error": "Failed to clear done products"}), 500
    except Exception as e:
        server_logger.error(f"Error clearing done products: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/product_tracking')
def get_product_tracking():
    barcode = request.args.get('barcode')
    product_name_from_url = request.args.get('name')

    if not barcode:
        server_logger.error("Failed to get product tracking: Barcode not provided.")
        return jsonify({"error": "Barcode not provided"}), 400

    try:
        product_master_name, product_details_from_master = data_manager.get_product_from_master_by_barcode(barcode)

        if not product_details_from_master and product_name_from_url:
            product_master_name, product_details_from_master = data_manager.get_product_from_master_by_name(
                product_name_from_url)
            if product_details_from_master and not product_details_from_master.get('barcode') and barcode:
                products_master_data = data_manager._load_db(data_manager.PRODUCTS_MASTER_DB)
                products_master_data['products'][product_master_name]['barcode'] = barcode
                data_manager._save_db(data_manager.PRODUCTS_MASTER_DB, products_master_data)
                product_details_from_master['barcode'] = barcode
                server_logger.info(
                    f"Updated barcode for product '{product_master_name}' in master list to '{barcode}'.")

        display_name = product_master_name if product_master_name else product_name_from_url if product_name_from_url else 'שם לא ידוע'

        if not product_details_from_master or not product_details_from_master.get('barcode'):
            server_logger.error(
                f"Product with barcode '{barcode}' not found or has no associated barcode for tracking.")
            return jsonify({"error": "Product not found or has no associated barcode for tracking"}), 404

        tracking_history, name_from_tracking_db = data_manager.get_tracking_history_by_barcode(barcode)

        final_display_name = name_from_tracking_db if name_from_tracking_db != 'שם לא ידוע' else display_name
        server_logger.info(
            f"Successfully retrieved tracking history for product '{final_display_name}' (Barcode: {barcode}).")
        return jsonify({
            "tracking": tracking_history,
            "name": final_display_name,
            "barcode": barcode
        })
    except Exception as e:
        server_logger.error(f"Error retrieving product tracking for barcode '{barcode}': {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/record_product_price', methods=['POST'])
def record_product_price():
    payload = request.json
    barcode = payload.get('barcode')
    price = payload.get('price')

    if not all([barcode, price is not None]):
        server_logger.error("Failed to record product price: Missing barcode or price.")
        return jsonify({"error": "Missing barcode or price"}), 400

    try:
        product_name, product_details = data_manager.get_product_from_master_by_barcode(barcode)
        if not product_details:
            server_logger.error(f"Failed to record price for barcode '{barcode}': Product not found in master list.")
            return jsonify({"error": "Product not found with this barcode in master list"}), 404

        success = data_manager.record_product_price_entry(product_name, barcode, price)
        if success:
            server_logger.info(
                f"Price '{price}' recorded successfully for product '{product_name}' (Barcode: {barcode}).")
            return jsonify({"success": True, "message": "Price recorded successfully"})
        else:
            server_logger.error(f"Failed to record price '{price}' for product '{product_name}' (Barcode: {barcode}).")
            return jsonify({"error": "Failed to record price"}), 500
    except Exception as e:
        server_logger.error(f"Error recording product price for barcode '{barcode}': {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/all_products')
def get_all_products():
    try:
        products_data = data_manager.get_all_products_from_master()
        server_logger.info("Successfully retrieved all products from master list.")
        return jsonify(products_data)
    except Exception as e:
        server_logger.error(f"Failed to retrieve all products from master list: {e}", exc_info=True)
        return jsonify({"error": f"Failed to retrieve all products: {e}"}), 500


@app.route('/api/delete_master_product', methods=['POST'])
def delete_master_product():
    payload = request.json
    name = payload.get('name')
    if not name:
        server_logger.error("Failed to delete master product: Missing product name.")
        return jsonify({"error": "Missing product name"}), 400

    try:
        success = data_manager.delete_product_from_master(name)
        if success:
            server_logger.info(f"Product '{name}' deleted successfully from master list.")
            return jsonify({"success": True, "message": "Product deleted from master successfully"})
        else:
            server_logger.error(f"Failed to delete product '{name}' from master list. Product not found.")
            return jsonify({"error": "Product not found in master list"}), 404
    except Exception as e:
        server_logger.error(f"Error deleting master product '{name}': {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/update_master_product', methods=['POST'])
def update_master_product():
    payload = request.json
    old_name = payload.get('old_name')
    new_name = payload.get('new_name')
    new_category = payload.get('new_category', '').strip()
    new_barcode = payload.get('new_barcode', '').strip()

    if not old_name or not new_name or not new_category:
        server_logger.error(f"Failed to update master product: Missing old name ({old_name}) or new name ({new_name}) or new category ({new_category}).")
        return jsonify({"error": "Missing old or new product name"}), 400

    try:
        success = data_manager.update_product_in_master(old_name, new_name,new_category, new_barcode)
        if success:
            server_logger.info(f"Product '{old_name}' updated in master to '{new_name}' (Barcode: {new_barcode}).")
            return jsonify({"success": True, "message": "Product updated in master successfully"})
        else:
            server_logger.error(
                f"Failed to update product '{old_name}' in master list. Product not found or update failed.")
            return jsonify({"error": "Product not found or failed to update in master"}), 404
    except Exception as e:
        server_logger.error(f"Error updating master product '{old_name}': {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/process_scanned_barcode', methods=['POST'])
def process_scanned_barcode():
    payload = request.json
    print("Received payload for scanned barcode processing:", payload)
    scanned_barcode = payload.get('barcode')
    category = payload.get('category', '').strip()
    product_name = payload.get('product_name')

    if not scanned_barcode:
        server_logger.error("Failed to process scanned barcode: Barcode is missing.")
        return jsonify({"success": False, "error": "Barcode is missing"}), 400

    try:
        existing_product_name, existing_product_details = data_manager.get_product_from_master_by_barcode(
            scanned_barcode)

        if existing_product_name:
            product = {
                "success": True,
                "exists": True,
                "product_name": existing_product_name,
                "category": existing_product_details.get('category', 'לא מקוטלג'),
                "barcode": scanned_barcode,
                "message": "Barcode already associated with an existing product."
            }
            server_logger.info(
                f"Processed scanned barcode '{scanned_barcode}': Found existing product '{existing_product_name}'.")
            return jsonify(product)
        else:
            if not product_name:
                server_logger.info(
                    f"Processed scanned barcode '{scanned_barcode}': Barcode is new, product name required to add.")
                return jsonify({
                    "success": True,
                    "exists": False,
                    "barcode": scanned_barcode,
                    "category": category,
                    "message": "Barcode is new. A product name is required to add it."
                })
            else:
                success = data_manager.add_product_to_master(product_name, scanned_barcode,category=category)
                if success:
                    server_logger.info(
                        f"Processed scanned barcode '{scanned_barcode}': New product '{product_name}' added to master.")
                    return jsonify({
                        "success": True,
                        "exists": False,
                        "product_name": product_name,
                        "category": category,
                        "barcode": scanned_barcode,
                        "message": "New product added successfully."
                    })
                else:
                    server_logger.error(
                        f"Failed to process scanned barcode '{scanned_barcode}': Failed to add new product '{product_name}'.")
                    return jsonify({"success": False, "error": "Failed to add new product."}), 500
    except Exception as e:
        server_logger.error(f"Error processing scanned barcode '{scanned_barcode}': {e}", exc_info=True)
        return jsonify({"success": False, "error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/categories')
def get_categories():
    try:
        categories_data = data_manager.get_all_categories()
        server_logger.info("Successfully retrieved all categories.")
        return jsonify({"categories": categories_data})
    except Exception as e:
        server_logger.error(f"Failed to retrieve categories: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/update_product_name_category', methods=['POST'])
def update_product_name_category():
    payload = request.json
    old_name = payload.get('old_name')
    new_name = payload.get('new_name')
    new_category = payload.get('new_category')
    barcode = str(payload.get('barcode', '')).strip()

    if not old_name or not new_name or not new_category:
        server_logger.error(
            f"Failed to update product name/category: Missing old name ({old_name}), new name ({new_name}), or new category ({new_category}).")
        return jsonify({"error": "Missing old name, new name, or new category"}), 400

    try:
        data_manager.add_category_if_not_exists(new_category)
        success = data_manager.update_product_name_and_category(old_name, new_name, new_category, barcode)
        if success:
            server_logger.info(
                f"Product '{old_name}' updated to new name '{new_name}' and category '{new_category}' (Barcode: {barcode}).")
            return jsonify({"success": True, "message": "Product name and category updated successfully."})
        else:
            server_logger.error(f"Failed to update product name/category for '{old_name}'.")
            return jsonify({"error": "Failed to update product name and category."}), 500
    except Exception as e:
        server_logger.error(f"Error updating product name/category for '{old_name}': {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


# --- HTML Rendering Routes for Logs (Existing) ---
@app.route('/logs/server')
def get_server_logs_page():
    """Renders the HTML page for server logs."""
    return render_template('server_logs.html', log_type='server')


@app.route('/logs/scanner')
def get_scanner_logs_page():
    """Renders the HTML page for scanner logs."""
    return render_template('scanner_logs.html', log_type='scanner')


# --- API Endpoints for Log Data (New) ---
@app.route('/api/logs/server')
def get_server_logs_json():
    """Reads server logs from file and returns as JSON."""
    logs = read_logs_from_file(SERVER_LOG_FILE_PATH)
    return jsonify(logs)


@app.route('/api/logs/scanner')
def get_scanner_logs_json():
    """Reads scanner logs from file and returns as JSON."""
    logs = read_logs_from_file(SCANNER_LOG_FILE_PATH)
    return jsonify(logs)


if __name__ == '__main__':
    # Call to write initial logs if files are empty
    create_initial_logs_if_empty()

    server_logger.info("Flask application starting...")
    app.run(debug=True, host="0.0.0.0", port=5000)
    server_logger.info("Flask application shut down.")
