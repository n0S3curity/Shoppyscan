from flask import Flask, jsonify, render_template, request, redirect, url_for
import data_manager  # Import the new data_manager module
import json  # Keep json for potential direct manipulation if needed, though data_manager should handle most

app = Flask(__name__)


# --- Routes for serving HTML pages ---

@app.route('/')
def index():
    return render_template('dash.html')


@app.route('/test')
def test():
    return jsonify({"response":"success!"})



@app.route('/products') # This will be the new barcode scanning and product management page
def products_page():
    return render_template('products.html') # Use the new template directly


@app.route('/tracking')
def tracking_page():
    product_name = request.args.get('name')
    barcode = request.args.get('barcode')

    if barcode:
        # If barcode is provided, render the detailed tracking page
        return render_template('tracking.html', show_details=True, product_name=product_name, barcode=barcode)
    else:
        # If no barcode, redirect to the products list page
        return render_template('tracking.html', show_details=False)


@app.route('/scan', methods=['POST']) # New endpoint for logging scanned barcodes
def scan_barcode():
    payload = request.json
    barcode = payload.get('barcode')
    if barcode:
        print(f"Scanned barcode: {barcode}") # Log to server console for debugging
        return jsonify({"success": True, "message": "Barcode logged"}), 200
    return jsonify({"error": "No barcode provided"}), 400



# --- API Endpoints ---

@app.route('/api/shoppinglist')
def get_shopping_list():
    data = data_manager.get_all_shopping_items()
    return jsonify(data)


@app.route('/api/add_product', methods=['POST'])
def add_product():
    payload = request.json
    name = payload.get('name')
    quantity = int(payload.get('quantity', 1))
    category = payload.get('category')
    barcode = payload.get('barcode', '').strip()

    if not name or not category:
        return jsonify({"error": "Missing product name or category"}), 400

    success = data_manager.add_shopping_item(name, quantity, category, barcode)
    if success:
        return jsonify({"success": True, "message": "Product added/updated successfully"})
    return jsonify({"error": "Failed to add/update product"}), 500


@app.route('/api/update_product', methods=['POST'])
def update_product():
    payload = request.json
    name = payload.get('name')

    if not name:
        return jsonify({"error": "Missing product name"}), 400

    # Handle quantity update
    if 'quantity' in payload:
        quantity = payload.get('quantity')
        success = data_manager.update_shopping_item(name, quantity=quantity)
        if not success:
            return jsonify({"error": "Product not found or failed to update quantity"}), 404
        return jsonify({"success": True, "message": "Product quantity updated"})

    # Handle done status update (and potential price recording)
    if 'done' in payload:
        done_status = payload.get('done')
        price = payload.get('price')  # Price is optional when marking as done

        # First, update done status in shopping_items.json
        success = data_manager.update_shopping_item(name, done=done_status)
        if not success:
            return jsonify({"error": "Product not found or failed to update status"}), 404

        # If product is marked as done AND a price is provided, record it in tracking_data.json
        # Get the barcode from the shopping_items_db for the product being marked done
        shopping_data = data_manager.get_all_shopping_items()
        product_in_shopping = shopping_data['products'].get(name)

        if product_in_shopping and product_in_shopping.get('barcode'):
            barcode_for_tracking = product_in_shopping['barcode']
            if done_status and price is not None and price != "":  # Only record if done and price is provided
                data_manager.record_product_price_entry(name, barcode_for_tracking, price)  # Pass name here
                print("Product marked as done with price recorded:", name, barcode_for_tracking, price)
                return jsonify({"success": True, "message": "Product status and price updated"})
            elif done_status:  # If done but no price, just update status
                return jsonify({"success": True, "message": "Product status updated"})
            elif not done_status:  # If un-done, just update status
                return jsonify({"success": True, "message": "Product status updated"})
        else:
            return jsonify({"success": True,
                            "message": "Product status updated, but barcode not found for tracking"}), 200  # Still success, but inform

        return jsonify({"success": True, "message": "Product status updated"})  # Fallback, should be handled by above

    return jsonify({"error": "No valid update operation specified"}), 400


@app.route('/api/delete_product', methods=['POST'])
def delete_product():
    payload = request.json
    name = payload.get('name')
    if not name:
        return jsonify({"error": "Missing product name"}), 400

    success = data_manager.delete_shopping_item(name)
    if success:
        return jsonify({"success": True, "message": "Product deleted successfully"})
    return jsonify({"error": "Product not found or failed to delete"}), 404


@app.route('/api/clear_done_products', methods=['POST'])
def clear_done_products():
    success = data_manager.clear_done_shopping_items()
    if success:
        return jsonify({"success": True, "message": "Done products cleared successfully"})
    return jsonify({"error": "Failed to clear done products"}), 500  # Should ideally always succeed if called correctly


