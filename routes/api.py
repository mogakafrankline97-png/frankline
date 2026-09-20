from flask import Blueprint, jsonify, request, session

from utils.data import get_sales_analytics, load_orders, load_products

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/status')
def api_status():
    try:
        orders = load_orders()
        products = load_products()
        return jsonify({
            'success': True,
            'products': len(products),
            'orders': len(orders),
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
            'environment': 'vercel' if __import__('config').Config.IS_VERCEL else 'local',
        })
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@api_bp.route('/api/products')
def api_products():
    try:
        return jsonify(load_products())
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@api_bp.route('/api/orders')
def api_orders():
    try:
        return jsonify(load_orders())
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@api_bp.route('/cart-count', methods=['GET'])
def cart_count():
    try:
        from utils.data import get_cart
        cart = get_cart()
        count = sum(cart.values()) if cart and isinstance(cart, dict) else 0
        return jsonify({'count': count})
    except Exception:
        return jsonify({'count': 0})
