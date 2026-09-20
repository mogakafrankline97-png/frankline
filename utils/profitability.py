import os
import json
import requests
from datetime import datetime
from config import Config  # ✅ Use Config instead of hardcoding

# ============================================================
# USE CONFIG (NO HARDCODED KEYS)
# ============================================================
SUPABASE_URL = Config.SUPABASE_URL
SUPABASE_KEY = Config.SUPABASE_KEY
SUPABASE_HEADERS = Config.SUPABASE_HEADERS

print(f"📊 Profitability module using: {SUPABASE_URL}")

# ============================================================
# ✅ FIXED: PROFITABILITY TRACKING - ONLY PAID SALES
# ============================================================

def get_paid_sales():
    """
    Get ONLY PAID sales:
    - Cash + POS = already paid
    - Credit payments = paid by credit customers
    - Credit outstanding = NOT counted (not yet paid)
    """
    try:
        print("📊 get_paid_sales() called")
        
        # 1. Get orders (Cash + POS - already paid)
        orders_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/orders?select=total,status",
            headers=SUPABASE_HEADERS,
            timeout=30
        )
        
        total_orders = 0
        if orders_response.status_code == 200:
            orders = orders_response.json()
            print(f"📦 Found {len(orders)} orders")
            for order in orders:
                if order.get('status') != 'cancelled':
                    total_orders += float(order.get('total', 0))
        else:
            print(f"❌ Orders API error: {orders_response.status_code}")
            print(f"📄 Response: {orders_response.text}")
        
        print(f"💰 Total Orders Revenue: {total_orders}")
        
        # 2. Get ALL credit transactions (purchases AND payments)
        credit_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/credit_transactions?select=amount,transaction_type",
            headers=SUPABASE_HEADERS,
            timeout=30
        )
        
        total_credit_paid = 0
        total_credit_sales = 0
        
        if credit_response.status_code == 200:
            transactions = credit_response.json()
            print(f"💳 Found {len(transactions)} credit transactions")
            
            for tx in transactions:
                tx_type = tx.get('transaction_type', '').lower()
                amount = float(tx.get('amount', 0))
                
                if tx_type == 'purchase':
                    total_credit_sales += amount
                    print(f"  📦 Credit Purchase: +KSh {amount}")
                elif tx_type == 'payment':
                    total_credit_paid += amount
                    print(f"  💳 Credit Payment: +KSh {amount}")
        else:
            print(f"❌ Credit API error: {credit_response.status_code}")
            print(f"📄 Response: {credit_response.text}")
        
        print(f"💰 Total Credit Sales: {total_credit_sales}")
        print(f"💰 Total Credit Payments: {total_credit_paid}")
        
        # 3. Calculate totals
        total_paid_sales = total_orders + total_credit_paid
        outstanding_credit = total_credit_sales - total_credit_paid
        
        # ✅ FIX: Collection rate can't exceed 100%
        if total_credit_sales > 0:
            collection_rate = round((total_credit_paid / total_credit_sales) * 100, 2)
            if collection_rate > 100:
                collection_rate = 100
        else:
            collection_rate = 0
        
        result = {
            'total_paid_sales': total_paid_sales,
            'cash_pos_sales': total_orders,
            'credit_payments_received': total_credit_paid,
            'total_credit_sales': total_credit_sales,
            'outstanding_credit': outstanding_credit,
            'collection_rate': collection_rate
        }
        
        print(f"📊 Result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Error getting paid sales: {e}")
        import traceback
        traceback.print_exc()
        return {
            'total_paid_sales': 0,
            'cash_pos_sales': 0,
            'credit_payments_received': 0,
            'total_credit_sales': 0,
            'outstanding_credit': 0,
            'collection_rate': 0
        }


def get_profitability_summary():
    """Get profitability based ONLY on PAID sales"""
    try:
        print("📊 get_profitability_summary() called")
        
        sales_data = get_paid_sales()
        print(f"📊 Sales data: {sales_data}")
        
        # ✅ FIX: Get ACTUAL cost from orders and credit transactions
        total_cost = 0
        total_profit = 0
        
        # 1. Get cost from orders
        orders_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/orders?select=items,status",
            headers=SUPABASE_HEADERS,
            timeout=30
        )
        
        if orders_response.status_code == 200:
            orders = orders_response.json()
            for order in orders:
                if order.get('status') == 'cancelled':
                    continue
                items = order.get('items', [])
                if isinstance(items, str):
                    try:
                        items = json.loads(items)
                    except:
                        items = []
                for item in items:
                    if isinstance(item, dict):
                        cost = float(item.get('cost_price', 0) or 0)
                        qty = int(item.get('quantity', 1))
                        total_cost += cost * qty
        
        # 2. Get cost from credit transactions
        credit_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/credit_transactions?select=total_cost,transaction_type",
            headers=SUPABASE_HEADERS,
            timeout=30
        )
        
        if credit_response.status_code == 200:
            transactions = credit_response.json()
            for tx in transactions:
                if tx.get('transaction_type') == 'purchase':
                    total_cost += float(tx.get('total_cost', 0) or 0)
        
        total_revenue = sales_data.get('total_paid_sales', 0)
        total_profit = total_revenue - total_cost
        
        if total_revenue > 0:
            profit_margin = round((total_profit / total_revenue) * 100, 2)
        else:
            profit_margin = 0
        
        result = {
            'total_revenue': total_revenue,
            'cash_pos_revenue': sales_data.get('cash_pos_sales', 0),
            'credit_payments_received': sales_data.get('credit_payments_received', 0),
            'total_credit_sales': sales_data.get('total_credit_sales', 0),
            'outstanding_credit': sales_data.get('outstanding_credit', 0),
            'collection_rate': sales_data.get('collection_rate', 0),
            'total_cost': total_cost,
            'total_profit': total_profit,
            'profit_margin': profit_margin
        }
        
        print(f"📊 Profitability result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Error getting profitability: {e}")
        import traceback
        traceback.print_exc()
        return {
            'total_revenue': 0,
            'cash_pos_revenue': 0,
            'credit_payments_received': 0,
            'total_credit_sales': 0,
            'outstanding_credit': 0,
            'collection_rate': 0,
            'total_cost': 0,
            'total_profit': 0,
            'profit_margin': 0
        }