@app.route('/api/product_tracking')
def get_product_tracking():
    barcode = request.args.get('barcode')
    product_name_from_url = request.args.get('name')  # Get name from URL for fallback if barcode is new/not in master

    if not barcode:
        return jsonify({"error": "Barcode not provided"}), 400

    # Get product name and details from products_master by barcode first
    product_master_name, product_details_from_master = data_manager.get_product_from_master_by_barcode(barcode)

    # If not found by barcode in master, try by name (for older entries) and update barcode in master if available
    if not product_details_from_master and product_name_from_url:
        product_master_name, product_details_from_master = data_manager.get_product_from_master_by_name(
            product_name_from_url)
        if product_details_from_master and not product_details_from_master.get('barcode') and barcode:
            # If product found by name but has no barcode, and a barcode was passed, update its barcode in master
            products_master_data = data_manager._load_db(data_manager.PRODUCTS_MASTER_DB)
            products_master_data['products'][product_master_name]['barcode'] = barcode
            data_manager._save_db(data_manager.PRODUCTS_MASTER_DB, products_master_data)
            product_details_from_master['barcode'] = barcode  # Update in current dict too

    # Determine the name to use for display and for passing to tracking_data functions
    # Prioritize name from master DB, then URL, then default
    display_name = product_master_name if product_master_name else product_name_from_url if product_name_from_url else 'שם לא ידוע'

    if not product_details_from_master or not product_details_from_master.get(
            'barcode'):  # Ensure we have a barcode to track
        return jsonify({"error": "Product not found or has no associated barcode for tracking"}), 404

    tracking_history, name_from_tracking_db = data_manager.get_tracking_history_by_barcode(barcode)

    # If name is available from tracking DB, use it, otherwise use display_name
    final_display_name = name_from_tracking_db if name_from_tracking_db != 'שם לא ידוע' else display_name

    return jsonify({
        "tracking": tracking_history,
        "name": final_display_name,  # Use name from tracking DB if available, else from master/URL
        "barcode": barcode
    })


@app.route('/api/record_product_price', methods=['POST'])
def record_product_price():
    payload = request.json
    barcode = payload.get('barcode')
    price = payload.get('price')

    if not all([barcode, price is not None]):
        return jsonify({"error": "Missing barcode or price"}), 400

    # Ensure product exists in master to get its name for tracking data
    product_name, product_details = data_manager.get_product_from_master_by_barcode(barcode)
    if not product_details:
        return jsonify({"error": "Product not found with this barcode in master list"}), 404

    success = data_manager.record_product_price_entry(product_name, barcode, price)  # Pass name here
    if success:
        return jsonify({"success": True, "message": "Price recorded successfully"})
    return jsonify({"error": "Failed to record price"}), 500


@app.route('/api/all_products')
def get_all_products():
    products_data = data_manager.get_all_products_from_master()
    return jsonify(products_data)


@app.route('/api/delete_master_product', methods=['POST'])
def delete_master_product():
    payload = request.json
    name = payload.get('name')
    if not name:
        return jsonify({"error": "Missing product name"}), 400

    success = data_manager.delete_product_from_master(name)
    if success:
        return jsonify({"success": True, "message": "Product deleted from master successfully"})
    return jsonify({"error": "Product not found in master list"}), 404


@app.route('/api/update_master_product', methods=['POST'])
def update_master_product():
    payload = request.json
    old_name = payload.get('old_name')
    new_name = payload.get('new_name')
    new_barcode = payload.get('new_barcode', '').strip()

    if not old_name or not new_name:
        return jsonify({"error": "Missing old or new product name"}), 400

    success = data_manager.update_product_in_master(old_name, new_name, new_barcode)
    if success:
        return jsonify({"success": True, "message": "Product updated in master successfully"})
    return jsonify({"error": "Product not found or failed to update in master"}), 404



# --- NEW: Endpoint to process scanned barcodes and handle product addition/update ---
@app.route('/api/process_scanned_barcode', methods=['POST'])
def process_scanned_barcode():
    payload = request.json
    scanned_barcode = payload.get('barcode')
    product_name = payload.get('product_name') # This will be optional, used only for new products

    if not scanned_barcode:
        return jsonify({"success": False, "error": "Barcode is missing"}), 400

    existing_product_name = data_manager.get_product_from_master_by_barcode(scanned_barcode)

    if existing_product_name:

        # Barcode already exists, return its name
        product = {
            "success": True,
            "exists": True,
            "product_name": existing_product_name[0],
            "barcode": scanned_barcode,
            "message": "Barcode already associated with an existing product."
        }
        print("Existing product found:", product)
        return jsonify(product)
    else:
        # Barcode does not exist, add it if product_name is provided
        if not product_name:
            # If product_name is not provided, this is just a check from the frontend
            # The frontend will then prompt the user for a name.
            return jsonify({
                "success": True,
                "exists": False,
                "barcode": scanned_barcode,
                "message": "Barcode is new. A product name is required to add it."
            })
        else:
            # Add the new product
            success = data_manager.add_product_to_master(product_name, scanned_barcode)
            if success:
                return jsonify({
                    "success": True,
                    "exists": False, # Still false, as it was new before addition
                    "product_name": product_name,
                    "barcode": scanned_barcode,
                    "message": "New product added successfully."
                })
            else:
                return jsonify({"success": False, "error": "Failed to add new product."}), 500




if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)

