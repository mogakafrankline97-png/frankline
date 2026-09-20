import os
import json
import uuid
import requests
from datetime import datetime
from config import Config

# ============================================================
# ENVIRONMENT DETECTION
# ============================================================
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('NOW_REGION') is not None
print(f"🏭 Supplier module running on: {'Vercel' if IS_VERCEL else 'Localhost'}")

# ============================================================
# SUPPLIER MANAGEMENT FUNCTIONS
# ============================================================

def generate_supplier_id():
    """Generate a unique supplier ID"""
    return f'SUP-{uuid.uuid4().hex[:8].upper()}'

def get_supabase_headers():
    """Get Supabase headers with proper auth"""
    return Config.SUPABASE_HEADERS

def add_supplier(supplier_data):
    """Add a new supplier to Supabase"""
    try:
        if not supplier_data.get('supplier_id'):
            supplier_data['supplier_id'] = generate_supplier_id()
        
        supplier_data['created_at'] = datetime.utcnow().isoformat()
        supplier_data['updated_at'] = datetime.utcnow().isoformat()
        
        if not supplier_data.get('status'):
            supplier_data['status'] = 'active'
        
        # Clean data - remove None values
        clean_data = {k: v for k, v in supplier_data.items() if v is not None}
        
        response = requests.post(
            f"{Config.SUPABASE_URL}/rest/v1/suppliers",
            headers=Config.SUPABASE_HEADERS,
            json=clean_data,
            timeout=30  # Increased timeout for Vercel
        )
        
        if response.status_code in [200, 201]:
            return {
                'success': True,
                'message': 'Supplier added successfully',
                'data': response.json() if response.json() else supplier_data
            }
        else:
            print(f"❌ Failed to add supplier: {response.status_code} - {response.text}")
            return {
                'success': False,
                'message': f'Failed to add supplier: {response.status_code}',
                'error': response.text
            }
            
    except requests.exceptions.Timeout:
        print("❌ Timeout adding supplier")
        return {'success': False, 'message': 'Request timeout - please try again'}
    except Exception as e:
        print(f"❌ Error adding supplier: {e}")
        return {'success': False, 'message': str(e)}

def get_all_suppliers():
    """Get all suppliers from Supabase"""
    try:
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/suppliers?select=*&order=created_at.desc",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            suppliers = response.json()
            # Clean dates for display
            for supplier in suppliers:
                if supplier.get('created_at'):
                    try:
                        supplier['created_at'] = supplier['created_at'][:10]
                    except:
                        pass
            return suppliers
        else:
            print(f"⚠️ Failed to get suppliers: {response.status_code}")
            return []
            
    except requests.exceptions.Timeout:
        print("⚠️ Timeout getting suppliers")
        return []
    except Exception as e:
        print(f"❌ Error getting suppliers: {e}")
        return []

def get_supplier_by_id(supplier_id):
    """Get a specific supplier by ID"""
    try:
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/suppliers?supplier_id=eq.{supplier_id}&select=*",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            suppliers = response.json()
            return suppliers[0] if suppliers else None
        else:
            return None
            
    except Exception as e:
        print(f"❌ Error getting supplier: {e}")
        return None

def update_supplier(supplier_id, update_data):
    """Update an existing supplier"""
    try:
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Clean data - remove None values
        clean_data = {k: v for k, v in update_data.items() if v is not None}
        
        response = requests.patch(
            f"{Config.SUPABASE_URL}/rest/v1/suppliers?supplier_id=eq.{supplier_id}",
            headers=Config.SUPABASE_HEADERS,
            json=clean_data,
            timeout=30
        )
        
        if response.status_code in [200, 204]:
            return {
                'success': True,
                'message': 'Supplier updated successfully'
            }
        else:
            print(f"❌ Failed to update supplier: {response.status_code} - {response.text}")
            return {
                'success': False,
                'message': f'Failed to update supplier: {response.status_code}'
            }
            
    except Exception as e:
        print(f"❌ Error updating supplier: {e}")
        return {'success': False, 'message': str(e)}

