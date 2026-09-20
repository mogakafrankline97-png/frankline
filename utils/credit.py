import os
import json
import uuid
import requests
from datetime import datetime, timedelta
from config import Config

# ============================================================
# ENVIRONMENT DETECTION
# ============================================================
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('NOW_REGION') is not None
print(f"🏦 Credit module running on: {'Vercel' if IS_VERCEL else 'Localhost'}")

# ============================================================
# CREDIT CUSTOMER FUNCTIONS
# ============================================================


def load_local_credit_customers():
    """Load credit customers from the local offline JSON file."""
    try:
        from utils.storage import load_json_data

        data = load_json_data() or {}
        customers = data.get('credit_customers', []) or []
        normalized = []

        for customer in customers:
            if not isinstance(customer, dict):
                continue

            normalized.append({
                'customer_id': customer.get('customer_id') or customer.get('id') or customer.get('customerId') or '',
                'full_name': customer.get('full_name') or customer.get('name') or customer.get('customer_name') or 'Credit Customer',
                'name': customer.get('full_name') or customer.get('name') or customer.get('customer_name') or 'Credit Customer',
                'phone': customer.get('phone') or customer.get('contact_phone') or '',
                'email': customer.get('email') or customer.get('customer_email') or '',
                'current_balance': customer.get('current_balance', customer.get('balance', 0)) or 0,
                'balance': customer.get('balance', customer.get('current_balance', 0)) or 0,
                'credit_limit': customer.get('credit_limit', customer.get('limit', 0)) or 0,
                'limit': customer.get('limit', customer.get('credit_limit', 0)) or 0,
                'account_status': customer.get('account_status') or customer.get('status') or 'active',
                'status': customer.get('status') or customer.get('account_status') or 'active',
                'created_at': customer.get('created_at'),
                'updated_at': customer.get('updated_at')
            })

        return normalized
    except Exception as e:
        print(f"⚠️ Error loading local credit customers: {e}")
        return []


def save_local_credit_customers(customers):
    """Persist credit customers to the local offline JSON file."""
    try:
        from utils.storage import load_json_data, save_json_data

        data = load_json_data() or {}
        data['credit_customers'] = customers or []
        save_json_data(data)
        return True
    except Exception as e:
        print(f"⚠️ Error saving local credit customers: {e}")
        return False


def generate_customer_id():
    """Generate a unique credit customer ID"""
    return f'CR-{uuid.uuid4().hex[:8].upper()}'

def generate_transaction_id():
    """Generate a unique transaction ID"""
    return f'TXN-{uuid.uuid4().hex[:8].upper()}'

def add_credit_customer(customer_data):
    """Add a new credit customer"""
    try:
        if not customer_data.get('customer_id'):
            customer_data['customer_id'] = generate_customer_id()

        customer_data['created_at'] = datetime.utcnow().isoformat()
        customer_data['updated_at'] = datetime.utcnow().isoformat()

        if not customer_data.get('account_status'):
            customer_data['account_status'] = 'active'
        if not customer_data.get('current_balance'):
            customer_data['current_balance'] = 0
        if not customer_data.get('credit_limit'):
            customer_data['credit_limit'] = 0
        if not customer_data.get('total_purchases'):
            customer_data['total_purchases'] = 0
        if not customer_data.get('total_payments'):
            customer_data['total_payments'] = 0
        if not customer_data.get('total_cost'):
            customer_data['total_cost'] = 0
        if not customer_data.get('total_profit'):
            customer_data['total_profit'] = 0

        clean_data = {k: v for k, v in customer_data.items() if v is not None}

        existing_local = load_local_credit_customers()
        local_customer = {
            'customer_id': clean_data.get('customer_id'),
            'full_name': clean_data.get('full_name') or clean_data.get('name') or 'Credit Customer',
            'name': clean_data.get('full_name') or clean_data.get('name') or 'Credit Customer',
            'phone': clean_data.get('phone') or '',
            'email': clean_data.get('email') or '',
            'current_balance': clean_data.get('current_balance', 0) or 0,
            'balance': clean_data.get('current_balance', 0) or 0,
            'credit_limit': clean_data.get('credit_limit', 0) or 0,
            'limit': clean_data.get('credit_limit', 0) or 0,
            'account_status': clean_data.get('account_status') or 'active',
            'status': clean_data.get('account_status') or 'active',
            'created_at': clean_data.get('created_at'),
            'updated_at': clean_data.get('updated_at')
        }

        merged_local = []
        seen_ids = set()
        for item in existing_local + [local_customer]:
            customer_id = item.get('customer_id') or item.get('id') or item.get('customerId')
            if not customer_id:
                continue
            if customer_id not in seen_ids:
                merged_local.append(item)
                seen_ids.add(customer_id)

        save_local_credit_customers(merged_local)

        response = requests.post(
            f"{Config.SUPABASE_URL}/rest/v1/credit_customers",
            headers=Config.SUPABASE_HEADERS,
            json=clean_data,
            timeout=30
        )

        if response.status_code in [200, 201]:
            return {
                'success': True,
                'message': 'Credit customer added successfully',
                'data': response.json() if response.json() else customer_data
            }
        else:
            print(f"❌ Failed to add credit customer: {response.status_code} - {response.text}")
            return {
                'success': False,
                'message': f'Failed to add customer: {response.status_code}',
                'error': response.text
            }

    except Exception as e:
        print(f"❌ Error adding credit customer: {e}")
        return {'success': False, 'message': str(e)}