def get_monthly_profitability(year=None):
    """Get monthly profitability based ONLY on PAID sales"""
    try:
        if not year:
            year = datetime.utcnow().year
        
        # Get orders (Cash + POS)
        orders_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/orders?select=total,created_at,status,items",
            headers=SUPABASE_HEADERS,
            timeout=30
        )
        
        # Get credit transactions
        credit_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/credit_transactions?select=amount,transaction_type,created_at,total_cost",
            headers=SUPABASE_HEADERS,
            timeout=30
        )
        
        months = {}
        month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Process orders (already paid)
        if orders_response.status_code == 200:
            orders = orders_response.json()
            for order in orders:
                if order.get('status') == 'cancelled':
                    continue
                    
                created_at = order.get('created_at', '')
                if not created_at:
                    continue
                    
                try:
                    if 'T' in created_at:
                        clean_date = created_at.replace('Z', '').replace('+00:00', '')
                        order_date = datetime.fromisoformat(clean_date[:19])
                    else:
                        order_date = datetime.strptime(created_at[:10], '%Y-%m-%d')
                except:
                    continue
                
                if order_date.year != year:
                    continue
                
                month_key = order_date.strftime('%b %Y')
                
                if month_key not in months:
                    months[month_key] = {
                        'month': month_key,
                        'cash_pos_sales': 0,
                        'credit_payments': 0,
                        'total_paid_sales': 0,
                        'credit_sales': 0,
                        'outstanding': 0,
                        'profit': 0,
                        'margin': 0,
                        'cost': 0
                    }
                
                months[month_key]['cash_pos_sales'] += float(order.get('total', 0))
                
                # Calculate cost from items
                items = order.get('items', [])
                if isinstance(items, str):
                    try:
                        items = json.loads(items)
                    except:
                        items = []
                for item in items:
                    if isinstance(item, dict):
                        cost = float(item.get('cost_price', 0) or 0)
                        qty = int(item.get('quantity', 1))
                        months[month_key]['cost'] += cost * qty
        
        # Process credit transactions
        if credit_response.status_code == 200:
            transactions = credit_response.json()
            for tx in transactions:
                created_at = tx.get('created_at', '')
                if not created_at:
                    continue
                    
                try:
                    if 'T' in created_at:
                        clean_date = created_at.replace('Z', '').replace('+00:00', '')
                        tx_date = datetime.fromisoformat(clean_date[:19])
                    else:
                        tx_date = datetime.strptime(created_at[:10], '%Y-%m-%d')
                except:
                    continue
                
                if tx_date.year != year:
                    continue
                
                month_key = tx_date.strftime('%b %Y')
                
                if month_key not in months:
                    months[month_key] = {
                        'month': month_key,
                        'cash_pos_sales': 0,
                        'credit_payments': 0,
                        'total_paid_sales': 0,
                        'credit_sales': 0,
                        'outstanding': 0,
                        'profit': 0,
                        'margin': 0,
                        'cost': 0
                    }
                
                tx_type = tx.get('transaction_type', '').lower()
                amount = float(tx.get('amount', 0))
                
                if tx_type == 'purchase':
                    months[month_key]['credit_sales'] += amount
                    months[month_key]['cost'] += float(tx.get('total_cost', 0) or 0)
                elif tx_type == 'payment':
                    months[month_key]['credit_payments'] += amount
        
        # Calculate totals and profit for each month
        for key in months:
            months[key]['total_paid_sales'] = months[key]['cash_pos_sales'] + months[key]['credit_payments']
            months[key]['outstanding'] = months[key]['credit_sales'] - months[key]['credit_payments']
            months[key]['profit'] = months[key]['total_paid_sales'] - months[key]['cost']
            months[key]['margin'] = round((months[key]['profit'] / months[key]['total_paid_sales'] * 100) if months[key]['total_paid_sales'] > 0 else 0, 2)
        
        report = list(months.values())
        report.sort(key=lambda x: month_order.index(x['month'].split()[0]) if x['month'].split()[0] in month_order else 99)
        
        return report
        
    except Exception as e:
        print(f"❌ Error getting monthly profitability: {e}")
        import traceback
        traceback.print_exc()
        return []