def delete_supplier(supplier_id):
    """
    Permanently delete a supplier from Supabase.
    Also unlinks any products referencing this supplier.
    """
    try:
        if not supplier_id:
            return {'success': False, 'message': 'Supplier ID is required'}
        
        print(f"🗑️ Deleting supplier: {supplier_id}")
        
        # Count linked products first (for reporting)
        product_count = 0
        try:
            prod_check = requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/products?supplier_id=eq.{supplier_id}&select=id",
                headers=Config.SUPABASE_HEADERS,
                timeout=10
            )
            if prod_check.status_code == 200:
                product_count = len(prod_check.json())
        except Exception as e:
            print(f"⚠️ Could not count linked products: {e}")
        
        # Unlink products by setting supplier_id to null
        if product_count > 0:
            try:
                unlink_response = requests.patch(
                    f"{Config.SUPABASE_URL}/rest/v1/products?supplier_id=eq.{supplier_id}",
                    headers=Config.SUPABASE_HEADERS,
                    json={'supplier_id': None},
                    timeout=30
                )
                if unlink_response.status_code in [200, 204]:
                    print(f"✅ Unlinked {product_count} product(s) from supplier")
                else:
                    print(f"⚠️ Could not unlink products: {unlink_response.status_code}")
            except Exception as e:
                print(f"⚠️ Error unlinking products: {e}")
        
        # Actually DELETE the supplier row from Supabase
        response = requests.delete(
            f"{Config.SUPABASE_URL}/rest/v1/suppliers?supplier_id=eq.{supplier_id}",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if response.status_code in [200, 204]:
            msg = 'Supplier deleted successfully'
            if product_count > 0:
                msg += f' ({product_count} product(s) unlinked)'
            print(f"✅ {msg}")
            return {
                'success': True,
                'message': msg,
                'unlinked_products': product_count
            }
        else:
            print(f"❌ Failed to delete supplier: {response.status_code} - {response.text}")
            return {
                'success': False,
                'message': f'Failed to delete supplier: HTTP {response.status_code}',
                'error': response.text
            }
            
    except requests.exceptions.Timeout:
        print("❌ Timeout deleting supplier")
        return {'success': False, 'message': 'Request timeout - please try again'}
    except Exception as e:
        print(f"❌ Error deleting supplier: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': str(e)}

def get_supplier_products(supplier_id):
    """Get all products from a specific supplier"""
    try:
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/products?supplier_id=eq.{supplier_id}&select=*",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return []
            
    except Exception as e:
        print(f"❌ Error getting supplier products: {e}")
        return []

def get_low_stock_products(supplier_id=None):
    """Get products that need restocking (below reorder level)"""
    try:
        # First, get all products with reorder_level set
        query = "reorder_level=not.is.null"
        if supplier_id:
            query += f"&supplier_id=eq.{supplier_id}"
        
        response = requests.get(
            f"{Config.SUPABASE_URL}/rest/v1/products?{query}&select=*",
            headers=Config.SUPABASE_HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            products = response.json()
            # Filter products where stock < reorder_level
            low_stock = [
                p for p in products 
                if p.get('stock', 0) < p.get('reorder_level', 10)
            ]
            return low_stock
        else:
            return []
            
    except Exception as e:
        print(f"❌ Error getting low stock products: {e}")
        return []

def update_supplier_product_count(supplier_id):
    """Update the total_products count for a supplier"""
    try:
        products = get_supplier_products(supplier_id)
        count = len(products)
        
        return update_supplier(supplier_id, {'total_products': count})
        
    except Exception as e:
        print(f"❌ Error updating supplier product count: {e}")
        return {'success': False, 'message': str(e)}

def get_supplier_summary():
    """Get summary statistics for suppliers"""
    try:
        suppliers = get_all_suppliers()
        
        total_suppliers = len(suppliers)
        active_suppliers = len([s for s in suppliers if s.get('status') == 'active'])
        inactive_suppliers = total_suppliers - active_suppliers
        total_products = sum(s.get('total_products', 0) for s in suppliers)
        
        return {
            'total_suppliers': total_suppliers,
            'active_suppliers': active_suppliers,
            'inactive_suppliers': inactive_suppliers,
            'total_products': total_products
        }
        
    except Exception as e:
        print(f"❌ Error getting supplier summary: {e}")
        return {
            'total_suppliers': 0,
            'active_suppliers': 0,
            'inactive_suppliers': 0,
            'total_products': 0
        }