def get_all_credit_customers():
    """Get all credit customers, with local offline fallback."""
    try:
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/credit_customers?select=*&order=created_at.desc",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )

        if response.status_code == 200:
            customers = response.json()
            for customer in customers:
                if customer.get('created_at'):
                    try:
                        customer['created_at'] = customer['created_at'][:10]
                    except:
                        pass
            save_local_credit_customers(customers)
            return customers
        else:
            print(f"⚠️ Failed to get credit customers: {response.status_code}")
            local_customers = load_local_credit_customers()
            return local_customers

    except Exception as e:
        print(f"❌ Error getting credit customers: {e}")
        local_customers = load_local_credit_customers()
        return local_customers

def get_credit_customer_by_id(customer_id):
    """Get a specific credit customer by ID"""
    try:
        customer_id = str(customer_id).strip()
        print(f"🔍 get_credit_customer_by_id searching for: '{customer_id}'")
        
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/credit_customers?customer_id=eq.{customer_id}&select=*",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            customers = response.json()
            print(f"📋 Found {len(customers)} customers")
            if customers:
                customer = customers[0]
                print(f"✅ Found customer: {customer.get('full_name')}")
                return customer
            else:
                print(f"⚠️ No customer found with customer_id: {customer_id}")
        else:
            print(f"❌ API error: {response.status_code} - {response.text[:200]}")
        
        return None
            
    except Exception as e:
        print(f"❌ Error getting credit customer: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_credit_customer_by_phone(phone):
    """Find a credit customer by phone number"""
    try:
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/credit_customers?phone=eq.{phone}&select=*",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            customers = response.json()
            return customers[0] if customers else None
        else:
            return None
            
    except Exception as e:
        print(f"❌ Error finding customer by phone: {e}")
        return None

def update_credit_customer(customer_id, update_data):
    """Update a credit customer"""
    try:
        update_data['updated_at'] = datetime.utcnow().isoformat()
        clean_data = {k: v for k, v in update_data.items() if v is not None}
        
        response = requests.patch(
            f"{Config.SUPABASE_URL}/rest/v1/credit_customers?customer_id=eq.{customer_id}",
            headers=Config.SUPABASE_HEADERS,
            json=clean_data,
            timeout=30
        )
        
        if response.status_code in [200, 204]:
            return {
                'success': True,
                'message': 'Customer updated successfully'
            }
        else:
            return {
                'success': False,
                'message': f'Failed to update customer: {response.status_code}'
            }
            
    except Exception as e:
        print(f"❌ Error updating credit customer: {e}")
        return {'success': False, 'message': str(e)}

# ============================================================
# 🔴 UPDATED: DELETE CREDIT CUSTOMER - HARD DELETE
# ============================================================

def delete_credit_customer(customer_id):
    """
    Delete a credit customer permanently from the database.
    This will also delete all associated transactions.
    """
    try:
        import traceback
        
        customer_id = str(customer_id).strip()
        print(f"🗑️ delete_credit_customer called for: '{customer_id}'")
        
        # First, check if customer exists
        customer = get_credit_customer_by_id(customer_id)
        if not customer:
            return {
                'success': False,
                'message': f'Customer not found with ID: {customer_id}'
            }
        
        print(f"👤 Found customer: {customer.get('full_name')}")
        
        # Check if customer has balance
        balance = float(customer.get('current_balance', 0))
        if balance > 0:
            return {
                'success': False,
                'message': f'Cannot delete customer with balance of KSh {balance:,.2f}. Please clear balance first.'
            }
        
        # ============================================================
        # STEP 1: Delete all transactions for this customer
        # ============================================================
        print(f"📤 Deleting transactions for customer: {customer_id}")
        
        # First, get all transaction IDs
        tx_response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/credit_transactions?customer_id=eq.{customer_id}&select=transaction_id",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if tx_response.status_code == 200:
            transactions = tx_response.json()
            print(f"📋 Found {len(transactions)} transactions to delete")
            
            # Delete each transaction
            for tx in transactions:
                tx_id = tx.get('transaction_id')
                if tx_id:
                    delete_tx = requests.delete(
                        f"{Config.SUPABASE_URL}/rest/v1/credit_transactions?transaction_id=eq.{tx_id}",
                        headers=Config.SUPABASE_HEADERS,
                        timeout=30
                    )
                    if delete_tx.status_code in [200, 204]:
                        print(f"✅ Deleted transaction: {tx_id}")
                    else:
                        print(f"⚠️ Failed to delete transaction: {tx_id}")
        else:
            print(f"⚠️ Could not fetch transactions: {tx_response.status_code}")
        
        # ============================================================
        # STEP 2: Delete the customer
        # ============================================================
        print(f"🗑️ Deleting customer: {customer_id}")
        
        response = requests.delete(
            f"{Config.SUPABASE_URL}/rest/v1/credit_customers?customer_id=eq.{customer_id}",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if response.status_code in [200, 204]:
            print(f"✅ Customer deleted successfully: {customer_id}")
            
            # Clear cache
            try:
                import utils.data
                utils.data.orders_cache = []
                utils.data.products_cache = []
            except:
                pass
            
            return {
                'success': True,
                'message': f'Customer "{customer.get("full_name")}" deleted successfully'
            }
        else:
            print(f"❌ Failed to delete customer: {response.status_code} - {response.text}")
            return {
                'success': False,
                'message': f'Failed to delete customer: {response.status_code}',
                'error': response.text
            }
            
    except Exception as e:
        print(f"❌ Error deleting credit customer: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

# ============================================================
# ✅ COMPLETE: CREDIT PURCHASE WITH ORDER CREATION
# ============================================================

def record_credit_purchase(customer_id, items, total_amount, staff_name, notes=""):
    """Record a credit purchase with profit tracking AND create order entry"""
    try:
        import json
        import uuid
        
        print(f"🔍 record_credit_purchase called")
        print(f"💰 Amount: {total_amount}")
        print(f"📦 Items: {items}")
        
        # Get customer
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/credit_customers?customer_id=eq.{customer_id}&select=*",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if response.status_code != 200:
            return {'success': False, 'message': 'Customer not found'}
        
        customers = response.json()
        if not customers:
            return {'success': False, 'message': 'Customer not found'}
        
        customer = customers[0]
        print(f"✅ Customer found: {customer.get('full_name')}")
        
        current_balance = float(customer.get('current_balance', 0))
        credit_limit = float(customer.get('credit_limit', 0))
        total_amount = float(total_amount)
        
        # ✅ Calculate costs and profit for each item
        total_cost = 0
        total_profit = 0
        item_details = []
        order_items = []  # For order table
        
        # Parse items
        if isinstance(items, list):
            item_list = items
        elif isinstance(items, str):
            try:
                item_list = json.loads(items)
            except:
                item_list = [{'name': items, 'quantity': 1, 'price': total_amount}]
        else:
            item_list = [{'name': str(items), 'quantity': 1, 'price': total_amount}]
        
        # Process each item - FETCH CURRENT COST FROM PRODUCT TABLE
        for item in item_list:
            product_name = item.get('name', 'Unknown')
            quantity = int(item.get('quantity', 1))
            price = float(item.get('price', 0))
            product_id = item.get('product_id')
            
            # ✅ ALWAYS FETCH CURRENT COST FROM PRODUCT TABLE
            cost_price = 0
            
            try:
                if product_id:
                    # Try by product_id first (more accurate)
                    prod_response = requests.get(
                        f"{Config.SUPABASE_URL}/rest/v1/products?id=eq.{product_id}&select=cost_price",
                        headers=Config.SUPABASE_HEADERS,
                        timeout=10
                    )
                    if prod_response.status_code == 200:
                        products = prod_response.json()
                        if products:
                            cost_price = float(products[0].get('cost_price', 0))
                            print(f"✅ Found product by ID: {product_id}, Cost: KSh {cost_price}")
                
                # If not found by ID, try by name
                if cost_price == 0:
                    prod_response = requests.get(
                        f"{Config.SUPABASE_URL}/rest/v1/products?name=ilike.%25{product_name}%25&select=cost_price",
                        headers=Config.SUPABASE_HEADERS,
                        timeout=10
                    )
                    if prod_response.status_code == 200:
                        products = prod_response.json()
                        if products:
                            cost_price = float(products[0].get('cost_price', 0))
                            print(f"✅ Found product by name: {product_name}, Cost: KSh {cost_price}")
                            
            except Exception as e:
                print(f"⚠️ Error fetching product cost: {e}")
            
            # If still 0, estimate at 70% (fallback)
            if cost_price == 0:
                cost_price = price * 0.7
                print(f"⚠️ No cost found, using estimate: KSh {cost_price}")
            
            # Store cost in item
            item['cost_price'] = cost_price
            
            item_cost = cost_price * quantity
            item_profit = (price - cost_price) * quantity
            item_margin = ((price - cost_price) / price * 100) if price > 0 else 0
            
            total_cost += item_cost
            total_profit += item_profit
            
            item_details.append({
                'name': product_name,
                'quantity': quantity,
                'price': price,
                'cost_price': cost_price,
                'total_cost': item_cost,
                'profit': item_profit,
                'margin': round(item_margin, 1)
            })
            
            # ✅ Build order items for orders table
            order_items.append({
                'product_id': product_id,
                'name': product_name,
                'price': price,
                'quantity': quantity,
                'total': price * quantity,
                'cost_price': cost_price
            })
        
        profit_margin = (total_profit / total_amount * 100) if total_amount > 0 else 0
        
        print(f"📊 Profit Calculation:")
        print(f"   Total Amount: KSh {total_amount:,.2f}")
        print(f"   Total Cost: KSh {total_cost:,.2f}")
        print(f"   Total Profit: KSh {total_profit:,.2f}")
        print(f"   Margin: {profit_margin:.1f}%")
        
        if credit_limit > 0 and (current_balance + total_amount) > credit_limit:
            return {
                'success': False,
                'message': f'Credit limit exceeded. Limit: KSh {credit_limit:,.2f}, Available: KSh {(credit_limit - current_balance):,.2f}'
            }
        
        new_balance = current_balance + total_amount
        
        # ✅ Create transaction with all fields
        transaction_id = f'TXN-{uuid.uuid4().hex[:8].upper()}'
        
        transaction_data = {
            'transaction_id': transaction_id,
            'customer_id': customer_id,
            'transaction_type': 'purchase',
            'amount': total_amount,
            'balance_after': new_balance,
            'items_json': json.dumps(item_details),
            'staff_name': staff_name,
            'notes': notes or '',
            'payment_status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'total_cost': total_cost,
            'profit': total_profit,
            'profit_margin': profit_margin
        }
        
        print(f"📤 Inserting transaction with cost: KSh {total_cost}")
        
        response = requests.post(
            f"{Config.SUPABASE_URL}/rest/v1/credit_transactions",
            headers=Config.SUPABASE_HEADERS,
            json=transaction_data,
            timeout=30
        )
        
        print(f"📥 Response status: {response.status_code}")
        
        if response.status_code not in [200, 201]:
            # Fallback - try with simple data
            simple_transaction = {
                'transaction_id': transaction_id,
                'customer_id': customer_id,
                'transaction_type': 'purchase',
                'amount': total_amount,
                'balance_after': new_balance,
                'items_json': json.dumps(item_details),
                'staff_name': staff_name,
                'notes': notes or '',
                'payment_status': 'pending',
                'created_at': datetime.utcnow().isoformat(),
                'total_cost': total_cost,
                'profit': total_profit,
                'profit_margin': profit_margin
            }
            
            response = requests.post(
                f"{Config.SUPABASE_URL}/rest/v1/credit_transactions",
                headers=Config.SUPABASE_HEADERS,
                json=simple_transaction,
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                return {
                    'success': False,
                    'message': f'Failed to record transaction: {response.status_code}',
                    'error': response.text
                }
        
        print(f"✅ Transaction saved with correct cost")
        
        # Update customer balance
        update_data = {
            'current_balance': new_balance,
            'total_purchases': float(customer.get('total_purchases', 0)) + total_amount,
            'total_cost': float(customer.get('total_cost', 0)) + total_cost,
            'total_profit': float(customer.get('total_profit', 0)) + total_profit,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        update_response = requests.patch(
            f"{Config.SUPABASE_URL}/rest/v1/credit_customers?customer_id=eq.{customer_id}",
            headers=Config.SUPABASE_HEADERS,
            json=update_data,
            timeout=30
        )
        
        if update_response.status_code not in [200, 204]:
            return {
                'success': False,
                'message': f'Transaction saved but failed to update balance: {update_response.status_code}'
            }
        
        # ============================================================
        # ✅ CREATE ORDER ENTRY FOR CREDIT PURCHASE
        # ============================================================
        order_id = f"CREDIT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        order_data = {
            'order_id': order_id,
            'items': order_items,
            'subtotal': total_amount,
            'shipping': 0,
            'total': total_amount,
            'status': 'confirmed',
            'source': 'credit',
            'created_at': datetime.utcnow().isoformat(),
            'customer_name': customer.get('full_name', 'Credit Customer'),
            'customer_email': f"credit_{customer_id}@example.com",
            'customer_phone': customer.get('phone', ''),
            'customer_address': 'Credit Purchase',
            'customer': {
                'name': customer.get('full_name', 'Credit Customer'),
                'email': f"credit_{customer_id}@example.com",
                'phone': customer.get('phone', ''),
                'address': 'Credit Purchase'
            },
            'user_id': staff_name,
            'user_name': staff_name,
            'user_role': 'admin',
            'staff_name': staff_name
        }
        
        print(f"📤 Creating credit order entry: {order_id}")
        
        order_response = requests.post(
            f"{Config.SUPABASE_URL}/rest/v1/orders",
            headers=Config.SUPABASE_HEADERS,
            json=order_data,
            timeout=15
        )
        
        if order_response.status_code in [200, 201]:
            print(f"✅ Credit order created: {order_id}")
            order_created = True
        else:
            print(f"⚠️ Could not create credit order: {order_response.status_code}")
            order_created = False
        
        # Clear caches
        try:
            import utils.data
            utils.data.orders_cache = []
            utils.data.products_cache = []
        except:
            pass
        
        return {
            'success': True,
            'balance_after': new_balance,
            'customer_name': customer.get('full_name'),
            'transaction_id': transaction_id,
            'order_id': order_id if order_created else None,
            'order_created': order_created,
            'total_amount': total_amount,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'profit_margin': round(profit_margin, 1),
            'items': item_details,
            'message': f'Credit purchase recorded. New balance: KSh {new_balance:,.2f}'
        }
        
    except Exception as e:
        print(f"❌ Error recording credit purchase: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': str(e)}

# ============================================================
# CREDIT PAYMENT
# ============================================================

def record_credit_payment(customer_id, amount, staff_name, notes=""):
    """Record a credit payment with balance validation"""
    try:
        import uuid
        
        print(f"🔍 record_credit_payment called")
        print(f"💰 Amount: {amount}")
        
        # Get customer
        customer = get_credit_customer_by_id(customer_id)
        if not customer:
            return {'success': False, 'message': 'Customer not found'}
        
        current_balance = float(customer.get('current_balance', 0))
        amount = float(amount)
        
        # ✅ FIX: Validate payment doesn't exceed balance
        if amount > current_balance:
            return {
                'success': False,
                'message': f'❌ Payment exceeds balance. Balance: KSh {current_balance:,.2f}',
                'current_balance': current_balance,
                'payment_amount': amount
            }
        
        new_balance = current_balance - amount
        
        # ✅ Create payment transaction
        transaction_id = f'TXN-{uuid.uuid4().hex[:8].upper()}'
        
        transaction_data = {
            'transaction_id': transaction_id,
            'customer_id': customer_id,
            'transaction_type': 'payment',
            'amount': amount,
            'balance_after': new_balance,
            'staff_name': staff_name,
            'notes': notes or '',
            'payment_status': 'completed' if new_balance == 0 else 'partial',
            'created_at': datetime.utcnow().isoformat()
        }
        
        print(f"📤 Inserting payment: {transaction_data}")
        
        response = requests.post(
            f"{Config.SUPABASE_URL}/rest/v1/credit_transactions",
            headers=Config.SUPABASE_HEADERS,
            json=transaction_data,
            timeout=30
        )
        
        print(f"📥 Response status: {response.status_code}")
        
        if response.status_code not in [200, 201]:
            return {
                'success': False,
                'message': f'Failed to record payment: {response.status_code}',
                'error': response.text
            }
        
        print(f"✅ Payment saved")
        
        # Update customer balance
        update_data = {
            'current_balance': new_balance,
            'total_payments': float(customer.get('total_payments', 0)) + amount,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        update_response = requests.patch(
            f"{Config.SUPABASE_URL}/rest/v1/credit_customers?customer_id=eq.{customer_id}",
            headers=Config.SUPABASE_HEADERS,
            json=update_data,
            timeout=30
        )
        
        if update_response.status_code not in [200, 204]:
            return {
                'success': False,
                'message': f'Payment recorded but failed to update balance: {update_response.status_code}'
            }
        
        return {
            'success': True,
            'balance_after': new_balance,
            'customer_name': customer.get('full_name'),
            'amount_paid': amount,
            'remaining_balance': new_balance,
            'payment_status': 'completed' if new_balance == 0 else 'partial',
            'message': f'Payment recorded. Remaining balance: KSh {new_balance:,.2f}'
        }
        
    except Exception as e:
        print(f"❌ Error recording payment: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': str(e)}

# ============================================================
# OFFLINE CREDIT ORDER SUPPORT
# ============================================================

def save_credit_order_offline(order_data):
    """Save credit order locally when offline"""
    try:
        from utils.storage import load_json_data, save_json_data
        
        json_data = load_json_data()
        json_data.setdefault('credit_order_queue', [])
        
        json_data['credit_order_queue'].append({
            **order_data,
            'queued_at': datetime.utcnow().isoformat(),
            'is_credit': True
        })
        
        save_json_data(json_data)
        print(f"💾 Credit order saved offline: {order_data.get('order_id', 'unknown')}")
        return {'success': True, 'queued': True, 'message': 'Credit order saved locally. Will sync when online.'}
        
    except Exception as e:
        print(f"❌ Error saving credit order offline: {e}")
        return {'success': False, 'message': str(e)}

def process_credit_order_with_offline(customer_id, items, total_amount, staff_name, notes=""):
    """Process credit order - try online, fallback to offline"""
    try:
        import uuid
        
        print(f"🔄 Processing credit order with offline support")
        
        # Try online first
        result = record_credit_purchase(customer_id, items, total_amount, staff_name, notes)
        
        if result.get('success'):
            print(f"✅ Credit order recorded online")
            return result
        
        # If online fails, save offline
        print(f"⚠️ Online failed, saving offline...")
        
        order_data = {
            'order_id': f'CREDIT-OFFLINE-{uuid.uuid4().hex[:8].upper()}',
            'customer_id': customer_id,
            'items': items,
            'total_amount': total_amount,
            'staff_name': staff_name,
            'notes': notes or 'Offline credit order'
        }
        
        return save_credit_order_offline(order_data)
        
    except Exception as e:
        print(f"❌ Error processing credit order: {e}")
        return save_credit_order_offline({
            'order_id': f'CREDIT-OFFLINE-{uuid.uuid4().hex[:8].upper()}',
            'customer_id': customer_id,
            'items': items,
            'total_amount': total_amount,
            'staff_name': staff_name,
            'notes': notes or 'Offline credit order (error fallback)'
        })

def sync_credit_orders_offline():
    """Sync offline credit orders when back online"""
    try:
        from utils.storage import load_json_data, save_json_data
        
        json_data = load_json_data()
        queue = json_data.get('credit_order_queue', [])
        
        if not queue:
            print("✅ No credit orders to sync")
            return {'success': True, 'synced': 0, 'failed': 0}
        
        print(f"📦 Found {len(queue)} offline credit orders to sync")
        
        synced = []
        failed = []
        
        for order in queue:
            try:
                result = record_credit_purchase(
                    customer_id=order.get('customer_id'),
                    items=order.get('items', []),
                    total_amount=order.get('total_amount', 0),
                    staff_name=order.get('staff_name', 'System'),
                    notes=order.get('notes', 'Offline credit order')
                )
                
                if result.get('success'):
                    synced.append(order.get('order_id'))
                    print(f"✅ Synced credit order: {order.get('order_id')}")
                else:
                    failed.append(order.get('order_id'))
                    print(f"⚠️ Failed to sync credit order: {order.get('order_id')}")
                    
            except Exception as e:
                failed.append(order.get('order_id'))
                print(f"❌ Error syncing credit order: {e}")
        
        # Update queue - remove synced orders
        json_data['credit_order_queue'] = [o for o in queue if o.get('order_id') not in synced]
        save_json_data(json_data)
        
        return {
            'success': True,
            'synced': len(synced),
            'failed': len(failed),
            'message': f'Synced {len(synced)} orders, {len(failed)} failed'
        }
        
    except Exception as e:
        print(f"❌ Error syncing credit orders: {e}")
        return {'success': False, 'message': str(e)}

# ============================================================
# TRANSACTION FUNCTIONS
# ============================================================

def get_customer_transactions(customer_id):
    """Get all transactions for a customer"""
    try:
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/credit_transactions?customer_id=eq.{customer_id}&order=created_at.desc",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return []
            
    except Exception as e:
        print(f"❌ Error getting transactions: {e}")
        return []

def get_all_credit_transactions():
    """Get all credit transactions"""
    try:
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/credit_transactions?select=*&order=created_at.desc",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return []
            
    except Exception as e:
        print(f"❌ Error getting all credit transactions: {e}")
        return []

def get_customer_balance(customer_id):
    """Get current balance for a customer"""
    try:
        customer = get_credit_customer_by_id(customer_id)
        if customer:
            return {
                'customer_id': customer_id,
                'customer_name': customer.get('full_name'),
                'current_balance': customer.get('current_balance', 0),
                'credit_limit': customer.get('credit_limit', 0),
                'available_credit': customer.get('credit_limit', 0) - customer.get('current_balance', 0),
                'total_purchases': customer.get('total_purchases', 0),
                'total_payments': customer.get('total_payments', 0),
                'total_cost': customer.get('total_cost', 0),
                'total_profit': customer.get('total_profit', 0)
            }
        else:
            return None
            
    except Exception as e:
        print(f"❌ Error getting balance: {e}")
        return None

# ============================================================
# PROFIT TRACKING FUNCTIONS
# ============================================================

def get_customer_profit_summary(customer_id):
    """Get profit summary for a specific customer"""
    try:
        customer = get_credit_customer_by_id(customer_id)
        if not customer:
            return {'success': False, 'message': 'Customer not found'}
        
        transactions = get_customer_transactions(customer_id)
        
        total_sales = 0
        total_cost = 0
        total_profit = 0
        
        for tx in transactions:
            if tx.get('transaction_type') == 'purchase':
                total_sales += float(tx.get('amount', 0))
                total_cost += float(tx.get('total_cost', 0))
                total_profit += float(tx.get('profit', 0))
        
        margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
        
        return {
            'success': True,
            'customer_id': customer_id,
            'customer_name': customer.get('full_name'),
            'total_sales': total_sales,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'profit_margin': round(margin, 1),
            'remaining_balance': customer.get('current_balance', 0),
            'credit_limit': customer.get('credit_limit', 0),
            'total_purchases': customer.get('total_purchases', 0),
            'total_payments': customer.get('total_payments', 0)
        }
        
    except Exception as e:
        print(f"❌ Error getting customer profit summary: {e}")
        return {'success': False, 'message': str(e)}

# ============================================================
# SUMMARY FUNCTIONS
# ============================================================

def get_all_credit_profit_summary():
    """Get profit summary for all credit customers - Collection rate capped at 100%"""
    try:
        customers = get_all_credit_customers()
        
        total_sales = 0
        total_cost = 0
        total_profit = 0
        total_outstanding = 0
        total_payments = 0
        
        for customer in customers:
            total_sales += float(customer.get('total_purchases', 0))
            total_cost += float(customer.get('total_cost', 0))
            total_profit += float(customer.get('total_profit', 0))
            total_outstanding += float(customer.get('current_balance', 0))
            total_payments += float(customer.get('total_payments', 0))
        
        margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
        
        # ✅ FIX: Cap collection rate at 100%
        if total_sales > 0:
            collection_rate = (total_payments / total_sales * 100)
            if collection_rate > 100:
                collection_rate = 100
            collection_rate = round(collection_rate, 1)
        else:
            collection_rate = 0
        
        return {
            'success': True,
            'total_credit_sales': total_sales,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'profit_margin': round(margin, 1),
            'total_outstanding': total_outstanding,
            'total_payments_received': total_payments,
            'collection_rate': collection_rate,
            'total_customers': len(customers),
            'active_customers': len([c for c in customers if c.get('account_status') == 'active'])
        }
        
    except Exception as e:
        print(f"❌ Error getting all credit profit summary: {e}")
        return {
            'success': False,
            'total_credit_sales': 0,
            'total_cost': 0,
            'total_profit': 0,
            'profit_margin': 0,
            'total_outstanding': 0,
            'total_payments_received': 0,
            'collection_rate': 0,
            'total_customers': 0,
            'active_customers': 0
        }

def get_credit_summary():
    """Get credit summary statistics - Collection rate capped at 100%"""
    try:
        customers = get_all_credit_customers()
        
        total_customers = len(customers)
        active_customers = len([c for c in customers if c.get('account_status') == 'active'])
        total_balance = sum(c.get('current_balance', 0) for c in customers)
        total_credit_limit = sum(c.get('credit_limit', 0) for c in customers)
        total_purchases = sum(c.get('total_purchases', 0) for c in customers)
        total_payments = sum(c.get('total_payments', 0) for c in customers)
        total_cost = sum(c.get('total_cost', 0) for c in customers)
        total_profit = sum(c.get('total_profit', 0) for c in customers)
        
        # ✅ FIX: Cap collection rate at 100%
        if total_purchases > 0:
            collection_rate = (total_payments / total_purchases * 100)
            if collection_rate > 100:
                collection_rate = 100
            collection_rate = round(collection_rate, 1)
        else:
            collection_rate = 0
        
        # ✅ FIX: Profit margin
        profit_margin = (total_profit / total_purchases * 100) if total_purchases > 0 else 0
        
        return {
            'total_customers': total_customers,
            'active_customers': active_customers,
            'inactive_customers': total_customers - active_customers,
            'total_balance': total_balance,
            'total_credit_limit': total_credit_limit,
            'total_purchases': total_purchases,
            'total_payments': total_payments,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'profit_margin': round(profit_margin, 1),
            'collection_rate': collection_rate,
            'average_balance': total_balance / active_customers if active_customers > 0 else 0
        }
        
    except Exception as e:
        print(f"❌ Error getting credit summary: {e}")
        return {
            'total_customers': 0,
            'active_customers': 0,
            'inactive_customers': 0,
            'total_balance': 0,
            'total_credit_limit': 0,
            'total_purchases': 0,
            'total_payments': 0,
            'total_cost': 0,
            'total_profit': 0,
            'profit_margin': 0,
            'collection_rate': 0,
            'average_balance': 0
        }

def get_overdue_customers():
    """Get customers with overdue payments"""
    try:
        customers = get_all_credit_customers()
        overdue = []
        
        for c in customers:
            if c.get('account_status') != 'active':
                continue
            if c.get('current_balance', 0) <= 0:
                continue
            
            overdue.append({
                'customer_id': c.get('customer_id'),
                'full_name': c.get('full_name'),
                'phone': c.get('phone'),
                'balance': c.get('current_balance', 0),
                'credit_limit': c.get('credit_limit', 0),
                'total_purchases': c.get('total_purchases', 0),
                'total_payments': c.get('total_payments', 0),
                'days_overdue': 0
            })
        
        overdue.sort(key=lambda x: x['balance'], reverse=True)
        return overdue
        
    except Exception as e:
        print(f"❌ Error getting overdue customers: {e}")
        return []

def get_monthly_credit_report(year=None):
    """Get monthly credit report"""
    try:
        if not year:
            year = datetime.utcnow().year
        
        transactions = get_all_credit_transactions()
        months = {}
        
        for tx in transactions:
            date_str = tx.get('created_at', '')
            tx_date = None
            
            if date_str:
                try:
                    if ' ' in date_str:
                        clean_date = date_str.split(' ')[0]
                        tx_date = datetime.strptime(clean_date, '%Y-%m-%d')
                    elif 'T' in date_str:
                        clean_date = date_str.replace('Z', '').replace('+00:00', '')
                        tx_date = datetime.fromisoformat(clean_date[:19])
                    else:
                        tx_date = datetime.strptime(date_str[:10], '%Y-%m-%d')
                except:
                    tx_date = datetime.utcnow()
            
            if not tx_date:
                tx_date = datetime.utcnow()
            
            if tx_date.year != year:
                continue
            
            month_key = tx_date.strftime('%b %Y')
            
            if month_key not in months:
                months[month_key] = {
                    'month': month_key,
                    'sales': 0,
                    'payments': 0,
                    'profit': 0,
                    'cost': 0,
                    'transactions': 0
                }
            
            tx_type = tx.get('transaction_type', '').lower()
            amount = float(tx.get('amount', 0))
            
            if tx_type == 'payment':
                months[month_key]['payments'] += amount
            else:
                months[month_key]['sales'] += amount
                months[month_key]['cost'] += float(tx.get('total_cost', 0))
                months[month_key]['profit'] += float(tx.get('profit', 0))
            
            months[month_key]['transactions'] += 1
        
        report = list(months.values())
        month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        report.sort(key=lambda x: month_order.index(x['month'].split()[0]) if x['month'].split()[0] in month_order else 99)
        
        return report
        
    except Exception as e:
        print(f"❌ Error getting monthly credit report: {e}")
        return []

print("✅ Credit module loaded successfully with order creation for credit purchases!")
