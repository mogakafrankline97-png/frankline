import os
import traceback
import uuid
from datetime import datetime, timedelta

import requests
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from config import Config
from utils.data import get_cart, get_sales_analytics, load_bundles, load_orders, load_products, save_order_to_supabase, update_product_stock

admin_bp = Blueprint('admin', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def calculate_analytics_from_orders(orders):
    """Helper function to calculate analytics from orders with categories"""
    if not orders:
        return {
            'total_revenue': 0,
            'total_cost': 0,
            'total_profit': 0,
            'total_orders': 0,
            'total_items_sold': 0,
            'pos_orders_count': 0,
            'web_orders_count': 0,
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
    product_sales = {}
    category_sales = {}
    monthly_data = {}
    
    for order in orders:
        if order.get('status') == 'cancelled':
            continue
            
        if order.get('source') == 'pos':
            pos_orders_count += 1
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
        
        for item in order.get('items', []):
            quantity = item.get('quantity', 1)
            price = float(item.get('price', 0) or 0)
            total_items_sold += quantity
            
            item_total = price * quantity
            total_revenue += item_total
            monthly_data[month_key]['revenue'] += item_total
            
            p_id = str(item.get('product_id', ''))
            product = product_lookup.get(p_id, {})
            cost_price = float(item.get('cost_price') or product.get('cost_price') or 0)
            
            item_cost = cost_price * quantity
            total_cost += item_cost
            monthly_data[month_key]['cost'] += item_cost
            
            item_profit = item_total - item_cost
            total_profit += item_profit
            monthly_data[month_key]['profit'] += item_profit
            
    return {
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'total_orders': len(orders),
        'total_items_sold': total_items_sold,
        'pos_orders_count': pos_orders_count,
        'web_orders_count': web_orders_count,
        'product_sales': product_sales,
        'category_sales': category_sales,
        'monthly_data': monthly_data
    }

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == 'admin' and password == 'electronics2026':
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        
        flash('Invalid credentials', 'danger')

    return render_template('admin_login.html')

@admin_bp.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out', 'success')
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login first', 'danger')
        return redirect(url_for('admin.admin_login'))

    try:
        products = load_products()
        orders = load_orders()
        bundles = load_bundles()
        cart = get_cart()
        analytics = get_sales_analytics()

        customer_list = {}
        pos_count = 0
        web_count = 0
        for order in orders:
            customer = order.get('customer', {})
            if isinstance(customer, str):
                try:
                    customer = __import__('json').loads(customer)
                except Exception:
                    customer = {}
            if isinstance(customer, list):
                customer = customer[0] if customer else {}
            if not isinstance(customer, dict):
                customer = {}
            source = order.get('source', 'web')
            if source == 'pos':
                pos_count += 1
            else:
                web_count += 1
            name = customer.get('name', 'Unknown') if isinstance(customer, dict) else 'Unknown'
            if name and name != 'Unknown':
                if name not in customer_list:
                    customer_list[name] = {'name': name, 'email': customer.get('email', ''), 'phone': customer.get('phone', ''), 'orders': 0, 'total_spent': 0}
                customer_list[name]['orders'] += 1
                customer_list[name]['total_spent'] += order.get('total', 0)

        customers = list(customer_list.values())
        customers.sort(key=lambda x: x['orders'], reverse=True)

        stats = {
            'total_products': len(products),
            'total_bundles': len(bundles),
            'total_cart_items': sum(cart.values()) if cart else 0,
            'low_stock': len([p for p in products if p.get('stock', 0) < 10]),
            'total_orders': len(orders),
            'pending_orders': len([o for o in orders if o.get('status') == 'pending']),
            'pos_orders': pos_count,
            'web_orders': web_count,
            'total_revenue': analytics.get('total_revenue', 0),
            'total_cost': analytics.get('total_cost', 0),
            'total_profit': analytics.get('total_profit', 0),
            'total_items_sold': analytics.get('total_items_sold', 0),
            'total_customers': len(customers),
            'db_mode': 'online',
        }

        return render_template('admin.html', products=products, bundles=bundles, orders=orders, customers=customers, stats=stats, pos_count=pos_count, analytics=analytics, DB_CONNECTED=True)
    except Exception as exc:
        print(f'Admin dashboard error: {exc}')
        traceback.print_exc()
        flash('Error loading admin dashboard', 'danger')
        return render_template('admin.html', products=[], bundles=[], orders=[], customers=[], pos_count=0, analytics={}, stats={
            'total_products': 0,
            'total_bundles': 0,
            'total_cart_items': 0,
            'low_stock': 0,
            'total_orders': 0,
            'pending_orders': 0,
            'pos_orders': 0,
            'web_orders': 0,
            'total_revenue': 0,
            'total_cost': 0,
            'total_profit': 0,
            'total_items_sold': 0,
            'total_customers': 0,
            'db_mode': 'offline',
        }, DB_CONNECTED=False)

@admin_bp.route('/admin/pos')
def admin_pos():
    if not session.get('admin_logged_in'):
        flash('Please login first', 'danger')
        return redirect(url_for('admin.admin_login'))

    products = load_products()
    for product in products:
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

    customer_list = {}
    orders = load_orders()
    for order in orders:
        customer = order.get('customer', {})
        if isinstance(customer, str):
            try:
                customer = __import__('json').loads(customer)
            except Exception:
                customer = {}
        if isinstance(customer, list):
            customer = customer[0] if customer else {}
        if not isinstance(customer, dict):
            customer = {}
        name = customer.get('name', 'Unknown') if isinstance(customer, dict) else 'Unknown'
        if name and name != 'Unknown':
            if name not in customer_list:
                customer_list[name] = {'name': name, 'email': customer.get('email', ''), 'phone': customer.get('phone', ''), 'orders': 0, 'total_spent': 0}
            customer_list[name]['orders'] += 1
            customer_list[name]['total_spent'] += order.get('total', 0)

    customers = list(customer_list.values())
    customers.sort(key=lambda x: x['orders'], reverse=True)
    return render_template('pos.html', products=products, customers=customers, DB_CONNECTED=True)

@admin_bp.route('/admin/pos/place-order', methods=['POST'])
def admin_pos_place_order():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        if not data or not data.get('items'):
            return jsonify({'success': False, 'message': 'No items in order'}), 400

        order_id = f'POS-{uuid.uuid4().hex[:8].upper()}'
        products = load_products()
        product_lookup = {str(p.get('id')): p for p in products}

        items = data.get('items', [])
        calculated_subtotal = 0
        items_with_cost = []

        for item in items:
            product_id = str(item.get('product_id'))
            quantity = item.get('quantity', 1)
            price = item.get('price', 0)

            calculated_subtotal += price * quantity

            product = product_lookup.get(product_id)
            cost_price = product.get('cost_price', 0) if product else 0

            item_with_cost = item.copy()
            item_with_cost['cost_price'] = cost_price
            items_with_cost.append(item_with_cost)

            if product:
                current_stock = product.get('stock', 0)
                if current_stock < quantity:
                    return jsonify({
                        'success': False,
                        'message': f'Not enough stock for {product.get("name")}. Available: {current_stock}'
                    }), 400
                new_stock = max(0, current_stock - quantity)
                update_product_stock(product_id, new_stock)

        subtotal = calculated_subtotal if calculated_subtotal > 0 else data.get('subtotal', 0)
        shipping = data.get('shipping', 0)
        total = subtotal + shipping

        order_data = {
            'order_id': order_id,
            'items': items_with_cost,
            'subtotal': subtotal,
            'shipping': shipping,
            'total': total,
            'status': 'confirmed',
            'source': 'pos',
            'created_at': datetime.utcnow().isoformat(),
            'customer': {
                'name': data.get('customer_name', 'Walk-in Customer'),
                'email': data.get('customer_email', 'walkin@example.com'),
                'phone': data.get('customer_phone', 'N/A'),
                'address': data.get('customer_address', 'In-store purchase'),
            },
        }

        save_result = save_order_to_supabase(order_data)

        if save_result.get('success'):
            all_orders = load_orders()

            total_revenue = sum(order.get('total', 0) for order in all_orders)

            total_profit = 0
            total_items_sold = 0
            pos_orders_count = 0
            web_orders_count = 0

            for order in all_orders:
                if order.get('source') == 'pos':
                    pos_orders_count += 1
                else:
                    web_orders_count += 1

                for item in order.get('items', []):
                    quantity = item.get('quantity', 1)
                    total_items_sold += quantity

                    price = item.get('price', 0)
                    cost_price = item.get('cost_price', 0)
                    if cost_price > 0:
                        total_profit += (price - cost_price) * quantity
                    elif price > 0:
                        total_profit += price * quantity * 0.3

            analytics = {
                'total_revenue': total_revenue,
                'total_profit': total_profit,
                'total_orders': len(all_orders),
                'total_items_sold': total_items_sold,
                'pos_orders_count': pos_orders_count,
                'web_orders_count': web_orders_count,
                'product_sales': {},
                'category_sales': {}
            }

            return jsonify({
                'success': True,
                'order_id': order_id,
                'message': 'Order placed successfully!',
                'analytics': analytics,
                'stats': {
                    'total_revenue': total_revenue,
                    'total_profit': total_profit,
                    'total_orders': len(all_orders),
                    'total_items_sold': total_items_sold,
                    'pos_orders_count': pos_orders_count,
                    'web_orders_count': web_orders_count,
                },
                'queued': save_result.get('queued', False),
                'synced': save_result.get('synced', False)
            })
        else:
            return jsonify({
                'success': False,
                'message': save_result.get('message', 'Failed to save order')
            }), 500

    except Exception as exc:
        print(f'POS Order error: {exc}')
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(exc)}), 500

@admin_bp.route('/admin/api/analytics')
def admin_api_analytics():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    orders = load_orders()
    analytics = calculate_analytics_from_orders(orders)
    return jsonify(analytics)

@admin_bp.route('/admin/api/revenue')
def admin_api_revenue():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        orders = load_orders()
        analytics = calculate_analytics_from_orders(orders)

        return jsonify({
            "total_revenue": analytics.get('total_revenue', 0),
            "total_cost": analytics.get('total_cost', 0),
            "total_profit": analytics.get('total_profit', 0),
            "total_orders": analytics.get('total_orders', 0),
            "total_items_sold": analytics.get('total_items_sold', 0),
            "today_revenue": 0,
            "today_orders": 0,
            "yesterday_revenue": 0,
            "month_revenue": 0,
            "month_orders": 0,
            "last_month_revenue": 0,
            "today_growth_pct": 0,
            "month_growth_pct": 0
        })
    except Exception as exc:
        print(f'❌ Revenue API error: {exc}')
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500
