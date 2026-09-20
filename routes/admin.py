import sys
import os
import json

# Add the project root to Python path so config can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import traceback
import uuid
from datetime import datetime, timedelta
from functools import wraps

import requests
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for, send_from_directory
from werkzeug.utils import secure_filename

from config import Config
from models.user import User
from utils.data import (
    get_cart,
    get_sales_analytics,
    load_bundles,
    load_orders,
    load_products,
    order_revenue_value,
    update_product_stock,
)
from utils.storage import load_json_data, save_json_data

admin_bp = Blueprint('admin', __name__)

# ============================================================
# DETECT VERCEL ENVIRONMENT
# ============================================================
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('NOW_REGION') is not None
print(f"🚀 Running on: {'Vercel' if IS_VERCEL else 'Local'}")

# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def is_admin():
    user = session.get('user', {})
    return user.get('role') == 'admin' or session.get('admin_logged_in')

def is_logged_in():
    return 'user' in session or session.get('admin_logged_in')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash('Admin access required', 'danger')
            return redirect(url_for('admin.user_login'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Please login first', 'danger')
            return redirect(url_for('admin.user_login'))
        return f(*args, **kwargs)
    return decorated_function

def seed_demo_products():
    demo_products = [
        {'id': 'PROD_1', 'name': 'Wireless Headphones', 'price': 2999, 'stock': 45, 'category': 'Electronics', 'image': '', 'description': 'Premium wireless headphones'},
        {'id': 'PROD_2', 'name': 'USB-C Cable', 'price': 499, 'stock': 120, 'category': 'Accessories', 'image': ''},
        {'id': 'PROD_3', 'name': 'Bluetooth Speaker', 'price': 1499, 'stock': 30, 'category': 'Electronics', 'image': ''},
        {'id': 'PROD_4', 'name': 'Laptop Stand', 'price': 899, 'stock': 25, 'category': 'Furniture', 'image': ''},
        {'id': 'PROD_5', 'name': 'Wireless Mouse', 'price': 699, 'stock': 60, 'category': 'Accessories', 'image': ''},
        {'id': 'PROD_6', 'name': 'Mechanical Keyboard', 'price': 2499, 'stock': 15, 'category': 'Electronics', 'image': ''},
        {'id': 'PROD_7', 'name': 'HDMI Cable', 'price': 299, 'stock': 80, 'category': 'Accessories', 'image': ''},
        {'id': 'PROD_8', 'name': 'USB Hub', 'price': 1299, 'stock': 20, 'category': 'Accessories', 'image': ''},
        {'id': 'PROD_9', 'name': 'Monitor 24"', 'price': 14999, 'stock': 8, 'category': 'Electronics', 'image': ''},
        {'id': 'PROD_10', 'name': 'Desk Lamp', 'price': 599, 'stock': 35, 'category': 'Furniture', 'image': ''},
    ]
    return demo_products

def get_default_users():
    return [
        {'id': 'admin_1', 'email': 'admin@pricepoint.com', 'password': 'electronics2026', 'name': 'Admin User', 'role': 'admin'},
        {'id': 'manager_1', 'email': 'manager@pricepoint.com', 'password': 'electronics2026', 'name': 'Store Manager', 'role': 'manager'},
        {'id': 'pos_1', 'email': 'pos@pricepoint.com', 'password': 'electronics2026', 'name': 'POS Operator', 'role': 'pos'},
        {'id': 'user_1', 'email': 'user@pricepoint.com', 'password': 'electronics2026', 'name': 'Regular User', 'role': 'user'}
    ]

# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

@admin_bp.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Please enter both email and password', 'danger')
            return render_template('admin_login.html')

        db_user, db_error = User.authenticate(email, password)
        if db_user:
            session['user'] = {
                'email': db_user.email,
                'name': db_user.full_name or db_user.email,
                'role': db_user.role,
                'id': db_user.id
            }
            session['admin_logged_in'] = True
            flash('Welcome, ' + (db_user.full_name or db_user.email) + '!', 'success')
            return redirect('/admin' if db_user.role == 'admin' else '/admin/pos')

        users_legacy = {
            'admin@pricepoint.com': {
                'password': 'electronics2026',
                'name': 'Admin User',
                'role': 'admin',
                'redirect': '/admin'
            },
            'user@pricepoint.com': {
                'password': 'electronics2026',
                'name': 'John Doe',
                'role': 'user',
                'redirect': '/admin/pos'
            },
            'pos@pricepoint.com': {
                'password': 'electronics2026',
                'name': 'POS Operator',
                'role': 'pos',
                'redirect': '/admin/pos'
            },
            'manager@pricepoint.com': {
                'password': 'electronics2026',
                'name': 'Store Manager',
                'role': 'manager',
                'redirect': '/admin/pos'
            }
        }

        username = request.form.get('username', '').strip()
        if username == 'admin' and password == 'electronics2026':
            session['admin_logged_in'] = True
            session['user'] = {
                'email': 'admin@pricepoint.com',
                'name': 'Admin User',
                'role': 'admin',
                'id': 'legacy_admin'
            }
            flash('Welcome back, Admin!', 'success')
            return redirect('/admin')

        if email in users_legacy and users_legacy[email]['password'] == password:
            session['user'] = {
                'email': email,
                'name': users_legacy[email]['name'],
                'role': users_legacy[email]['role'],
                'id': 'legacy_' + email
            }
            session['admin_logged_in'] = True
            flash('Welcome, ' + users_legacy[email]['name'] + '!', 'success')
            return redirect(users_legacy[email]['redirect'])
        else:
            flash('Invalid email or password', 'danger')
            return render_template('admin_login.html')

    return render_template('admin_login.html')

@admin_bp.route('/logout')
def user_logout():
    session.pop('user', None)
    session.pop('admin_logged_in', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('admin.user_login'))

@admin_bp.route('/admin/login')
def admin_login_redirect():
    return redirect(url_for('admin.user_login'))

@admin_bp.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out', 'success')
    return redirect(url_for('admin.user_login'))

# ============================================================
# PRODUCTS API - MAIN
# ============================================================

@admin_bp.route('/admin/api/products', methods=['GET'])
@admin_required
def api_products_list():
    """Get paginated products for AJAX - FIXED"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '').strip()
        filter_low_stock = request.args.get('low_stock', 'false').lower() == 'true'
        filter_out_of_stock = request.args.get('out_of_stock', 'false').lower() == 'true'
        
        print(f"🔍 API Products called: search='{search}', low_stock={filter_low_stock}, out_of_stock={filter_out_of_stock}")
        
        all_products = load_products()
        
        # ============================================================
        # [NEW] GET SUPPLIER NAMES
        # ============================================================
        supplier_map = {}
        try:
            response = requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/suppliers?select=supplier_id,business_name",
                headers=Config.SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                for s in response.json():
                    supplier_map[s['supplier_id']] = s.get('business_name', '')
        except:
            pass
        
        # Apply filters
        filtered_products = []
        search_lower = search.lower() if search else ''
        
        for product in all_products:
            # Get stock safely
            stock = product.get('stock', 0)
            if isinstance(stock, str):
                try:
                    stock = int(stock)
                except:
                    stock = 0
            if stock is None:
                stock = 0
            
            # Apply stock filters
            if filter_low_stock and stock >= 10:
                continue
            if filter_out_of_stock and stock > 0:
                continue
            
            # Apply search filter
            if search:
                name = str(product.get('name', '')).lower()
                category = str(product.get('category', '')).lower()
                description = str(product.get('description', '')).lower()
                barcode = str(product.get('barcode', '')).lower()
                product_id = str(product.get('id', '')).lower()
                
                if not (search_lower in name or 
                       search_lower in category or 
                       search_lower in description or 
                       search_lower in barcode or 
                       search_lower in product_id):
                    continue
            
            # [NEW] Add supplier name to product
            supplier_id = product.get('supplier_id')
            if supplier_id and supplier_id in supplier_map:
                product['supplier_name'] = supplier_map[supplier_id]
            else:
                product['supplier_name'] = ''
            
            filtered_products.append(product)
        
        print(f"📊 Found {len(filtered_products)} products after filtering")
        
        # Sort by stock if low stock filter is applied
        if filter_low_stock or filter_out_of_stock:
            filtered_products.sort(key=lambda x: x.get('stock', 0))
        else:
            filtered_products.sort(key=lambda x: x.get('name', ''))
        
        total = len(filtered_products)
        start = (page - 1) * per_page
        end = start + per_page
        products = filtered_products[start:end]
        
        return jsonify({
            'success': True,
            'products': products,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
            'start': start + 1 if products else 0,
            'end': min(end, total),
            'filter_low_stock': filter_low_stock,
            'filter_out_of_stock': filter_out_of_stock,
            'search': search
        })
    except Exception as e:
        print(f"❌ Products API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# PRODUCT SEARCH API
# ============================================================

@admin_bp.route('/admin/api/products/search', methods=['GET'])
@admin_required
def api_product_search():
    """Search products across ALL pages with filters"""
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 500))
        filter_low_stock = request.args.get('low_stock', 'false').lower() == 'true'
        filter_out_of_stock = request.args.get('out_of_stock', 'false').lower() == 'true'
        
        print(f"🔍 Searching products: query='{query}', low_stock={filter_low_stock}, out_of_stock={filter_out_of_stock}")
        
        all_products = load_products()
        query_lower = query.lower()
        results = []
        
        for product in all_products:
            name = str(product.get('name', '')).lower()
            category = str(product.get('category', '')).lower()
            description = str(product.get('description', '')).lower()
            barcode = str(product.get('barcode', '')).lower()
            product_id = str(product.get('id', '')).lower()
            
            stock = product.get('stock', 0)
            if isinstance(stock, str):
                try:
                    stock = int(stock)
                except:
                    stock = 0
            if stock is None:
                stock = 0
            
            if filter_low_stock and stock >= 10:
                continue
            if filter_out_of_stock and stock > 0:
                continue
            
            if not query:
                product['_stock'] = stock
                results.append(product)
                continue
            
            specs = product.get('specs')
            specs_match = False
            if specs is not None:
                if isinstance(specs, list):
                    specs_str = ' '.join([str(s).lower() for s in specs if s is not None])
                    specs_match = query_lower in specs_str
                else:
                    specs_match = query_lower in str(specs).lower()
            
            name_match = query_lower in name
            category_match = query_lower in category
            desc_match = query_lower in description
            barcode_match = query_lower in barcode
            id_match = query_lower in product_id
            
            if name_match or category_match or desc_match or barcode_match or id_match or specs_match:
                score = 0
                if name_match:
                    score += 10
                    if query_lower == name:
                        score += 5
                if category_match:
                    score += 5
                if desc_match:
                    score += 3
                if barcode_match:
                    score += 3
                if id_match:
                    score += 2
                if specs_match:
                    score += 2
                
                product['_score'] = score
                product['_stock'] = stock
                results.append(product)
        
        if query:
            results.sort(key=lambda x: x.get('_score', 0), reverse=True)
        elif filter_low_stock or filter_out_of_stock:
            results.sort(key=lambda x: x.get('_stock', 999))
        else:
            results.sort(key=lambda x: x.get('name', ''))
        
        for r in results:
            r.pop('_score', None)
            r.pop('_stock', None)
        
        results = results[:limit]
        
        return jsonify({
            'success': True,
            'products': results,
            'total': len(results),
            'query': query,
            'limit': limit,
            'filter_low_stock': filter_low_stock,
            'filter_out_of_stock': filter_out_of_stock
        })
        
    except Exception as e:
        print(f"❌ Product search error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'products': [],
            'total': 0
        }), 500

# ============================================================
# LOW STOCK PRODUCTS API
# ============================================================

@admin_bp.route('/admin/api/products/low-stock', methods=['GET'])
@admin_required
def api_low_stock_products():
    """Get all low stock products (stock < 10)"""
    try:
        all_products = load_products()
        low_stock = []
        out_of_stock = []
        
        for product in all_products:
            stock = product.get('stock', 0)
            if isinstance(stock, str):
                try:
                    stock = int(stock)
                except:
                    stock = 0
            if stock is None:
                stock = 0
            
            if stock == 0:
                out_of_stock.append(product)
            elif stock < 10:
                low_stock.append(product)
        
        low_stock.sort(key=lambda x: x.get('stock', 0))
        out_of_stock.sort(key=lambda x: x.get('name', ''))
        
        return jsonify({
            'success': True,
            'low_stock': low_stock,
            'out_of_stock': out_of_stock,
            'low_stock_count': len(low_stock),
            'out_of_stock_count': len(out_of_stock),
            'total_low_stock': len(low_stock) + len(out_of_stock)
        })
    except Exception as e:
        print(f"❌ Low stock API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# ORDERS API
# ============================================================

@admin_bp.route('/admin/api/orders', methods=['GET'])
@admin_required
def api_orders_list():
    """Get paginated orders for AJAX"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Try to get from Supabase
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/orders?select=*&order=created_at.desc",
            headers=Config.SUPABASE_HEADERS,
            timeout=10
        )
        
        all_orders = []
        if response.status_code == 200:
            all_orders = response.json()
            print(f"📋 Found {len(all_orders)} orders from Supabase")
        else:
            # Fallback to local cache
            all_orders = load_orders()
            all_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            print(f"📋 Found {len(all_orders)} orders from local cache")
        
        total = len(all_orders)
        start = (page - 1) * per_page
        end = start + per_page
        orders = all_orders[start:end]
        
        return jsonify({
            'success': True,
            'orders': orders,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
            'start': start + 1 if orders else 0,
            'end': min(end, total)
        })
    except Exception as e:
        print(f"❌ Orders API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# ORDER DETAIL API
# ============================================================

@admin_bp.route('/admin/api/order/<order_id>', methods=['GET'])
@admin_required
def api_get_order_details(order_id):
    """Get single order details for modal"""
    try:
        print(f"🔍 Fetching order details for: {order_id}")
        
        # Try to get from Supabase directly
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/orders?order_id=eq.{order_id}&select=*",
            headers=Config.SUPABASE_HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            orders = response.json()
            if orders:
                order = orders[0]
                print(f"✅ Found order: {order.get('order_id')}")
                
                items = order.get('items', [])
                if isinstance(items, str):
                    try:
                        items = json.loads(items)
                    except:
                        items = []
                
                customer = order.get('customer', {})
                if isinstance(customer, str):
                    try:
                        customer = json.loads(customer)
                    except:
                        customer = {}
                
                return jsonify({
                    'success': True,
                    'order': {
                        'order_id': order.get('order_id'),
                        'items': items,
                        'subtotal': order.get('subtotal', 0),
                        'shipping': order.get('shipping', 0),
                        'total': order.get('total', 0),
                        'status': order.get('status', 'pending'),
                        'source': order.get('source', 'web'),
                        'payment_method': order.get('payment_method', order.get('payment_type', 'Cash')),
                        'payment_status': order.get('payment_status', 'pending'),
                        'location': order.get('location', order.get('customer_address', 'N/A')),
                        'delivery_zone': order.get('delivery_zone', ''),
                        'distance_km': order.get('distance_km', 0),
                        'delivery_notes': order.get('delivery_notes', ''),
                        'created_at': order.get('created_at', ''),
                        'customer_name': order.get('customer_name', 'Customer'),
                        'customer_email': order.get('customer_email', ''),
                        'customer_phone': order.get('customer_phone', ''),
                        'customer_address': order.get('customer_address', ''),
                        'customer': customer
                    }
                })
        
        # If not found in Supabase, try local cache
        all_orders = load_orders()
        for order in all_orders:
            if str(order.get('order_id')) == str(order_id):
                items = order.get('items', [])
                if isinstance(items, str):
                    try:
                        items = json.loads(items)
                    except:
                        items = []
                
                customer = order.get('customer', {})
                if isinstance(customer, str):
                    try:
                        customer = json.loads(customer)
                    except:
                        customer = {}
                
                return jsonify({
                    'success': True,
                    'order': {
                        'order_id': order.get('order_id'),
                        'items': items,
                        'subtotal': order.get('subtotal', 0),
                        'shipping': order.get('shipping', 0),
                        'total': order.get('total', 0),
                        'status': order.get('status', 'pending'),
                        'source': order.get('source', 'web'),
                        'payment_method': order.get('payment_method', order.get('payment_type', 'Cash')),
                        'payment_status': order.get('payment_status', 'pending'),
                        'location': order.get('location', order.get('customer_address', 'N/A')),
                        'delivery_zone': order.get('delivery_zone', ''),
                        'distance_km': order.get('distance_km', 0),
                        'delivery_notes': order.get('delivery_notes', ''),
                        'created_at': order.get('created_at', ''),
                        'customer_name': order.get('customer_name', 'Customer'),
                        'customer_email': order.get('customer_email', ''),
                        'customer_phone': order.get('customer_phone', ''),
                        'customer_address': order.get('customer_address', ''),
                        'customer': customer
                    }
                })
        
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    except Exception as e:
        print(f"❌ Error fetching order: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# PRODUCT DETAIL API - GET
# ============================================================

@admin_bp.route('/admin/api/product/<product_id>', methods=['GET'])
@admin_required
def api_get_product_details(product_id):
    """Get single product details for editing"""
    try:
        print(f"🔍 Fetching product details for: {product_id}")
        
        # Try to get from Supabase directly
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}&select=*",
            headers=Config.SUPABASE_HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            products = response.json()
            if products:
                product = products[0]
                print(f"✅ Found product: {product.get('name')}")
                return jsonify({'success': True, 'product': product})
        
        # If not found in Supabase, try local cache
        all_products = load_products()
        for product in all_products:
            if str(product.get('id')) == str(product_id):
                return jsonify({'success': True, 'product': product})
        
        return jsonify({'success': False, 'error': 'Product not found'}), 404
    except Exception as e:
        print(f"❌ Error fetching product: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# PRODUCT DETAIL API - UPDATE (PUT/PATCH)
# ============================================================

@admin_bp.route('/admin/api/product/<product_id>', methods=['PUT', 'PATCH'])
@admin_required
def api_update_product(product_id):
    """Update an existing product - FIXES 405 ERROR"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        print(f"📦 Updating product: {product_id}")
        print(f"📦 Data: {data}")
        
        # Clean data - remove None values
        clean_data = {k: v for k, v in data.items() if v is not None}
        
        # Update in Supabase
        response = requests.patch(
            f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
            headers=Config.SUPABASE_HEADERS,
            json=clean_data,
            timeout=10
        )
        
        if response.status_code in [200, 204]:
            # Clear cache
            import utils.data
            utils.data.products_cache = []
            
            return jsonify({
                'success': True,
                'message': 'Product updated successfully',
                'product': data
            })
        else:
            print(f"❌ Failed to update product: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'message': f'Failed to update product: {response.status_code}',
                'error': response.text
            }), 500
            
    except Exception as e:
        print(f"❌ Error updating product: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# PRODUCT DETAIL API - DELETE
# ============================================================

@admin_bp.route('/admin/api/product/<product_id>', methods=['DELETE'])
@admin_required
def api_delete_product(product_id):
    """Delete a product"""
    try:
        print(f"🗑️ Deleting product: {product_id}")
        
        response = requests.delete(
            f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
            headers=Config.SUPABASE_HEADERS,
            timeout=10
        )
        
        if response.status_code in [200, 204]:
            import utils.data
            utils.data.products_cache = []
            
            return jsonify({
                'success': True,
                'message': 'Product deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to delete product: {response.status_code}'
            }), 500
            
    except Exception as e:
        print(f"❌ Error deleting product: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# ADMIN DASHBOARD
# ============================================================

@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    if not is_admin():
        flash('Admin access required', 'danger')
        return redirect(url_for('admin.user_login'))

    try:
        import utils.data
        utils.data.orders_cache = []

        user = session.get('user', {})
        user_name = user.get('name', 'Admin User')
        user_role = user.get('role', 'admin')

        all_products = load_products()
        all_orders = load_orders()
        
        cleaned_products = []
        for p in all_products:
            clean_p = dict(p)
            if clean_p.get('stock') is None:
                clean_p['stock'] = 0
            if clean_p.get('price') is None:
                clean_p['price'] = 0
            if clean_p.get('name') is None:
                clean_p['name'] = 'Unnamed Product'
            if clean_p.get('category') is None:
                clean_p['category'] = 'Uncategorized'
            if clean_p.get('image') is None:
                clean_p['image'] = ''
            if clean_p.get('description') is None:
                clean_p['description'] = ''
            if clean_p.get('cost_price') is None:
                clean_p['cost_price'] = 0
            if clean_p.get('badge') is None:
                clean_p['badge'] = ''
            if clean_p.get('supplier_id') is None:
                clean_p['supplier_id'] = ''
            cleaned_products.append(clean_p)
        
        all_products = cleaned_products
        
        # ============================================================
        # [NEW] GET SUPPLIER DATA FOR PRODUCTS
        # ============================================================
        supplier_map = {}
        try:
            response = requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/suppliers?select=supplier_id,business_name",
                headers=Config.SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                for s in response.json():
                    supplier_map[s['supplier_id']] = s.get('business_name', '')
                print(f"✅ Loaded {len(supplier_map)} suppliers for product mapping")
        except Exception as e:
            print(f"⚠️ Could not load supplier map: {e}")
        
        # Attach supplier names to products
        for p in all_products:
            if p.get('supplier_id') in supplier_map:
                p['supplier_name'] = supplier_map[p['supplier_id']]
            else:
                p['supplier_name'] = ''
        
        print(f"📡 Loaded: {len(all_products)} products, {len(all_orders)} orders")

        if not all_products:
            all_products = seed_demo_products()
            for p in all_products:
                if p.get('stock') is None:
                    p['stock'] = 0
                if p.get('price') is None:
                    p['price'] = 0
                if p.get('name') is None:
                    p['name'] = 'Unnamed Product'
                if p.get('category') is None:
                    p['category'] = 'Uncategorized'
                if p.get('supplier_id') is None:
                    p['supplier_id'] = ''
            try:
                for product in all_products:
                    requests.post(
                        f"{Config.SUPABASE_URL}/rest/v1/products",
                        headers=Config.SUPABASE_HEADERS,
                        json=product,
                        timeout=10
                    )
                print("🌱 Demo products seeded to Supabase")
            except Exception as e:
                print(f"⚠️ Could not seed demo products: {e}")

        bundles = load_bundles()
        cart = get_cart()
        analytics = get_sales_analytics()

        per_page = 10

        products_page = request.args.get('products_page', 1, type=int)
        orders_page = request.args.get('orders_page', 1, type=int)
        customers_page = request.args.get('customers_page', 1, type=int)

        customer_dict = {}
        pos_count = 0
        web_count = 0
        credit_count = 0

        for order in all_orders:
            name = None
            email = None
            phone = None

            if order.get('customer_name'):
                name = order.get('customer_name')

            if not name:
                customer = order.get('customer', {})
                if isinstance(customer, dict):
                    name = customer.get('name')
                    if not email:
                        email = customer.get('email')
                    if not phone:
                        phone = customer.get('phone')
                elif isinstance(customer, str):
                    try:
                        customer_obj = json.loads(customer)
                        name = customer_obj.get('name')
                        if not email:
                            email = customer_obj.get('email')
                        if not phone:
                            phone = customer_obj.get('phone')
                    except:
                        pass

            if not name:
                email = order.get('customer_email', '')
                if email and '@' in email:
                    name = email.split('@')[0].replace('.', ' ').title()

            if not name or name in ['Walk-in Customer', 'Web Customer', 'Customer', 'Unknown', '']:
                continue

            if not email or email == 'N/A':
                email = order.get('customer_email', 'N/A')
                if (not email or email == 'N/A') and isinstance(order.get('customer'), dict):
                    email = order.get('customer', {}).get('email', 'N/A')

            if not phone or phone == 'N/A':
                phone = order.get('customer_phone', 'N/A')
                if (not phone or phone == 'N/A') and isinstance(order.get('customer'), dict):
                    phone = order.get('customer', {}).get('phone', 'N/A')

            if order.get('source') == 'pos':
                pos_count += 1
            elif order.get('source') == 'credit':
                credit_count += 1
            else:
                web_count += 1

            if name not in customer_dict:
                customer_dict[name] = {
                    'name': name,
                    'email': email if email else 'N/A',
                    'phone': phone if phone else 'N/A',
                    'orders': 0,
                    'total_spent': 0
                }
            customer_dict[name]['orders'] += 1
            customer_dict[name]['total_spent'] += order.get('total', 0)

        customers = list(customer_dict.values())
        customers.sort(key=lambda x: x['orders'], reverse=True)
        total_customers = len(customers)

        total_orders = len([o for o in all_orders if o.get('status') != 'cancelled'])
        total_revenue = sum(order_revenue_value(o) for o in all_orders if o.get('status') != 'cancelled')
        pending_orders = len([o for o in all_orders if o.get('status') == 'pending'])
        
        low_stock_items = 0
        out_of_stock_items = 0
        for p in all_products:
            stock = p.get('stock', 0)
            if stock is None:
                stock = 0
            if stock < 10 and stock > 0:
                low_stock_items += 1
            elif stock == 0:
                out_of_stock_items += 1

        now = datetime.utcnow()
        today = now.date()
        first_day_this_month = today.replace(day=1)

        today_revenue = 0
        today_orders = 0
        yesterday_revenue = 0
        month_revenue = 0
        month_orders = 0
        last_month_revenue = 0

        if today.month == 1:
            last_month_year = today.year - 1
            last_month_month = 12
        else:
            last_month_year = today.year
            last_month_month = today.month - 1

        first_day_last_month = datetime(last_month_year, last_month_month, 1).date()
        if today.month == 1:
            last_day_last_month = datetime(last_month_year, 12, 31).date()
        else:
            last_day_last_month = datetime(today.year, today.month, 1).date() - timedelta(days=1)

        for order in all_orders:
            total = order_revenue_value(order)

            if order.get('status') == 'cancelled':
                continue

            created_at = order.get('created_at', '')
            if not created_at:
                continue

            try:
                if isinstance(created_at, datetime):
                    order_date = created_at.date()
                elif isinstance(created_at, str):
                    if 'T' in created_at:
                        clean = created_at.replace('Z', '').replace('+00:00', '')
                        if '.' in clean:
                            order_date = datetime.fromisoformat(clean).date()
                        else:
                            order_date = datetime.strptime(clean[:10], '%Y-%m-%d').date()
                    elif ' ' in created_at:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                    else:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                else:
                    continue
            except Exception as e:
                print(f"Date parse error: {e}")
                continue

            if order_date == today:
                today_revenue += total
                today_orders += 1

            if order_date == today - timedelta(days=1):
                yesterday_revenue += total

            if order_date >= first_day_this_month:
                month_revenue += total
                month_orders += 1

            if first_day_last_month <= order_date <= last_day_last_month:
                last_month_revenue += total

        if yesterday_revenue > 0:
            today_growth = round(((today_revenue - yesterday_revenue) / yesterday_revenue) * 100, 1)
        else:
            today_growth = 100.0 if today_revenue > 0 else 0

        if last_month_revenue > 0:
            month_growth = round(((month_revenue - last_month_revenue) / last_month_revenue) * 100, 1)
        else:
            month_growth = 100.0 if month_revenue > 0 else 0

        total_customer_pages = (total_customers + per_page - 1) // per_page if total_customers > 0 else 1
        if customers_page < 1:
            customers_page = 1
        elif customers_page > total_customer_pages and total_customer_pages > 0:
            customers_page = total_customer_pages

        customers_start = (customers_page - 1) * per_page
        customers_end = customers_start + per_page
        paginated_customers = customers[customers_start:customers_end] if customers else []

        total_products = len(all_products)
        total_product_pages = (total_products + per_page - 1) // per_page if total_products > 0 else 1
        if products_page < 1:
            products_page = 1
        elif products_page > total_product_pages and total_product_pages > 0:
            products_page = total_product_pages

        products_start = (products_page - 1) * per_page
        products_end = products_start + per_page
        paginated_products = all_products[products_start:products_end] if all_products else []

        sorted_orders = sorted(all_orders, key=lambda x: x.get('created_at', ''), reverse=True)
        total_order_pages = (total_orders + per_page - 1) // per_page if total_orders > 0 else 1
        if orders_page < 1:
            orders_page = 1
        elif orders_page > total_order_pages and total_order_pages > 0:
            orders_page = total_order_pages

        orders_start = (orders_page - 1) * per_page
        orders_end = orders_start + per_page
        paginated_orders = sorted_orders[orders_start:orders_end] if sorted_orders else []

        recent_orders = sorted_orders[:3] if sorted_orders else []

        stats = {
            'total_products': total_products,
            'total_bundles': len(bundles),
            'total_cart_items': sum(cart.values()) if cart else 0,
            'low_stock': low_stock_items,
            'out_of_stock': out_of_stock_items,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'pos_orders': pos_count,
            'web_orders': web_count,
            'credit_orders': credit_count,
            'total_revenue': total_revenue,
            'total_cost': analytics.get('total_cost', 0),
            'total_profit': analytics.get('total_profit', 0),
            'total_items_sold': analytics.get('total_items_sold', 0),
            'total_customers': total_customers,
            'today_revenue': today_revenue,
            'today_orders': today_orders,
            'yesterday_revenue': yesterday_revenue,
            'month_revenue': month_revenue,
            'month_orders': month_orders,
            'last_month_revenue': last_month_revenue,
            'today_growth_pct': today_growth,
            'month_growth_pct': month_growth,
            'db_mode': 'online',
        }

        # ============================================================
        # CREDIT DATA
        # ============================================================
        credit_summary = {
            'total_customers': 0,
            'active_customers': 0,
            'total_balance': 0,
            'total_purchases': 0,
            'total_payments': 0,
            'total_cost': 0,
            'total_profit': 0
        }
        credit_customers = []
        overdue_count = 0

        try:
            response = requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/credit_customers?select=*",
                headers=Config.SUPABASE_HEADERS,
                timeout=10
            )
            
            if response.status_code == 200:
                credit_customers = response.json()
                total_cust = len(credit_customers)
                active_cust = sum(1 for c in credit_customers if c.get('account_status') == 'active')
                total_balance = sum(c.get('current_balance', 0) for c in credit_customers)
                total_cost = sum(c.get('total_cost', 0) for c in credit_customers)
                total_profit = sum(c.get('total_profit', 0) for c in credit_customers)
                
                tx_response = requests.get(
                    f"{Config.SUPABASE_URL}/rest/v1/credit_transactions?select=*",
                    headers=Config.SUPABASE_HEADERS,
                    timeout=10
                )
                
                total_purchases = 0
                total_payments = 0
                if tx_response.status_code == 200:
                    transactions = tx_response.json()
                    total_purchases = sum(t.get('amount', 0) for t in transactions if t.get('transaction_type') == 'purchase')
                    total_payments = sum(t.get('amount', 0) for t in transactions if t.get('transaction_type') == 'payment')
                
                overdue_count = sum(1 for c in credit_customers if c.get('current_balance', 0) > c.get('credit_limit', 0))
                
                credit_summary = {
                    'total_customers': total_cust,
                    'active_customers': active_cust,
                    'total_balance': total_balance,
                    'total_purchases': total_purchases,
                    'total_payments': total_payments,
                    'total_cost': total_cost,
                    'total_profit': total_profit
                }
                print(f"✅ Loaded {total_cust} credit customers with profit: KSh {total_profit}")
            else:
                print(f"⚠️ Credit customers fetch error: {response.status_code}")
        except Exception as e:
            print(f"❌ Error loading credit data: {e}")

        # ============================================================
        # SUPPLIER DATA
        # ============================================================
        supplier_summary = {
            'total_suppliers': 0,
            'active_suppliers': 0,
            'total_products': 0
        }
        suppliers = []
        low_stock_count = low_stock_items

        try:
            response = requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/suppliers?select=*",
                headers=Config.SUPABASE_HEADERS,
                timeout=10
            )
            
            if response.status_code == 200:
                suppliers = response.json()
                total_supp = len(suppliers)
                active_supp = sum(1 for s in suppliers if s.get('status') == 'active')
                
                prod_response = requests.get(
                    f"{Config.SUPABASE_URL}/rest/v1/products?select=supplier_id",
                    headers=Config.SUPABASE_HEADERS,
                    timeout=10
                )
                
                product_counts = {}
                if prod_response.status_code == 200:
                    products = prod_response.json()
                    for p in products:
                        sid = p.get('supplier_id')
                        if sid:
                            product_counts[sid] = product_counts.get(sid, 0) + 1
                
                for s in suppliers:
                    s['total_products'] = product_counts.get(s.get('supplier_id'), 0)
                
                supplier_summary = {
                    'total_suppliers': total_supp,
                    'active_suppliers': active_supp,
                    'total_products': sum(product_counts.values())
                }
                print(f"✅ Loaded {total_supp} suppliers")
            else:
                print(f"⚠️ Suppliers fetch error: {response.status_code}")
        except Exception as e:
            print(f"❌ Error loading supplier data: {e}")

        return render_template('admin.html',
            products=paginated_products,
            all_products=all_products,
            total_products=total_products,
            product_page=products_page,
            total_product_pages=total_product_pages,
            orders=paginated_orders,
            recent_orders=recent_orders,
            total_orders=total_orders,
            orders_page=orders_page,
            total_order_pages=total_order_pages,
            customers=paginated_customers,
            total_customers=total_customers,
            customers_page=customers_page,
            total_customer_pages=total_customer_pages,
            per_page=per_page,
            bundles=bundles,
            stats=stats,
            pos_count=pos_count,
            analytics=analytics,
            DB_CONNECTED=True,
            credit_summary=credit_summary,
            credit_customers=credit_customers,
            overdue_count=overdue_count,
            supplier_summary=supplier_summary,
            suppliers=suppliers,
            low_stock_count=low_stock_count,
            out_of_stock_count=out_of_stock_items
        )

    except Exception as exc:
        print(f'Admin dashboard error: {exc}')
        traceback.print_exc()
        flash('Error loading admin dashboard', 'danger')
        return render_template('admin.html',
            products=[],
            bundles=[],
            orders=[],
            customers=[],
            pos_count=0,
            analytics={},
            stats={
                'total_products': 0,
                'total_bundles': 0,
                'total_cart_items': 0,
                'low_stock': 0,
                'out_of_stock': 0,
                'total_orders': 0,
                'pending_orders': 0,
                'pos_orders': 0,
                'web_orders': 0,
                'credit_orders': 0,
                'total_revenue': 0,
                'total_cost': 0,
                'total_profit': 0,
                'total_items_sold': 0,
                'total_customers': 0,
                'today_revenue': 0,
                'today_orders': 0,
                'yesterday_revenue': 0,
                'month_revenue': 0,
                'month_orders': 0,
                'last_month_revenue': 0,
                'today_growth_pct': 0,
                'month_growth_pct': 0,
                'db_mode': 'offline',
            },
            total_products=0,
            total_product_pages=1,
            product_page=1,
            total_orders=0,
            total_order_pages=1,
            orders_page=1,
            total_customers=0,
            total_customer_pages=1,
            customers_page=1,
            per_page=10,
            recent_orders=[],
            DB_CONNECTED=False,
            credit_summary={'total_customers': 0, 'active_customers': 0, 'total_balance': 0, 'total_purchases': 0, 'total_payments': 0},
            credit_customers=[],
            overdue_count=0,
            supplier_summary={'total_suppliers': 0, 'active_suppliers': 0, 'total_products': 0},
            suppliers=[],
            low_stock_count=0,
            out_of_stock_count=0
        )

# ============================================================
# CREDIT CUSTOMER MANAGEMENT ROUTES
# ============================================================

@admin_bp.route('/admin/credit')
@admin_required
def admin_credit():
    """Credit management page"""
    try:
        from utils.credit import get_all_credit_customers, get_credit_summary, get_overdue_customers
        from datetime import datetime
        
        customers = get_all_credit_customers()
        summary = get_credit_summary()
        overdue = get_overdue_customers()
        
        stats = {
            'total_orders': 0,
            'pending_orders': 0,
            'total_products': 0,
            'total_customers': summary.get('total_customers', 0),
            'today_revenue': 0,
            'month_revenue': 0,
            'total_revenue': 0,
            'low_stock': 0,
            'total_bundles': 0,
            'total_cart_items': 0,
            'pos_orders': 0,
            'web_orders': 0,
            'credit_orders': 0,
            'today_growth_pct': 0,
            'month_growth_pct': 0,
            'db_mode': 'online'
        }
        
        return render_template('admin_credit.html',
            customers=customers,
            summary=summary,
            overdue=overdue,
            overdue_count=len(overdue),
            stats=stats,
            DB_CONNECTED=True,
            IS_VERCEL=IS_VERCEL,
            now=datetime.utcnow()
        )
    except Exception as e:
        print(f"❌ Error loading credit customers: {e}")
        flash('Error loading credit customers', 'danger')
        
        stats = {
            'total_orders': 0,
            'pending_orders': 0,
            'total_products': 0,
            'total_customers': 0,
            'today_revenue': 0,
            'month_revenue': 0,
            'total_revenue': 0,
            'low_stock': 0,
            'total_bundles': 0,
            'total_cart_items': 0,
            'pos_orders': 0,
            'web_orders': 0,
            'credit_orders': 0,
            'today_growth_pct': 0,
            'month_growth_pct': 0,
            'db_mode': 'offline'
        }
        
        return render_template('admin_credit.html',
            customers=[],
            summary={'total_customers': 0, 'active_customers': 0, 'inactive_customers': 0, 
                    'total_balance': 0, 'total_credit_limit': 0, 'total_purchases': 0, 
                    'total_payments': 0, 'average_balance': 0},
            overdue=[],
            overdue_count=0,
            stats=stats,
            DB_CONNECTED=False,
            IS_VERCEL=IS_VERCEL,
            now=datetime.utcnow()
        )

# ============================================================
# CREDIT API ROUTES
# ============================================================

@admin_bp.route('/admin/api/credit/customers', methods=['GET'])
@admin_required
def api_get_credit_customers():
    try:
        from utils.credit import get_all_credit_customers
        customers = get_all_credit_customers()
        return jsonify({'success': True, 'customers': customers})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/credit/customers', methods=['POST'])
@admin_required
def api_add_credit_customer():
    try:
        from utils.credit import add_credit_customer
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        required = ['full_name', 'phone']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        result = add_credit_customer(data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/credit/customers/<customer_id>', methods=['GET'])
@admin_required
def api_get_credit_customer(customer_id):
    try:
        from utils.credit import get_credit_customer_by_id
        
        print(f"🔍 API called with customer_id: '{customer_id}'")
        
        customer = get_credit_customer_by_id(customer_id)
        
        if customer:
            print(f"✅ Returning customer: {customer.get('full_name')}")
            return jsonify({'success': True, 'customer': customer})
        else:
            print(f"❌ Customer not found: '{customer_id}'")
            return jsonify({'success': False, 'message': 'Customer not found'}), 404
            
    except Exception as e:
        print(f"❌ API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/credit/customers/<customer_id>', methods=['PUT'])
@admin_required
def api_update_credit_customer(customer_id):
    try:
        from utils.credit import update_credit_customer
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        result = update_credit_customer(customer_id, data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/credit/customers/<customer_id>', methods=['DELETE'])
@admin_required
def api_delete_credit_customer(customer_id):
    try:
        from utils.credit import delete_credit_customer
        
        result = delete_credit_customer(customer_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/credit/balance/<customer_id>', methods=['GET'])
@admin_required
def api_get_credit_balance(customer_id):
    try:
        from utils.credit import get_customer_balance
        
        balance = get_customer_balance(customer_id)
        if balance:
            return jsonify({'success': True, 'balance': balance})
        else:
            return jsonify({'success': False, 'message': 'Customer not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# [NEW] CREDIT TRANSACTIONS API - WITH PERIOD FILTERING
# ============================================================

@admin_bp.route('/admin/api/credit/transactions/<customer_id>', methods=['GET'])
@admin_required
def api_get_credit_transactions(customer_id):
    """
    Get credit transactions with period filtering and pagination
    
    Query Parameters:
    - page: int (default 1)
    - per_page: int (default 20)
    - period: 'today' | 'week' | 'month' | 'quarter' | 'year' | 'all' (default 'all')
    - type: 'all' | 'purchase' | 'payment' (default 'all')
    """
    try:
        from utils.credit import get_customer_transactions
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        period = request.args.get('period', 'all')
        txn_type = request.args.get('type', 'all')
        
        # Get all transactions for customer
        all_transactions = get_customer_transactions(customer_id)
        
        if not all_transactions:
            return jsonify({
                'success': True,
                'transactions': [],
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'total_pages': 0
                }
            })



        
        # ============================================================
        # PERIOD FILTERING LOGIC
        # ============================================================
        now = datetime.utcnow()
        today = now.date()
        
        def filter_by_period(tx_date_str):
            if not tx_date_str:
                return True  # Keep if no date
            
            try:
                # Parse date
                if isinstance(tx_date_str, str):
                    if 'T' in tx_date_str:
                        clean = tx_date_str.replace('Z', '').replace('+00:00', '')
                        if '.' in clean:
                            tx_date = datetime.fromisoformat(clean).date()
                        else:
                            tx_date = datetime.strptime(clean[:10], '%Y-%m-%d').date()
                    elif ' ' in tx_date_str:
                        tx_date = datetime.strptime(tx_date_str[:10], '%Y-%m-%d').date()
                    else:
                        tx_date = datetime.strptime(tx_date_str[:10], '%Y-%m-%d').date()
                elif isinstance(tx_date_str, datetime):
                    tx_date = tx_date_str.date()
                else:
                    return True
            except:
                return True
            
            if period == 'today':
                return tx_date == today
            elif period == 'week':
                # Start of week (Monday)
                start_of_week = today - timedelta(days=today.weekday())
                return start_of_week <= tx_date <= today
            elif period == 'month':
                start_of_month = today.replace(day=1)
                return start_of_month <= tx_date <= today
            elif period == 'quarter':
                # Current quarter
                quarter_month = ((today.month - 1) // 3) * 3 + 1
                start_of_quarter = today.replace(month=quarter_month, day=1)
                return start_of_quarter <= tx_date <= today
            elif period == 'year':
                start_of_year = today.replace(month=1, day=1)
                return start_of_year <= tx_date <= today
            else:  # 'all'
                return True
        
        # Filter by period
        filtered_by_period = [t for t in all_transactions if filter_by_period(t.get('created_at', ''))]
        
        # Filter by type
        if txn_type != 'all':
            filtered_by_period = [t for t in filtered_by_period if t.get('transaction_type') == txn_type]
        
        # Sort by date descending (most recent first)
        filtered_by_period.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # ============================================================
        # PAGINATION
        # ============================================================
        total = len(filtered_by_period)
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        start = (page - 1) * per_page
        end = min(start + per_page, total)
        
        paginated_transactions = filtered_by_period[start:end] if total > 0 else []
        
        return jsonify({
            'success': True,
            'transactions': paginated_transactions,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'start': start + 1 if paginated_transactions else 0,
                'end': end
            },
            'filters': {
                'period': period,
                'type': txn_type
            }
        })
        
    except Exception as e:
        print(f"❌ Credit transactions API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


        # ============================================================
# [NEW] CREDIT PRODUCT PURCHASES API
# ============================================================

@admin_bp.route('/admin/api/credit/products/<customer_id>', methods=['GET'])
@admin_required
def api_get_credit_products(customer_id):
    """
    Get all products purchased on credit by a specific customer
    Returns aggregated product data with quantities and totals
    """
    try:
        from utils.credit import get_customer_transactions
        import json
        from datetime import datetime
        
        # Get all transactions for this customer
        transactions = get_customer_transactions(customer_id)
        
        if not transactions:
            return jsonify({
                'success': True,
                'products': [],
                'total_products': 0,
                'total_spent': 0,
                'total_quantity': 0,
                'message': 'No credit purchases found'
            })
        
        # Filter only purchase transactions
        purchases = [t for t in transactions if t.get('transaction_type') == 'purchase']
        
        if not purchases:
            return jsonify({
                'success': True,
                'products': [],
                'total_products': 0,
                'total_spent': 0,
                'total_quantity': 0,
                'message': 'No credit purchases found'
            })
        
        # Extract items from each purchase
        product_map = {}
        
        for purchase in purchases:
            items = purchase.get('items_json', [])
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except:
                    items = []
            
            if not items or not isinstance(items, list):
                continue
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                product_id = item.get('product_id', '')
                product_name = item.get('name', 'Unknown Product')
                quantity = int(item.get('quantity', 1))
                price = float(item.get('price', 0))
                cost_price = float(item.get('cost_price', 0))
                
                total_revenue = price * quantity
                total_cost = cost_price * quantity
                total_profit = total_revenue - total_cost
                
                key = product_id if product_id else product_name
                
                if key not in product_map:
                    product_map[key] = {
                        'product_id': product_id,
                        'name': product_name,
                        'total_quantity': 0,
                        'total_revenue': 0,
                        'total_cost': 0,
                        'total_profit': 0,
                        'avg_price': 0,
                        'last_purchased': None
                    }
                
                product_map[key]['total_quantity'] += quantity
                product_map[key]['total_revenue'] += total_revenue
                product_map[key]['total_cost'] += total_cost
                product_map[key]['total_profit'] += total_profit
                
                created_at = purchase.get('created_at', '')
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            if 'T' in created_at:
                                clean = created_at.replace('Z', '').replace('+00:00', '')
                                if '.' in clean:
                                    dt = datetime.fromisoformat(clean)
                                else:
                                    dt = datetime.strptime(clean[:10], '%Y-%m-%d')
                            else:
                                dt = datetime.strptime(created_at[:10], '%Y-%m-%d')
                        elif isinstance(created_at, datetime):
                            dt = created_at
                        else:
                            dt = datetime.utcnow()
                    except:
                        dt = datetime.utcnow()
                    
                    if product_map[key]['last_purchased'] is None or dt > product_map[key]['last_purchased']:
                        product_map[key]['last_purchased'] = dt
        
        # Convert to list and sort by total revenue
        products_list = []
        total_spent = 0
        total_quantity = 0
        
        for key, data in product_map.items():
            if data['total_quantity'] > 0:
                data['avg_price'] = data['total_revenue'] / data['total_quantity']
            
            if data['last_purchased']:
                data['last_purchased_str'] = data['last_purchased'].strftime('%Y-%m-%d %H:%M')
            else:
                data['last_purchased_str'] = 'N/A'
            
            total_spent += data['total_revenue']
            total_quantity += data['total_quantity']
            products_list.append(data)
        
        products_list.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        return jsonify({
            'success': True,
            'products': products_list,
            'total_products': len(products_list),
            'total_spent': total_spent,
            'total_quantity': total_quantity,
            'customer_id': customer_id
        })
        
    except Exception as e:
        print(f"❌ Error getting credit products: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# CREDIT PURCHASE ROUTE
# ============================================================

@admin_bp.route('/admin/api/credit/purchase', methods=['POST'])
@admin_required
def api_record_credit_purchase():
    try:
        from utils.credit import record_credit_purchase
        import re
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        required = ['customer_id', 'items', 'total_amount', 'staff_name']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        print(f"📤 Record credit purchase - customer_id: {data.get('customer_id')}")
        print(f"📤 Total amount: {data.get('total_amount')}")
        
        items_data = data.get('items', '')
        print(f"📦 Items type: {type(items_data)}")
        print(f"📦 Items: {items_data}")
        
        if isinstance(items_data, list):
            items_list = items_data
            print(f"📦 Items is a LIST: {items_list}")
        else:
            items_str = items_data
            items_list = []
            for item_str in items_str.split(', '):
                match = re.match(r'(.+?) x(\d+)$', item_str.strip())
                if match:
                    product_name = match.group(1).strip()
                    quantity = int(match.group(2))
                    
                    prod_response = requests.get(
                        f"{Config.SUPABASE_URL}/rest/v1/products?name=ilike.%25{product_name}%25",
                        headers=Config.SUPABASE_HEADERS,
                        timeout=10
                    )
                    if prod_response.status_code == 200:
                        products = prod_response.json()
                        if products:
                            items_list.append({
                                'product_id': products[0].get('id'),
                                'name': product_name,
                                'quantity': quantity,
                                'price': float(products[0].get('price', 0))
                            })
        
        # STOCK DEDUCTION
        print(f"📦 Processing {len(items_list)} items for stock deduction...")
        
        for item in items_list:
            product_id = item.get('product_id')
            quantity = int(item.get('quantity', 1))
            
            if not product_id:
                print(f"⚠️ No product_id for item: {item.get('name')}")
                continue
            
            response = requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                headers=Config.SUPABASE_HEADERS,
                timeout=10
            )
            
            if response.status_code == 200:
                products = response.json()
                if products:
                    product = products[0]
                    current_stock = product.get('stock', 0)
                    new_stock = max(0, current_stock - quantity)
                    
                    print(f"📦 {item.get('name')}: {current_stock} → {new_stock}")
                    
                    update_response = requests.patch(
                        f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                        headers=Config.SUPABASE_HEADERS,
                        json={'stock': new_stock},
                        timeout=10
                    )
        
        # Record credit purchase (this now also creates order entry)
        result = record_credit_purchase(
            customer_id=data['customer_id'],
            items=items_list,
            total_amount=float(data['total_amount']),
            staff_name=data['staff_name'],
            notes=data.get('notes', '')
        )
        
        print(f"📥 Result: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ API error: {e}")
        import traceback
        traceback.print_exc()

        try:
            from utils.credit import save_credit_order_offline

            safe_data = locals().get('data') or {}
            order_data = {
                'order_id': f'CREDIT-OFFLINE-{uuid.uuid4().hex[:8].upper()}',
                'customer_id': safe_data.get('customer_id'),
                'items': safe_data.get('items', []),
                'total_amount': float(safe_data.get('total_amount', 0) or 0),
                'staff_name': safe_data.get('staff_name', 'System'),
                'notes': safe_data.get('notes', 'Offline credit order (network fallback)')
            }

            result = save_credit_order_offline(order_data)
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'queued': True,
                    'message': 'Credit purchase saved offline. It will sync when the connection is available.',
                    'order_id': order_data['order_id']
                })
        except Exception as fallback_error:
            print(f"❌ Offline fallback failed: {fallback_error}")

        return jsonify({
            'success': False,
            'message': str(e),
            'error': str(e)
        }), 500

# ============================================================
# CREDIT PAYMENT ROUTE
# ============================================================

@admin_bp.route('/admin/api/credit/payment', methods=['POST'])
@admin_required
def api_record_credit_payment():
    try:
        from utils.credit import record_credit_payment, get_customer_balance
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        required = ['customer_id', 'amount', 'staff_name']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        customer_id = data['customer_id']
        amount = float(data['amount'])
        
        balance_info = get_customer_balance(customer_id)
        if balance_info:
            current_balance = balance_info.get('current_balance', 0)
            if amount > current_balance:
                return jsonify({
                    'success': False,
                    'message': f'❌ Payment exceeds balance. Balance: KSh {current_balance:,.2f}',
                    'current_balance': current_balance,
                    'payment_amount': amount
                }), 400
        
        result = record_credit_payment(
            customer_id=customer_id,
            amount=amount,
            staff_name=data['staff_name'],
            notes=data.get('notes', '')
        )
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# OTHER CREDIT ROUTES
# ============================================================

@admin_bp.route('/admin/api/credit/monthly-report', methods=['GET'])
@admin_required
def api_get_monthly_credit_report():
    try:
        from utils.credit import get_monthly_credit_report
        
        year = request.args.get('year', type=int)
        report = get_monthly_credit_report(year)
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/credit/overdue', methods=['GET'])
@admin_required
def api_get_overdue_customers():
    try:
        from utils.credit import get_overdue_customers
        
        overdue = get_overdue_customers()
        return jsonify({'success': True, 'overdue': overdue, 'count': len(overdue)})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/credit/summary', methods=['GET'])
@admin_required
def api_get_credit_summary():
    try:
        from utils.credit import get_credit_summary
        
        summary = get_credit_summary()
        return jsonify({'success': True, 'summary': summary})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/credit/transaction/<transaction_id>', methods=['PUT', 'PATCH'])
@admin_required
def api_update_credit_transaction(transaction_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        print(f"📤 Updating transaction: {transaction_id}")
        print(f"📤 Data: {data}")
        
        clean_data = {}
        allowed_fields = ['total_cost', 'profit', 'profit_margin', 'notes', 'payment_status']
        for field in allowed_fields:
            if field in data and data[field] is not None:
                clean_data[field] = data[field]
        
        if not clean_data:
            return jsonify({'success': False, 'message': 'No valid fields to update'}), 400
        
        response = requests.patch(
            f"{Config.SUPABASE_URL}/rest/v1/credit_transactions?transaction_id=eq.{transaction_id}",
            headers=Config.SUPABASE_HEADERS,
            json=clean_data,
            timeout=30
        )
        
        if response.status_code in [200, 204]:
            print(f"✅ Transaction {transaction_id} updated successfully")
            return jsonify({
                'success': True,
                'message': 'Transaction updated successfully',
                'data': clean_data
            })
        else:
            print(f"❌ Failed to update transaction: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'message': f'Failed to update: {response.status_code}'
            }), 500
            
    except Exception as e:
        print(f"❌ Error updating transaction: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# [NEW] SUPPLIER-RELATED API ROUTES
# ============================================================

@admin_bp.route('/admin/api/suppliers', methods=['GET'])
@admin_required
def api_get_suppliers():
    try:
        from utils.supplier import get_all_suppliers
        suppliers = get_all_suppliers()
        return jsonify({'success': True, 'suppliers': suppliers})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/suppliers', methods=['POST'])
@admin_required
def api_add_supplier():
    try:
        from utils.supplier import add_supplier
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        required = ['business_name', 'phone']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        result = add_supplier(data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/suppliers/<supplier_id>', methods=['GET'])
@admin_required
def api_get_supplier(supplier_id):
    try:
        from utils.supplier import get_supplier_by_id
        
        supplier = get_supplier_by_id(supplier_id)
        if supplier:
            return jsonify({'success': True, 'supplier': supplier})
        else:
            return jsonify({'success': False, 'message': 'Supplier not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/suppliers/<supplier_id>', methods=['PUT'])
@admin_required
def api_update_supplier(supplier_id):
    try:
        from utils.supplier import update_supplier
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        result = update_supplier(supplier_id, data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/suppliers/<supplier_id>', methods=['DELETE'])
@admin_required
def api_delete_supplier(supplier_id):
    try:
        from utils.supplier import delete_supplier
        
        result = delete_supplier(supplier_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/suppliers/low-stock', methods=['GET'])
@admin_required
def api_get_low_stock():
    try:
        from utils.supplier import get_low_stock_products
        
        supplier_id = request.args.get('supplier_id')
        low_stock = get_low_stock_products(supplier_id)
        return jsonify({'success': True, 'low_stock': low_stock, 'count': len(low_stock)})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/suppliers/summary', methods=['GET'])
@admin_required
def api_get_supplier_summary():
    try:
        from utils.supplier import get_supplier_summary
        
        summary = get_supplier_summary()
        return jsonify({'success': True, 'summary': summary})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# USER MANAGEMENT API
# ============================================================

@admin_bp.route('/api/users', methods=['POST'])
@admin_bp.route('/admin/api/users', methods=['POST'])
@admin_required
def api_add_user():
    try:
        data = request.get_json(silent=True) or {}

        full_name = (data.get('full_name') or '').strip()
        email = (data.get('email') or '').strip()
        role = (data.get('role') or 'user').strip()
        password = (data.get('password') or '').strip()

        if not full_name or not email or not password:
            return jsonify({'success': False, 'message': 'Name, email, and password are required'}), 400

        if User.get_by_email(email):
            return jsonify({'success': False, 'message': 'A user with this email already exists'}), 409

        user_payload = {
            'id': str(uuid.uuid4()),
            'email': email,
            'full_name': full_name,
            'role': role if role in ['admin', 'manager', 'pos', 'user'] else 'user',
            'password_hash': User.hash_password(password),
            'is_active': True,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        response = requests.post(
            f"{Config.SUPABASE_URL}/rest/v1/users",
            headers=Config.SUPABASE_HEADERS,
            json=user_payload,
            timeout=10
        )

        if response.status_code not in (200, 201):
            print(f"❌ Failed to create user: {response.status_code} - {response.text}")
            return jsonify({'success': False, 'message': 'Could not create user'}), 500

        return jsonify({
            'success': True,
            'message': f'User "{full_name}" added successfully',
            'user': {
                'email': email,
                'full_name': full_name,
                'role': user_payload['role']
            }
        })

    except Exception as e:
        print(f"❌ Error creating user: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# [NEW] CATEGORIES API - DYNAMIC
# ============================================================

@admin_bp.route('/api/categories', methods=['GET'])
@admin_bp.route('/admin/api/categories', methods=['GET'])
@admin_required
def api_get_categories():
    """Get all categories dynamically from products, plus locally saved custom categories."""
    try:
        local_data = load_json_data() or {}
        stored_categories = local_data.get('categories', []) or []
        if isinstance(stored_categories, dict):
            stored_categories = list(stored_categories.keys())
        elif not isinstance(stored_categories, list):
            stored_categories = []

        categories = {}
        for cat in stored_categories:
            cat_name = str(cat).strip()
            if cat_name:
                categories[cat_name] = {'name': cat_name, 'count': 0}

        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/products?select=category",
            headers=Config.SUPABASE_HEADERS,
            timeout=10
        )

        if response.status_code == 200:
            products = response.json() or []
            for p in products:
                cat = str(p.get('category', '') or '').strip()
                if not cat:
                    continue
                if cat not in categories:
                    categories[cat] = {'name': cat, 'count': 0}
                categories[cat]['count'] += 1

        if not categories:
            categories = {
                'General': {'name': 'General', 'count': 0}
            }

        return jsonify(categories)

    except Exception as e:
        print(f"❌ Error loading categories: {e}")
        return jsonify({
            'General': {'name': 'General', 'count': 0}
        })

@admin_bp.route('/api/categories', methods=['POST'])
@admin_bp.route('/admin/api/categories', methods=['POST'])
@admin_required
def api_add_category():
    """Add a new category and persist it locally so it appears in the category list."""
    try:
        data = request.get_json() or {}
        if not data or not data.get('name'):
            return jsonify({'success': False, 'message': 'Category name required'}), 400

        category_name = str(data['name']).strip()
        if not category_name:
            return jsonify({'success': False, 'message': 'Category name cannot be empty'}), 400

        local_data = load_json_data() or {}
        stored_categories = local_data.get('categories', []) or []
        if isinstance(stored_categories, dict):
            stored_categories = list(stored_categories.keys())
        elif not isinstance(stored_categories, list):
            stored_categories = []

        stored_categories = [str(cat).strip() for cat in stored_categories if str(cat).strip()]
        if category_name not in stored_categories:
            stored_categories.append(category_name)
            stored_categories = sorted(stored_categories)
            local_data['categories'] = stored_categories
            save_json_data(local_data)

        return jsonify({
            'success': True,
            'message': f'Category "{category_name}" added',
            'category': {'name': category_name}
        })

    except Exception as e:
        print(f"❌ Error adding category: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# [NEW] ANALYTICS API - WITH CREDIT DATA MERGED
# ============================================================

@admin_bp.route('/admin/api/analytics')
def admin_api_analytics():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    orders = load_orders()
    analytics = calculate_analytics_from_orders(orders)
    
    monthly_data = analytics.get('monthly_data', {})
    product_sales = analytics.get('product_sales', {})
    
    # ============================================================
    # CREDIT DATA - FOR REPORTING ONLY (NOT ADDED TO TOTALS)
    # ============================================================
    try:
        from utils.credit import get_all_credit_transactions
        
        credit_transactions = get_all_credit_transactions()
        
        credit_sales = 0
        credit_cost = 0
        credit_profit = 0
        
        for tx in credit_transactions:
            if tx.get('transaction_type') == 'purchase':
                amount = float(tx.get('amount', 0))
                cost = float(tx.get('total_cost', 0))
                profit = float(tx.get('profit', 0))
                credit_sales += amount
                credit_cost += cost
                credit_profit += profit
        
        total_revenue = analytics.get('total_revenue', 0)
        total_cost = analytics.get('total_cost', 0)
        total_profit = analytics.get('total_profit', 0)
        
        analytics['monthly_data'] = monthly_data
        analytics['product_sales'] = product_sales
        analytics['total_revenue'] = total_revenue
        analytics['total_cost'] = total_cost
        analytics['total_profit'] = total_profit
        analytics['credit_sales'] = credit_sales
        analytics['credit_cost'] = credit_cost
        analytics['credit_profit'] = credit_profit
        analytics['cash_sales'] = total_revenue - credit_sales
        
        if total_revenue > 0:
            analytics['credit_percentage'] = round((credit_sales / total_revenue) * 100, 2)
            analytics['profit_margin'] = round((total_profit / total_revenue) * 100, 2)
        else:
            analytics['credit_percentage'] = 0
            analytics['profit_margin'] = 0
        
        print(f"✅ Merged Analytics: Cash: KSh {analytics['cash_sales']}, Credit: KSh {credit_sales}, Total: KSh {total_revenue}, Margin: {analytics['profit_margin']}%")
        
    except Exception as e:
        print(f"⚠️ Error merging credit data: {e}")
        import traceback
        traceback.print_exc()

    # ============================================================
    # ORDER STATUS COUNTS  ← NEW
    # ============================================================
    status_counts = {
        'pending': 0,
        'confirmed': 0,
        'shipped': 0,
        'delivered': 0,
        'completed': 0,
        'cancelled': 0,
        'returned': 0
    }
    for order in orders:
        s = (order.get('status') or 'pending').lower()
        if s in status_counts:
            status_counts[s] += 1
        else:
            status_counts[s] = status_counts.get(s, 0) + 1

    analytics['status_counts'] = status_counts

    # ============================================================
    # PAYMENT METHOD COUNTS  ← NEW
    # ============================================================
    payment_counts = {}
    payment_revenue = {}
    for order in orders:
        if order.get('status') == 'cancelled':
            continue
        pm = (order.get('payment_method') or 'cash').lower()
        payment_counts[pm] = payment_counts.get(pm, 0) + 1
        payment_revenue[pm] = payment_revenue.get(pm, 0) + float(order.get('total', 0) or 0)

    analytics['payment_methods'] = payment_counts
    analytics['payment_methods_revenue'] = payment_revenue

    print(f"✅ Status counts: {status_counts}")
    print(f"✅ Payment methods: {payment_counts}")

    return jsonify(analytics)   # ← the only return, at the end

# ============================================================
# REVENUE API
# ============================================================

@admin_bp.route('/admin/api/revenue')
def admin_api_revenue():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        orders = load_orders()
        now = datetime.utcnow()
        today = now.date()
        first_day_this_month = today.replace(day=1)

        if today.month == 1:
            last_month_year = today.year - 1
            last_month_month = 12
        else:
            last_month_year = today.year
            last_month_month = today.month - 1

        first_day_last_month = datetime(last_month_year, last_month_month, 1).date()
        if today.month == 1:
            last_day_last_month = datetime(last_month_year, 12, 31).date()
        else:
            last_day_last_month = datetime(today.year, today.month, 1).date() - timedelta(days=1)

        today_revenue = 0
        today_orders = 0
        yesterday_revenue = 0
        month_revenue = 0
        month_orders = 0
        last_month_revenue = 0

        for order in orders:
            total = order.get('total', 0)
            if isinstance(total, str):
                try:
                    total = float(total.replace(',', ''))
                except:
                    total = 0
            total = float(total or 0)

            if order.get('status') == 'cancelled':
                continue

            created_at = order.get('created_at', '')
            if not created_at:
                continue

            try:
                if isinstance(created_at, datetime):
                    order_date = created_at.date()
                elif isinstance(created_at, str):
                    if 'T' in created_at:
                        clean = created_at.replace('Z', '').replace('+00:00', '')
                        if '.' in clean:
                            order_date = datetime.fromisoformat(clean).date()
                        else:
                            order_date = datetime.strptime(clean[:10], '%Y-%m-%d').date()
                    elif ' ' in created_at:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                    else:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                else:
                    continue
            except Exception as e:
                print(f"Date parse error: {e}")
                continue

            if order_date == today:
                today_revenue += total
                today_orders += 1

            if order_date == today - timedelta(days=1):
                yesterday_revenue += total

            if order_date >= first_day_this_month:
                month_revenue += total
                month_orders += 1

            if first_day_last_month <= order_date <= last_day_last_month:
                last_month_revenue += total

        if yesterday_revenue > 0:
            today_growth = round(((today_revenue - yesterday_revenue) / yesterday_revenue) * 100, 1)
        else:
            today_growth = 100.0 if today_revenue > 0 else 0

        if last_month_revenue > 0:
            month_growth = round(((month_revenue - last_month_revenue) / last_month_revenue) * 100, 1)
        else:
            month_growth = 100.0 if month_revenue > 0 else 0

        total_revenue = sum(order_revenue_value(order) for order in orders if order.get('status') != 'cancelled')

        return jsonify({
            "total_revenue": total_revenue,
            "total_cost": 0,
            "total_profit": 0,
            "total_orders": len(orders),
            "total_items_sold": 0,
            "today_revenue": today_revenue,
            "today_orders": today_orders,
            "yesterday_revenue": yesterday_revenue,
            "month_revenue": month_revenue,
            "month_orders": month_orders,
            "last_month_revenue": last_month_revenue,
            "today_growth_pct": today_growth,
            "month_growth_pct": month_growth
        })

    except Exception as exc:
        print(f'❌ Revenue API error: {exc}')
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500

# ============================================================
# CALCULATE ANALYTICS
# ============================================================

def calculate_analytics_from_orders(orders):
    if not orders:
        return {
            'total_revenue': 0,
            'total_cost': 0,
            'total_profit': 0,
            'total_orders': 0,
            'total_items_sold': 0,
            'pos_orders_count': 0,
            'web_orders_count': 0,
            'credit_orders_count': 0,
            'product_sales': {},
            'category_sales': {},
            'monthly_data': {}
        }

    products = load_products()
    product_lookup = {str(p.get('id')): p for p in products if p and p.get('id')}

    total_revenue = 0
    total_cost = 0
    total_profit = 0
    total_items_sold = 0
    pos_orders_count = 0
    web_orders_count = 0
    credit_orders_count = 0
    product_sales = {}
    category_sales = {}
    monthly_data = {}

    ACTIVE_STATUSES = ['pending', 'processing', 'confirmed', 'shipped', 'delivered', 'completed']
    active_orders = [o for o in orders if o.get('status', '') in ACTIVE_STATUSES]

    for order in active_orders:
        if order.get('source') == 'pos':
            pos_orders_count += 1
        elif order.get('source') == 'credit':
            credit_orders_count += 1
        else:
            web_orders_count += 1

        created_at = order.get('created_at', '')
        month_key = 'Unknown'
        if created_at:
            try:
                if isinstance(created_at, str):
                    if 'T' in created_at:
                        clean = created_at.replace('Z', '').replace('+00:00', '')
                        if '.' in clean:
                            dt = datetime.fromisoformat(clean)
                        else:
                            dt = datetime.strptime(clean[:10], '%Y-%m-%d')
                    elif ' ' in created_at:
                        dt = datetime.strptime(created_at[:10], '%Y-%m-%d')
                    else:
                        dt = datetime.strptime(created_at[:10], '%Y-%m-%d')
                elif isinstance(created_at, datetime):
                    dt = created_at
                else:
                    dt = datetime.utcnow()
                month_key = dt.strftime('%b %Y')
            except:
                month_key = 'Unknown'

        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'orders': 0,
                'items': 0,
                'revenue': 0,
                'cost': 0,
                'profit': 0,
                'margin': 0
            }
        monthly_data[month_key]['orders'] += 1

        order_total = 0
        order_cost = 0
        order_items = 0

        for item in order.get('items', []):
            quantity = item.get('quantity', 1)
            price = float(item.get('price', 0) or 0)
            total_items_sold += quantity
            order_items += quantity

            item_total = price * quantity
            order_total += item_total
            total_revenue += item_total

            cost_price = 0

            if 'cost_price' in item:
                try:
                    cost_price = float(item.get('cost_price', 0) or 0)
                except (ValueError, TypeError):
                    cost_price = 0

            if cost_price == 0:
                product_id = item.get('product_id', '')
                if product_id:
                    product = product_lookup.get(product_id, {})
                    if product:
                        cost_price = float(product.get('cost_price', 0) or 0)

            if cost_price == 0 and price > 0:
                cost_price = price * 0.7

            item_cost = cost_price * quantity
            order_cost += item_cost
            total_cost += item_cost
            total_profit += (item_total - item_cost)

            product_id = item.get('product_id', '')
            category = 'Uncategorized'
            if product_id:
                product = product_lookup.get(product_id, {})
                if product and product.get('category'):
                    category = product.get('category')

            product_name = item.get('name', 'Unknown Product')
            if product_name not in product_sales:
                product_sales[product_name] = {
                    'quantity': 0,
                    'revenue': 0,
                    'cost': 0,
                    'profit': 0,
                    'margin': 0
                }
            product_sales[product_name]['quantity'] += quantity
            product_sales[product_name]['revenue'] += item_total
            product_sales[product_name]['cost'] += item_cost
            product_sales[product_name]['profit'] += (item_total - item_cost)

            if category not in category_sales:
                category_sales[category] = {
                    'quantity': 0,
                    'revenue': 0,
                    'cost': 0,
                    'profit': 0,
                    'margin': 0
                }
            category_sales[category]['quantity'] += quantity
            category_sales[category]['revenue'] += item_total
            category_sales[category]['cost'] += item_cost
            category_sales[category]['profit'] += (item_total - item_cost)

        monthly_data[month_key]['items'] += order_items
        monthly_data[month_key]['revenue'] += order_total
        monthly_data[month_key]['cost'] += order_cost
        monthly_data[month_key]['profit'] += (order_total - order_cost)

    for product in product_sales.values():
        if product['revenue'] > 0:
            product['margin'] = round((product['profit'] / product['revenue']) * 100, 1)

    for category in category_sales.values():
        if category['revenue'] > 0:
            category['margin'] = round((category['profit'] / category['revenue']) * 100, 1)

    for month in monthly_data.values():
        if month['revenue'] > 0:
            month['margin'] = round((month['profit'] / month['revenue']) * 100, 1)

    sorted_products = sorted(
        product_sales.items(),
        key=lambda x: x[1]['profit'],
        reverse=True
    )
    product_sales = dict(sorted_products)

    return {
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'total_orders': len(active_orders),
        'total_items_sold': total_items_sold,
        'pos_orders_count': pos_orders_count,
        'web_orders_count': web_orders_count,
        'credit_orders_count': credit_orders_count,
        'product_sales': product_sales,
        'category_sales': category_sales,
        'monthly_data': monthly_data
    }

# ============================================================
# API ROUTES - LEGACY SUPPORT
# ============================================================

@admin_bp.route('/api/products/<product_id>', methods=['GET'])
def api_get_product(product_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        products = load_products()
        for product in products:
            if str(product.get('id')) == str(product_id):
                return jsonify(product)
        return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/orders/<order_id>', methods=['GET'])
def api_get_order(order_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        orders = load_orders()

        for order in orders:
            if str(order.get('order_id')) == str(order_id):
                customer = order.get('customer', {})
                if isinstance(customer, str):
                    try:
                        customer = json.loads(customer) if customer else {}
                    except:
                        customer = {}
                if isinstance(customer, list):
                    customer = customer[0] if customer else {}
                if not isinstance(customer, dict):
                    customer = {}

                items = order.get('items', [])
                if isinstance(items, str):
                    try:
                        items = json.loads(items)
                    except:
                        items = []
                if not isinstance(items, list):
                    items = []

                formatted_items = []
                for item in items:
                    if isinstance(item, dict):
                        formatted_items.append({
                            'name': item.get('name', 'Product'),
                            'quantity': item.get('quantity', 1),
                            'price': item.get('price', 0),
                            'total': item.get('total', item.get('price', 0) * item.get('quantity', 1))
                        })

                return jsonify({
                    'order_id': order.get('order_id', 'N/A'),
                    'customer': {
                        'name': customer.get('name', order.get('customer_name', 'Customer')),
                        'email': customer.get('email', order.get('customer_email', 'N/A')),
                        'phone': customer.get('phone', order.get('customer_phone', 'N/A')),
                        'address': customer.get('address', order.get('customer_address', 'N/A')),
                    },
                    'items': formatted_items,
                    'subtotal': order.get('subtotal', 0),
                    'shipping': order.get('shipping', 0),
                    'total': order.get('total', 0),
                    'status': order.get('status', 'pending'),
                    'created_at': order.get('created_at', ''),
                    'source': order.get('source', 'web'),
                    'payment_method': order.get('payment_method', order.get('payment_type', 'Cash')),
                    'payment_status': order.get('payment_status', 'pending'),
                    'location': order.get('location', order.get('customer_address', 'N/A')),
                    'delivery_zone': order.get('delivery_zone', ''),
                    'distance_km': order.get('distance_km', 0),
                    'delivery_notes': order.get('delivery_notes', ''),
                })
        return jsonify({'error': 'Order not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/customers', methods=['GET'])
def api_customers():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/customers",
            headers=Config.SUPABASE_HEADERS,
            timeout=10,
        )

        if response.status_code == 200:
            customers_from_db = response.json()
            if customers_from_db:
                result = []
                for c in customers_from_db:
                    result.append({
                        'name': c.get('name', ''),
                        'email': c.get('email', 'N/A'),
                        'phone': c.get('phone', 'N/A'),
                        'orders': 0,
                        'total_spent': 0
                    })
                return jsonify(result)

        orders = load_orders()
        customer_dict = {}

        for order in orders:
            name = None

            if order.get('customer_name'):
                name = order.get('customer_name')

            if not name:
                customer = order.get('customer', {})
                if isinstance(customer, dict):
                    name = customer.get('name')
                elif isinstance(customer, str):
                    try:
                        customer_obj = json.loads(customer)
                        name = customer_obj.get('name')
                    except:
                        pass

            if not name or name in ['Walk-in Customer', 'Web Customer', 'Customer', '']:
                continue

            email = order.get('customer_email', 'N/A')
            phone = order.get('customer_phone', 'N/A')

            if name not in customer_dict:
                customer_dict[name] = {
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'orders': 0,
                    'total_spent': 0
                }
            customer_dict[name]['orders'] += 1
            customer_dict[name]['total_spent'] += order.get('total', 0)

        return jsonify(list(customer_dict.values()))

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================
# SALES STATS API
# ============================================================

@admin_bp.route('/admin/api/sales-stats', methods=['GET'])
def api_sales_stats():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        orders = load_orders()
        products = load_products()
        today = datetime.utcnow().date()

        today_revenue = 0
        today_orders = 0
        today_returns = 0
        today_return_amount = 0
        credit_sales = 0
        credit_orders = 0
        all_customers = set()

        for order in orders:
            created_at = order.get('created_at', '')
            if not created_at:
                continue

            try:
                order_date = None
                if isinstance(created_at, str):
                    if 'T' in created_at:
                        clean = created_at.replace('Z', '').replace('+00:00', '')
                        if '.' in clean:
                            order_date = datetime.fromisoformat(clean).date()
                        else:
                            order_date = datetime.strptime(clean[:10], '%Y-%m-%d').date()
                    elif ' ' in created_at:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                    else:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d').date()
                elif isinstance(created_at, datetime):
                    order_date = created_at.date()
                else:
                    continue

                customer = order.get('customer', {})
                customer_name = None
                if isinstance(customer, dict):
                    customer_name = customer.get('name', '')
                elif isinstance(customer, str):
                    try:
                        c = json.loads(customer)
                        customer_name = c.get('name', '')
                    except:
                        pass

                if customer_name and customer_name not in ['Walk-in Customer', 'Web Customer', '']:
                    all_customers.add(customer_name)

                if order_date == today:
                    status = order.get('status', '')
                    total = float(order.get('total', 0))
                    order_source = order.get('source', '')
                    is_credit_order = order.get('is_credit') is True or order_source == 'credit'

                    if status == 'returned':
                        today_returns += 1
                        today_return_amount += abs(total)
                        today_revenue += total
                    elif status != 'cancelled':
                        today_revenue += total
                        today_orders += 1

                        if is_credit_order:
                            credit_sales += total
                            credit_orders += 1

            except Exception as e:
                print(f"Error processing order: {e}")
                continue

        total_products = len(products)
        
        low_stock_count = 0
        out_of_stock_count = 0
        for p in products:
            stock = p.get('stock', 0)
            if stock is None:
                stock = 0
            if stock < 10 and stock > 0:
                low_stock_count += 1
            elif stock == 0:
                out_of_stock_count += 1

        return jsonify({
            'success': True,
            'today_revenue': today_revenue,
            'today_orders': today_orders,
            'today_returns': today_returns,
            'today_return_amount': today_return_amount,
            'credit_sales': credit_sales,
            'credit_orders': credit_orders,
            'total_customers': len(all_customers),
            'total_products': total_products,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count
        })
    except Exception as e:
        print(f"❌ Sales stats error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# PRODUCT MANAGEMENT - LEGACY
# ============================================================

@admin_bp.route('/admin/products', methods=['POST'])
def admin_products():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = {
                'id': request.form.get('id', '').strip(),
                'name': request.form.get('name', '').strip(),
                'price': float(request.form.get('price', 0) or 0),
                'cost_price': float(request.form.get('cost_price', 0) or 0),
                'image': request.form.get('image', '').strip(),
                'category': request.form.get('category', '').strip(),
                'description': request.form.get('description', '').strip(),
                'rating': float(request.form.get('rating', 4.0) or 4.0),
                'reviews': int(request.form.get('reviews', 0) or 0),
                'badge': request.form.get('badge', '').strip(),
                'stock': int(request.form.get('stock', 0) or 0),
                'original_price': float(request.form.get('original_price', 0) or 0) or None,
                'specs': [s.strip() for s in request.form.get('specs', '').split(',') if s.strip()],
                'barcode': request.form.get('barcode', '').strip() or '',
                'supplier_id': request.form.get('supplier_id', '').strip() or None
            }

        product_id = data.get('id', '').strip()
        if not product_id:
            return jsonify({'success': False, 'message': 'Product ID is required'}), 400

        response = requests.post(
            f"{Config.SUPABASE_URL}/rest/v1/products",
            headers=Config.SUPABASE_HEADERS,
            json=data,
            timeout=10,
        )

        if response.status_code in [200, 201]:
            import utils.data
            utils.data.products_cache = []
            return jsonify({
                'success': True,
                'message': 'Product saved successfully!',
                'product': data
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Error saving product: {response.status_code}'
            }), 500

    except Exception as exc:
        print(f'❌ Product save error: {exc}')
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(exc)}), 500

@admin_bp.route('/admin/products/<product_id>', methods=['DELETE'])
def admin_delete_product(product_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        response = requests.delete(
            f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
            headers=Config.SUPABASE_HEADERS,
            timeout=5,
        )
        if response.status_code in [200, 204]:
            import utils.data
            utils.data.products_cache = []
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Failed to delete'})
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)})

@admin_bp.route('/admin/upload-image', methods=['POST'])
def upload_image():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    if file and allowed_file(file.filename):
        filename = f"{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        image_url = f"/static/uploads/{filename}"
        return jsonify({'success': True, 'url': image_url, 'message': 'Image uploaded successfully!'})
    return jsonify({'success': False, 'message': 'Invalid file type'}), 400

@admin_bp.route('/admin/orders/<order_id>/status', methods=['POST'])
def admin_update_order_status(order_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        new_status = request.json.get('status')
        if not new_status:
            return jsonify({'success': False, 'message': 'Status required'}), 400
        response = requests.patch(
            f"{Config.SUPABASE_URL}/rest/v1/orders?order_id=eq.{order_id}",
            headers=Config.SUPABASE_HEADERS,
            json={'status': new_status},
            timeout=5,
        )
        if response.status_code in [200, 204]:
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Failed to update status'})
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 500

# ============================================================
# PWA ROUTES - PUBLIC
# ============================================================

@admin_bp.route('/offline.html')
def offline_page():
    try:
        return render_template('offline.html')
    except Exception as e:
        print(f"❌ Error serving offline.html: {e}")
        return "Offline page not found", 404

@admin_bp.route('/sw.js')
def service_worker():
    try:
        return send_from_directory('static', 'sw.js', mimetype='application/javascript')
    except Exception as e:
        print(f"❌ Error serving sw.js: {e}")
        return "Service Worker not found", 404

@admin_bp.route('/manifest.json')
def manifest():
    try:
        return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')
    except Exception as e:
        print(f"❌ Error serving manifest.json: {e}")
        return "Manifest not found", 404

@admin_bp.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory('static/icons', 'favicon.ico', mimetype='image/x-icon')
    except Exception as e:
        print(f"⚠️ Favicon not found: {e}")
        return "", 204

@admin_bp.route('/static/<path:filename>')
def static_files(filename):
    try:
        return send_from_directory('static', filename)
    except Exception as e:
        print(f"❌ Error serving static file: {e}")
        return "File not found", 404

# ============================================================
# OFFLINE STATUS API
# ============================================================

@admin_bp.route('/api/offline-status', methods=['GET'])
def api_offline_status():
    try:
        from utils.storage import load_json_data
        json_data = load_json_data()
        
        credit_queue = json_data.get('credit_order_queue', [])
        payment_queue = json_data.get('credit_payment_queue', [])
        order_queue = json_data.get('order_queue', [])
        
        return jsonify({
            'success': True,
            'credit_order_queue': credit_queue,
            'credit_payment_queue': payment_queue,
            'order_queue': order_queue,
            'total_offline': len(credit_queue) + len(payment_queue) + len(order_queue)
        })
    except Exception as e:
        print(f"❌ Offline status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# SYNC OFFLINE CREDIT ORDERS
# ============================================================

@admin_bp.route('/admin/api/credit/sync-offline', methods=['GET', 'POST'])
@admin_required
def api_sync_credit_offline():
    try:
        from utils.credit import sync_credit_orders_offline, record_credit_payment, get_customer_balance
        from utils.storage import load_json_data, save_json_data
        
        print("🔄 Syncing offline credit orders...")
        
        order_result = sync_credit_orders_offline()
        
        json_data = load_json_data()
        payment_queue = json_data.get('credit_payment_queue', [])
        
        synced_payments = 0
        failed_payments = 0
        synced_payment_ids = []
        
        if payment_queue:
            for payment in payment_queue:
                try:
                    customer_id = payment.get('customer_id')
                    amount = float(payment.get('amount'))
                    payment_id = payment.get('payment_id', f"payment-{customer_id}-{len(synced_payment_ids) + 1}")
                    
                    balance_info = get_customer_balance(customer_id)
                    if balance_info:
                        current_balance = balance_info.get('current_balance', 0)
                        if amount > current_balance:
                            print(f"⚠️ Skipping payment {payment_id}: Amount {amount} exceeds balance {current_balance}")
                            failed_payments += 1
                            continue
                    
                    result = record_credit_payment(
                        customer_id=customer_id,
                        amount=amount,
                        staff_name=payment.get('staff_name', 'System'),
                        notes=payment.get('notes', 'Offline payment')
                    )
                    if result.get('success'):
                        synced_payments += 1
                        synced_payment_ids.append(payment_id)
                        print(f"✅ Synced payment for: {customer_id}")
                    else:
                        failed_payments += 1
                        print(f"⚠️ Failed to sync payment for: {customer_id}")
                except Exception as e:
                    failed_payments += 1
                    print(f"❌ Error syncing payment: {e}")
            
            json_data['credit_payment_queue'] = [
                p for p in payment_queue
                if p.get('payment_id') not in synced_payment_ids
            ]
            save_json_data(json_data)
        
        return jsonify({
            'success': True,
            'orders_synced': order_result.get('synced', 0),
            'orders_failed': order_result.get('failed', 0),
            'payments_synced': synced_payments,
            'payments_failed': failed_payments,
            'message': f"Orders: {order_result.get('synced', 0)} synced, {order_result.get('failed', 0)} failed. Payments: {synced_payments} synced, {failed_payments} failed."
        })
        
    except Exception as e:
        print(f"❌ Sync error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# CREDIT PROFIT API ROUTES
# ============================================================

@admin_bp.route('/admin/api/credit/profit/<customer_id>', methods=['GET'])
@admin_required
def api_credit_profit_details(customer_id):
    try:
        from utils.credit import get_customer_profit_summary, get_customer_transactions
        
        summary = get_customer_profit_summary(customer_id)
        transactions = get_customer_transactions(customer_id)
        
        if summary.get('success'):
            return jsonify({
                'success': True,
                'summary': summary,
                'transactions': transactions[:20]
            })
        else:
            return jsonify({'success': False, 'message': summary.get('message', 'Customer not found')}), 404
            
    except Exception as e:
        print(f"❌ Profit details error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/credit/profit/summary', methods=['GET'])
@admin_required
def api_credit_profit_summary():
    try:
        from utils.credit import get_all_credit_profit_summary
        
        summary = get_all_credit_profit_summary()
        return jsonify({'success': True, 'summary': summary})
        
    except Exception as e:
        print(f"❌ Profit summary error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# SYNC EXISTING CREDIT TRANSACTIONS TO ORDERS
# ============================================================

@admin_bp.route('/admin/api/credit/sync-to-orders', methods=['POST'])
@admin_required
def sync_credit_to_orders():
    """Sync existing credit transactions to orders table"""
    try:
        import json
        from datetime import datetime
        import uuid
        
        print("🔄 Syncing existing credit transactions to orders...")
        
        # Get all credit transactions
        tx_response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/credit_transactions?select=*",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if tx_response.status_code != 200:
            return jsonify({
                'success': False, 
                'message': f'Failed to fetch credit transactions: {tx_response.status_code}'
            }), 500
        
        credit_transactions = tx_response.json()
        print(f"📦 Found {len(credit_transactions)} credit transactions")
        
        # Filter only purchase transactions
        purchases = [t for t in credit_transactions if t.get('transaction_type') == 'purchase']
        print(f"🛒 Found {len(purchases)} purchase transactions")
        
        if not purchases:
            return jsonify({
                'success': True,
                'synced': 0,
                'failed': 0,
                'skipped': 0,
                'message': 'No purchase transactions found to sync'
            })
        
        # Get credit customers
        customer_response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/credit_customers?select=customer_id,full_name,phone",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        customer_map = {}
        if customer_response.status_code == 200:
            for c in customer_response.json():
                customer_map[c['customer_id']] = {
                    'name': c.get('full_name', 'Credit Customer'),
                    'phone': c.get('phone', '')
                }
        print(f"👤 Found {len(customer_map)} credit customers")
        
        synced = 0
        failed = 0
        skipped = 0
        
        for tx in purchases:
            transaction_id = tx.get('transaction_id')
            customer_id = tx.get('customer_id')
            amount = float(tx.get('amount', 0))
            
            # Check if order already exists
            check_response = requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/orders?credit_transaction_id=eq.{transaction_id}",
                headers=Config.SUPABASE_HEADERS,
                timeout=10
            )
            
            if check_response.status_code == 200 and check_response.json():
                print(f"⏭️ Order already exists for {transaction_id}")
                skipped += 1
                continue
            
            customer_info = customer_map.get(customer_id, {
                'name': 'Credit Customer',
                'phone': ''
            })
            
            order_id = f"CREDIT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            # Parse items from items_json
            items = tx.get('items_json', [])
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except:
                    items = []
            
            formatted_items = []
            if items and isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        product_name = item.get('name', 'Unknown Product')
                        product_id = item.get('product_id', '')
                        
                        cost_price = float(item.get('cost_price', 0))
                        if cost_price == 0 and product_id:
                            try:
                                prod_resp = requests.get(
                                    f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}&select=cost_price",
                                    headers=Config.SUPABASE_HEADERS,
                                    timeout=5
                                )
                                if prod_resp.status_code == 200:
                                    products = prod_resp.json()
                                    if products:
                                        cost_price = float(products[0].get('cost_price', 0))
                            except:
                                pass
                        
                        formatted_items.append({
                            'product_id': product_id,
                            'name': product_name,
                            'price': float(item.get('price', 0)),
                            'quantity': int(item.get('quantity', 1)),
                            'total': float(item.get('price', 0)) * int(item.get('quantity', 1)),
                            'cost_price': cost_price
                        })
            else:
                items_json = tx.get('items_json', [])
                if isinstance(items_json, str):
                    try:
                        items_json = json.loads(items_json)
                    except:
                        items_json = []
                
                if items_json and len(items_json) > 0:
                    for item in items_json:
                        if isinstance(item, dict):
                            formatted_items.append({
                                'product_id': item.get('product_id', ''),
                                'name': item.get('name', f'Credit - {customer_info.get("name", "Customer")}'),
                                'price': float(item.get('price', 0)),
                                'quantity': int(item.get('quantity', 1)),
                                'total': float(item.get('price', 0)) * int(item.get('quantity', 1)),
                                'cost_price': float(item.get('cost_price', 0))
                            })
                else:
                    formatted_items.append({
                        'product_id': '',
                        'name': f'Credit Purchase - {customer_info.get("name", "Customer")}',
                        'price': amount,
                        'quantity': 1,
                        'total': amount,
                        'cost_price': amount * 0.65
                    })
            
            order_data = {
                'order_id': order_id,
                'items': formatted_items,
                'subtotal': amount,
                'shipping': 0,
                'total': amount,
                'status': 'confirmed',
                'source': 'credit',
                'created_at': tx.get('created_at', datetime.utcnow().isoformat()),
                'customer_name': customer_info.get('name', 'Credit Customer'),
                'customer_email': f"credit_{customer_id}@example.com",
                'customer_phone': customer_info.get('phone', ''),
                'customer_address': 'Credit Purchase',
                'customer': {
                    'name': customer_info.get('name', 'Credit Customer'),
                    'email': f"credit_{customer_id}@example.com",
                    'phone': customer_info.get('phone', ''),
                    'address': 'Credit Purchase'
                },
                'user_id': tx.get('staff_name', 'System'),
                'user_name': tx.get('staff_name', 'System'),
                'user_role': 'admin',
                'staff_name': tx.get('staff_name', 'System')
            }
            
            print(f"📤 Creating order for transaction: {transaction_id} with items: {[i['name'] for i in formatted_items]}")
            
            order_response = requests.post(
                f"{Config.SUPABASE_URL}/rest/v1/orders",
                headers=Config.SUPABASE_HEADERS,
                json=order_data,
                timeout=15
            )
            
            if order_response.status_code in [200, 201]:
                synced += 1
                print(f"✅ Created order: {order_id}")
            else:
                failed += 1
                print(f"❌ Failed to create order: {order_response.status_code} - {order_response.text[:100]}")
        
        # Clear caches
        try:
            import utils.data
            utils.data.orders_cache = []
            utils.data.products_cache = []
        except:
            pass
        
        return jsonify({
            'success': True,
            'synced': synced,
            'failed': failed,
            'skipped': skipped,
            'total_purchases': len(purchases),
            'message': f'✅ Synced {synced} credit orders, {failed} failed, {skipped} already existed'
        })
        
    except Exception as e:
        print(f"❌ Error syncing credit to orders: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# CUSTOMERS API
# ============================================================

@admin_bp.route('/admin/api/customers', methods=['GET'])
@admin_required
def api_customers_paginated():
    """Get paginated customers for AJAX"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        all_orders = load_orders()
        
        customer_dict = {}
        for order in all_orders:
            if order.get('status') == 'cancelled':
                continue
                
            name = order.get('customer_name')
            if not name:
                customer = order.get('customer', {})
                if isinstance(customer, dict):
                    name = customer.get('name')
                elif isinstance(customer, str):
                    try:
                        name = json.loads(customer).get('name')
                    except:
                        pass
            
            if not name or name in ['Walk-in Customer', 'Web Customer', 'Customer', 'Unknown', '']:
                continue
            
            if name not in customer_dict:
                customer_dict[name] = {
                    'name': name,
                    'email': order.get('customer_email', 'N/A'),
                    'phone': order.get('customer_phone', 'N/A'),
                    'orders': 0,
                    'total_spent': 0
                }
            customer_dict[name]['orders'] += 1
            customer_dict[name]['total_spent'] += order.get('total', 0)
        
        customers = list(customer_dict.values())
        customers.sort(key=lambda x: x['orders'], reverse=True)
        
        total = len(customers)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = customers[start:end]
        
        return jsonify({
            'success': True,
            'customers': paginated,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'start': start + 1 if paginated else 0,
            'end': min(end, total)
        })
    except Exception as e:
        print(f"❌ Customers API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# PROFITABILITY API
# ============================================================

@admin_bp.route('/admin/api/profitability/summary', methods=['GET'])
@admin_required
def api_profitability_summary():
    try:
        from utils.profitability import get_profitability_summary, get_monthly_profitability
        
        summary = get_profitability_summary()
        monthly = get_monthly_profitability()
        
        return jsonify({
            'success': True,
            'summary': summary,
            'monthly': monthly
        })
        
    except Exception as e:
        print(f"❌ Profitability API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# CLEAR CACHE
# ============================================================

@admin_bp.route('/admin/api/clear-cache', methods=['GET'])
@admin_required
def clear_cache():
    try:
        import utils.data
        utils.data.orders_cache = []
        utils.data.products_cache = []
        return jsonify({'success': True, 'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# POS ROUTE
# ============================================================

@admin_bp.route('/admin/pos')
def admin_pos():
    if not session.get('admin_logged_in') and not session.get('user'):
        flash('Please login first', 'danger')
        return redirect(url_for('admin.user_login'))
    
    if session.get('user') and not session.get('admin_logged_in'):
        session['admin_logged_in'] = True
        print("✅ admin_logged_in set for POS user")

    all_products = load_products()
    for product in all_products:
        if 'price' not in product or product['price'] is None:
            product['price'] = 0
        if 'stock' not in product or product['stock'] is None:
            product['stock'] = 0
        if 'image' not in product:
            product['image'] = ''
        if 'name' not in product:
            product['name'] = 'Product'
        if 'id' not in product:
            product['id'] = str(uuid.uuid4())

    customers = []
    try:
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/customers",
            headers=Config.SUPABASE_HEADERS,
            timeout=10,
        )
        if response.status_code == 200:
            customers_from_db = response.json()
            for c in customers_from_db:
                customers.append({
                    'name': c.get('name', ''),
                    'email': c.get('email', ''),
                    'phone': c.get('phone', ''),
                    'orders': 0,
                    'total_spent': 0
                })
    except Exception as e:
        print(f"⚠️ Error loading customers: {e}")

    customers.sort(key=lambda x: x['name'])

    credit_customers = []
    try:
        from utils.credit import get_all_credit_customers
        credit_customers = get_all_credit_customers() or []
    except Exception as e:
        print(f"⚠️ Error loading credit customers for admin POS seed: {e}")
        credit_customers = []

    if not credit_customers:
        try:
            pos_orders_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pos_orders.json')
            if os.path.exists(pos_orders_path):
                with open(pos_orders_path, 'r', encoding='utf-8') as f:
                    orders = json.load(f)

                seen = {}
                for order in orders or []:
                    customer_id = order.get('customer_id') or order.get('customer', {}).get('id')
                    customer_name = order.get('customer_name') or order.get('customer', {}).get('name') or 'Credit Customer'
                    if customer_id and customer_name and customer_id not in seen:
                        seen[customer_id] = {
                            'customer_id': customer_id,
                            'full_name': customer_name,
                            'phone': order.get('customer_phone') or order.get('customer', {}).get('phone') or '',
                            'email': order.get('customer_email') or order.get('customer', {}).get('email') or '',
                            'current_balance': order.get('balance_after', 0) or 0,
                            'credit_limit': order.get('credit_limit', 0) or 0,
                            'account_status': 'active'
                        }
                credit_customers = list(seen.values())
        except Exception as e:
            print(f"⚠️ Error loading local order-based credit customer seed for admin POS: {e}")
            credit_customers = []

    return render_template('pos.html',
        products=all_products,
        customers=customers,
        credit_customers=credit_customers,
        DB_CONNECTED=True
    )

# ============================================================
# POS ORDER ROUTE
# ============================================================

@admin_bp.route('/admin/pos/place-order', methods=['POST'])
def admin_pos_place_order():
    if not session.get('admin_logged_in') and not session.get('user'):
        return jsonify({'success': False, 'message': 'Please login first'}), 401
    
    if session.get('user') and not session.get('admin_logged_in'):
        session['admin_logged_in'] = True
        print("✅ admin_logged_in set for POS order")

    try:
        data = request.get_json()
        if not data or not data.get('items'):
            return jsonify({'success': False, 'message': 'No items in order'}), 400

        user = session.get('user', {})
        user_id = user.get('id', 'unknown')
        user_name = user.get('name', 'Unknown User')
        user_role = user.get('role', 'user')

        order_id = data.get('order_id', f'POS-{uuid.uuid4().hex[:8].upper()}')
        items = data.get('items', [])
        
        print(f"📦 Received order: {order_id}")
        print(f"📦 Items: {len(items)}")
        print(f"👤 User: {user_name} ({user_role})")
        
        for item in items:
            print(f"  - {item.get('name')} x{item.get('quantity')}")

        print("📦 DEDUCTING STOCK...")
        
        stock_updated = []
        stock_failed = []
        
        for item in items:
            product_id = item.get('product_id')
            quantity = int(item.get('quantity', 1))
            
            if not product_id:
                print(f"⚠️ No product_id for item: {item.get('name')}")
                stock_failed.append({'name': item.get('name'), 'reason': 'No product_id'})
                continue
            
            try:
                print(f"🔍 Fetching product: {product_id}")
                response = requests.get(
                    f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                    headers=Config.SUPABASE_HEADERS,
                    timeout=10
                )
                
                if response.status_code == 200:
                    products = response.json()
                    if products and len(products) > 0:
                        product = products[0]
                        item['cost_price'] = product.get('cost_price', 0)
                        
                        current_stock = product.get('stock', 0)
                        new_stock = max(0, current_stock - quantity)
                        
                        print(f"📦 {product.get('name')}: Cost: {item['cost_price']}, Stock: {current_stock} → {new_stock}")
                        
                        update_response = requests.patch(
                            f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                            headers=Config.SUPABASE_HEADERS,
                            json={'stock': new_stock},
                            timeout=10
                        )
                        
                        if update_response.status_code in [200, 204]:
                            print(f"✅ Stock updated: {product.get('name')}")
                            stock_updated.append({
                                'name': product.get('name'),
                                'old_stock': current_stock,
                                'new_stock': new_stock
                            })
                        else:
                            print(f"❌ Failed to update stock: {update_response.status_code}")
                            stock_failed.append({
                                'name': product.get('name'),
                                'reason': f'HTTP {update_response.status_code}'
                            })
                    else:
                        print(f"⚠️ Product not found: {product_id}")
                        stock_failed.append({
                            'name': item.get('name'),
                            'reason': 'Product not found'
                        })
                else:
                    print(f"❌ Failed to fetch product: {response.status_code}")
                    stock_failed.append({
                        'name': item.get('name'),
                        'reason': f'Fetch error: {response.status_code}'
                    })
                    
            except Exception as e:
                print(f"❌ Stock deduction error for {product_id}: {e}")
                stock_failed.append({
                    'name': item.get('name'),
                    'reason': str(e)
                })

        print(f"📊 Stock updated: {len(stock_updated)} items")
        for s in stock_updated:
            print(f"  ✅ {s['name']}: {s['old_stock']} → {s['new_stock']}")
        
        if stock_failed:
            print(f"❌ Stock failed: {len(stock_failed)} items")
            for s in stock_failed:
                print(f"  ❌ {s['name']}: {s['reason']}")

        subtotal = float(data.get('subtotal', 0))
        shipping = float(data.get('shipping', 0))
        total = float(data.get('total', subtotal + shipping))

        customer_name = data.get('customer_name', 'Walk-in Customer')
        customer_email = data.get('customer_email', 'walkin@example.com')
        customer_phone = data.get('customer_phone', 'N/A')
        customer_address = data.get('customer_address', 'In-store purchase')

        order_data = {
            'order_id': order_id,
            'items': items,
            'subtotal': subtotal,
            'shipping': shipping,
            'total': total,
            'status': 'confirmed',
            'source': 'pos',
            'created_at': datetime.utcnow().isoformat(),
            'customer_name': customer_name,
            'customer_email': customer_email,
            'customer_phone': customer_phone,
            'customer_address': customer_address,
            'customer': {
                'name': customer_name,
                'email': customer_email,
                'phone': customer_phone,
                'address': customer_address,
            },
            'user_id': str(user_id),
            'user_name': user_name,
            'user_role': user_role,
            'staff_name': user_name
        }

        print(f"💰 Total: KSh {total}")

        try:
            response = requests.post(
                f"{Config.SUPABASE_URL}/rest/v1/orders",
                headers=Config.SUPABASE_HEADERS,
                json=order_data,
                timeout=15
            )

            if response.status_code in [200, 201]:
                print(f"✅ Order saved to Supabase: {order_id}")
                
                import utils.data
                utils.data.orders_cache = []
                utils.data.products_cache = []

                return jsonify({
                    'success': True,
                    'order_id': order_id,
                    'order': order_data,
                    'synced': True,
                    'stock_updated': stock_updated,
                    'stock_failed': stock_failed,
                    'message': f'✅ Order #{order_id} placed! Stock deducted: {len(stock_updated)} items.',
                    'total': total
                })
            else:
                print(f"❌ Failed to save order: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
                return jsonify({
                    'success': False,
                    'message': f'Failed to save order: {response.status_code}',
                    'supabase_error': response.text[:500]
                }), 500
                
        except Exception as e:
            print(f"❌ Order save error: {e}")
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Error saving order: {str(e)}'
            }), 500

    except Exception as exc:
        print(f'❌ POS Order error: {exc}')
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': f'Error: {str(exc)[:100]}'
        }), 500

# ============================================================
# SYNC QUEUED ORDERS
# ============================================================

@admin_bp.route('/admin/api/sync-queue', methods=['POST'])
def api_sync_queue():
    try:
        data = request.get_json()
        if not data or not data.get('orders'):
            return jsonify({
                'success': True,
                'synced': 0,
                'failed': 0,
                'message': 'No orders provided to sync'
            })

        orders_to_sync = data.get('orders', [])
        synced = 0
        failed = 0

        for order in orders_to_sync:
            try:
                order_id = order.get('order_id', f'OFF-{uuid.uuid4().hex[:8].upper()}')
                
                check_response = requests.get(
                    f"{Config.SUPABASE_URL}/rest/v1/orders?order_id=eq.{order_id}",
                    headers=Config.SUPABASE_HEADERS,
                    timeout=10
                )

                if check_response.status_code == 200 and check_response.json():
                    synced += 1
                    continue

                order_data = {
                    'order_id': order_id,
                    'items': order.get('items', []),
                    'subtotal': float(order.get('subtotal', 0)),
                    'shipping': float(order.get('shipping', 0)),
                    'total': float(order.get('total', 0)),
                    'status': order.get('status', 'confirmed'),
                    'source': order.get('source', 'pos'),
                    'created_at': order.get('created_at', datetime.utcnow().isoformat()),
                    'customer_name': order.get('customer_name', 'Walk-in Customer'),
                    'customer_email': order.get('customer_email', 'walkin@example.com'),
                    'customer_phone': order.get('customer_phone', 'N/A'),
                    'customer_address': order.get('customer_address', 'In-store purchase'),
                    'customer': order.get('customer', {
                        'name': order.get('customer_name', 'Walk-in Customer'),
                        'email': order.get('customer_email', 'walkin@example.com'),
                        'phone': order.get('customer_phone', 'N/A'),
                        'address': order.get('customer_address', 'In-store purchase')
                    }),
                    'user_id': order.get('user_id', 'unknown'),
                    'user_name': order.get('user_name', 'Unknown User'),
                    'user_role': order.get('user_role', 'user'),
                    'staff_name': order.get('staff_name', order.get('user_name', 'Unknown User'))
                }

                if not isinstance(order_data['items'], list):
                    order_data['items'] = []

                for item in order_data['items']:
                    if not isinstance(item, dict):
                        continue
                    if 'product_id' not in item:
                        item['product_id'] = str(uuid.uuid4())
                    if 'quantity' not in item:
                        item['quantity'] = 1
                    if 'price' not in item:
                        item['price'] = 0
                    if 'name' not in item:
                        item['name'] = 'Unknown Product'
                    if 'total' not in item:
                        item['total'] = float(item.get('price', 0)) * float(item.get('quantity', 1))

                response = requests.post(
                    f"{Config.SUPABASE_URL}/rest/v1/orders",
                    headers=Config.SUPABASE_HEADERS,
                    json=order_data,
                    timeout=15
                )

                if response.status_code in [200, 201]:
                    synced += 1
                else:
                    failed += 1

            except Exception as e:
                failed += 1
                print(f"❌ Sync error for {order.get('order_id', 'unknown')}: {e}")

        if synced > 0:
            import utils.data
            utils.data.orders_cache = []

        return jsonify({
            'success': True,
            'synced': synced,
            'failed': failed,
            'message': f"Synced {synced} items, {failed} failed"
        })

    except Exception as e:
        print(f"❌ Sync queue error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# PROCESS RETURN
# ============================================================

@admin_bp.route('/admin/api/process-return', methods=['POST'])
def api_process_return():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        items_to_return = data.get('items', [])
        refund_total = data.get('refund_total', 0)
        customer_name = data.get('customer_name', 'Customer')
        reason = data.get('reason', 'Customer return')

        if not items_to_return:
            return jsonify({'success': False, 'message': 'No items to return'}), 400

        return_items = []
        for item in items_to_return:
            item_price = float(item.get('price', 0))
            item_qty = int(item.get('quantity', 1))
            return_items.append({
                'product_id': str(item.get('id', '')),
                'name': item.get('name', 'Product'),
                'price': item_price,
                'quantity': item_qty,
                'total': item_price * item_qty,
                'type': 'return'
            })

        return_order_id = data.get('return_order_id', f'RET-{uuid.uuid4().hex[:8].upper()}')

        return_order_data = {
            'order_id': return_order_id,
            'items': return_items,
            'subtotal': refund_total,
            'shipping': 0,
            'total': -refund_total,
            'status': 'returned',
            'source': 'pos',
            'created_at': datetime.utcnow().isoformat(),
            'customer': {
                'name': customer_name,
                'email': 'return@example.com',
                'phone': 'N/A',
                'address': 'Return'
            },
            'customer_name': customer_name,
            'customer_email': 'return@example.com',
            'customer_phone': 'N/A',
            'customer_address': 'Return',
            'return_reason': reason,
            'return_amount': refund_total,
            'is_return': True
        }

        # Restock products
        for item in items_to_return:
            product_id = str(item.get('id', ''))
            quantity = int(item.get('quantity', 1))
            if product_id:
                try:
                    products = load_products()
                    for p in products:
                        if str(p.get('id')) == product_id:
                            current_stock = int(p.get('stock', 0))
                            new_stock = current_stock + quantity
                            requests.patch(
                                f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
                                headers=Config.SUPABASE_HEADERS,
                                json={'stock': new_stock},
                                timeout=10
                            )
                            break
                except Exception as e:
                    print(f"⚠️ Error restocking product {product_id}: {e}")

        response = requests.post(
            f"{Config.SUPABASE_URL}/rest/v1/orders",
            headers=Config.SUPABASE_HEADERS,
            json=return_order_data,
            timeout=10,
        )

        if response.status_code in [200, 201]:
            import utils.data
            utils.data.orders_cache = []
            utils.data.products_cache = []

            return jsonify({
                'success': True,
                'order_id': return_order_id,
                'message': f'Return processed! Refund: KSh {refund_total:,.2f}',
                'refund_total': refund_total,
                'revenue_deducted': refund_total
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to process return: {response.status_code}'
            }), 500

    except Exception as e:
        print(f'❌ Return error: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
        # ============================================================
# [FIXED v2] FILTERED ANALYTICS — NO DUPLICATES
# ============================================================

@admin_bp.route('/admin/api/analytics/filtered', methods=['GET'])
@admin_required
def api_analytics_filtered():
    """
    Filtered analytics: combines orders (POS + Web) with credit_transactions.
    Credit purchases are EXCLUDED from orders table to prevent duplicates.
    """
    try:
        year_param = request.args.get('year', 'all')
        month_param = request.args.get('month', 'all')

        # ---- 1. Load orders, BUT EXCLUDE any with source='credit' ----
        # (Credit purchases come from credit_transactions, not orders)
        raw_orders = load_orders()

        orders = []
        for o in raw_orders:
            src = (o.get('source') or '').lower()
            pm = (o.get('payment_method') or o.get('payment_type') or '').lower()

            # Skip if it's a credit order — we'll load those from credit_transactions
            if src == 'credit' or pm == 'credit':
                continue

            orders.append(o)

        print(f"📋 Loaded {len(orders)} non-credit orders (skipped {len(raw_orders) - len(orders)} credit orders)")

        # ---- 2. Load credit purchases from credit_transactions ----
        try:
            credit_resp = requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/credit_transactions"
                f"?transaction_type=eq.purchase&select=*",
                headers=Config.SUPABASE_HEADERS,
                timeout=15
            )
            credit_txns = credit_resp.json() if credit_resp.status_code == 200 else []
        except Exception as e:
            print(f"⚠️ Credit fetch failed: {e}")
            credit_txns = []

        print(f"💳 Loaded {len(credit_txns)} credit purchases")

        # ---- 3. Normalize both into a common shape ----
        def normalize(o, is_credit=False):
            total = float(o.get('total') or o.get('amount') or 0)

            if is_credit:
                source = 'credit'
                payment_method = 'credit'
                order_id = f"CREDIT-{o.get('transaction_id', o.get('id', ''))}"
            else:
                source = (o.get('source') or 'web').lower()
                payment_method = (o.get('payment_method') or o.get('payment_type') or 'cash').lower()
                order_id = o.get('order_id') or o.get('id') or ''

            items = o.get('items') or o.get('items_json') or []
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except Exception:
                    items = []
            if not isinstance(items, list):
                items = []

            return {
                'order_id': order_id,
                'total': total,
                'source': source,
                'payment_method': payment_method,
                'status': (o.get('status') or 'confirmed').lower(),
                'created_at': o.get('created_at') or '',
                'items': items,
                'customer_name': o.get('customer_name') or 'Customer',
                'stored_profit': float(o.get('profit') or 0) if is_credit else 0,
                'is_credit': is_credit
            }

        all_orders = [normalize(o, False) for o in orders]
        all_orders += [normalize(t, True) for t in credit_txns]

        print(f"📊 Total normalized: {len(all_orders)} transactions")

        # ---- 4. Parse dates ----
        def parse_date(raw):
            if not raw:
                return None
            try:
                if isinstance(raw, datetime):
                    return raw
                s = str(raw).replace('Z', '').replace('+00:00', '')
                if 'T' in s:
                    return datetime.fromisoformat(s[:19] if '.' not in s else s)
                if ' ' in s:
                    return datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
                return datetime.strptime(s[:10], '%Y-%m-%d')
            except Exception:
                return None

        # ---- 5. Apply filters ----
        filtered = []
        for o in all_orders:
            d = parse_date(o['created_at'])
            if not d:
                continue
            if year_param != 'all':
                try:
                    if d.year != int(year_param):
                        continue
                except Exception:
                    pass
            if month_param != 'all':
                try:
                    if d.month != int(month_param):
                        continue
                except Exception:
                    pass
            o['_dt'] = d
            filtered.append(o)

        print(f"✅ Filtered: {len(filtered)} transactions (year={year_param}, month={month_param})")

        # ---- 6. Product lookup for cost prices ----
        products = load_products()
        product_lookup = {str(p.get('id')): p for p in products if p and p.get('id')}

        # ---- 7. Calculate totals ----
        total_sales = 0.0
        total_cost = 0.0
        total_profit = 0.0
        total_items = 0
        order_count = 0
        credit_sales = 0.0
        cash_sales = 0.0
        payment_breakdown = {}

        for o in filtered:
            if o['status'] == 'cancelled':
                continue

            order_count += 1
            order_total = o['total']
            total_sales += order_total

            if o['is_credit']:
                credit_sales += order_total
            else:
                cash_sales += order_total

            pm = o['payment_method']
            payment_breakdown[pm] = payment_breakdown.get(pm, 0) + order_total

            # Compute profit
            order_profit = 0.0
            order_cost = 0.0

            if o['is_credit'] and o['stored_profit'] > 0:
                order_profit = o['stored_profit']
                order_cost = order_total - order_profit
                for it in o['items']:
                    if isinstance(it, dict):
                        total_items += int(it.get('quantity') or 1)
            else:
                for it in o['items']:
                    if not isinstance(it, dict):
                        continue
                    qty = int(it.get('quantity') or 1)
                    price = float(it.get('price') or 0)
                    cost = float(it.get('cost_price') or 0)

                    if cost == 0:
                        pid = str(it.get('product_id') or '')
                        if pid and pid in product_lookup:
                            cost = float(product_lookup[pid].get('cost_price') or 0)

                    total_items += qty
                    order_cost += cost * qty
                    order_profit += (price - cost) * qty

            total_cost += order_cost
            total_profit += order_profit

        # ---- 8. Margin ----
        profit_margin = round((total_profit / total_sales) * 100, 2) if total_sales > 0 else 0.0

        # ---- 9. Monthly breakdown ----
        monthly = {}
        for o in filtered:
            if o['status'] == 'cancelled':
                continue
            key = o['_dt'].strftime('%b %Y')

            order_profit = 0.0
            if o['is_credit'] and o['stored_profit'] > 0:
                order_profit = o['stored_profit']
            else:
                for it in o['items']:
                    if not isinstance(it, dict):
                        continue
                    qty = int(it.get('quantity') or 1)
                    price = float(it.get('price') or 0)
                    cost = float(it.get('cost_price') or 0)
                    if cost == 0:
                        pid = str(it.get('product_id') or '')
                        if pid and pid in product_lookup:
                            cost = float(product_lookup[pid].get('cost_price') or 0)
                    order_profit += (price - cost) * qty

            if key not in monthly:
                monthly[key] = {'sales': 0.0, 'orders': 0, 'profit': 0.0}
            monthly[key]['sales'] += o['total']
            monthly[key]['orders'] += 1
            monthly[key]['profit'] += order_profit

        def month_key_sort(k):
            try:
                parts = k.split()
                return (int(parts[1]), datetime.strptime(parts[0], '%b').month)
            except Exception:
                return (9999, 99)

        monthly_sorted = dict(sorted(monthly.items(), key=lambda kv: month_key_sort(kv[0])))

        # ---- 10. Available years ----
        years = set()
        for o in all_orders:
            d = parse_date(o['created_at'])
            if d:
                years.add(d.year)
        years = sorted(years, reverse=True) or [datetime.utcnow().year]

        # ---- 11. Top products ----
        product_sales = {}
        for o in filtered:
            if o['status'] == 'cancelled':
                continue
            for it in o['items']:
                if not isinstance(it, dict):
                    continue
                name = it.get('name') or 'Unknown'
                qty = int(it.get('quantity') or 1)
                price = float(it.get('price') or 0)
                if name not in product_sales:
                    product_sales[name] = {'qty': 0, 'revenue': 0.0}
                product_sales[name]['qty'] += qty
                product_sales[name]['revenue'] += price * qty

        top_products = sorted(
            product_sales.items(),
            key=lambda kv: kv[1]['revenue'],
            reverse=True
        )[:10]

        top_products_list = [
            {'name': k, 'qty': v['qty'], 'revenue': round(v['revenue'], 2)}
            for k, v in top_products
        ]

        # ---- 12. Return ----
        return jsonify({
            'success': True,
            'filters': {'year': year_param, 'month': month_param},
            'summary': {
                'total_sales': round(total_sales, 2),
                'total_cost': round(total_cost, 2),
                'total_profit': round(total_profit, 2),
                'total_items': total_items,
                'order_count': order_count,
                'credit_sales': round(credit_sales, 2),
                'cash_sales': round(cash_sales, 2),
                'profit_margin': profit_margin
            },
            'payment_breakdown': {k: round(v, 2) for k, v in payment_breakdown.items()},
            'monthly': monthly_sorted,
            'top_products': top_products_list,
            'available_years': years
        })

    except Exception as e:
        print(f"❌ Filtered analytics error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

print("✅ Admin module loaded successfully with all features working!")
