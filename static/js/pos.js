// ============================================================
// POS MAIN JAVASCRIPT
// ============================================================

// DATA
const allProducts = window.productsData || [];
let filteredProducts = [];
let currentCategory = 'all';
let posCart = [];
let discountValue = 0;
let discountType = 'percentage';
let returnItems = [];
let heldOrders = [];
let totalDiscount = 0;

// ============================================================
// CLOCK
// ============================================================
function updateClock() {
    document.getElementById('clockDisplay').textContent = new Date().toLocaleTimeString('en-KE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
setInterval(updateClock, 1000);
updateClock();

// ============================================================
// ONLINE/OFFLINE STATUS
// ============================================================
function updateOnlineStatus() {
    const badge = document.getElementById('onlineBadge');
    const isOnline = navigator.onLine;
    
    if (isOnline) {
        badge.textContent = '● LIVE';
        badge.className = 'badge';
        badge.style.background = '#34d399';
        badge.style.color = '#0f172a';
    } else {
        badge.textContent = '● OFFLINE';
        badge.className = 'badge offline';
        badge.style.background = '#f59e0b';
        badge.style.color = '#0f172a';
    }
}

// Update on status change
window.addEventListener('online', updateOnlineStatus);
window.addEventListener('offline', updateOnlineStatus);
updateOnlineStatus();

// ============================================================
// LOAD USER STATS
// ============================================================
function loadUserStats() {
    fetch('/admin/api/user-stats')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const todaySales = 'KSh ' + (data.today_revenue || 0).toLocaleString();
                const todayOrders = data.today_orders || 0;
                
                document.getElementById('userTodaySales').textContent = todaySales;
                document.getElementById('userTodayOrders').textContent = todayOrders;
            }
        })
        .catch(err => console.error('User stats error:', err));
}

// ============================================================
// LOAD SALES STATS
// ============================================================
function loadSalesStats() {
    fetch('/admin/api/sales-stats')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const todaySales = 'KSh ' + (data.today_revenue || 0).toLocaleString();
                const todayOrders = data.today_orders || 0;
                const todayReturns = data.today_returns || 0;
                const totalCust = data.total_customers || 0;
                const totalProds = data.total_products || 0;
                
                document.getElementById('todaySales').textContent = todaySales;
                document.getElementById('todayOrders').textContent = todayOrders;
                document.getElementById('todayReturns').textContent = todayReturns;
                document.getElementById('totalCustomers').textContent = totalCust;
                document.getElementById('totalProducts').textContent = totalProds;
            }
        })
        .catch(err => console.error('Stats error:', err));
}

// ============================================================
// SYNC FUNCTIONS
// ============================================================
function syncOfflineOrders() {
    if (!navigator.onLine) {
        showToast('📡 Offline - will sync when online', 'warning');
        return;
    }
    
    showToast('🔄 Syncing offline orders...', 'info');
    
    fetch('/admin/api/sync-queue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(r => r.json())
    .then(data => {
        if (data.offline) {
            showToast('📡 Supabase offline - orders remain in queue', 'warning');
            checkUnsyncedOrders();
            return;
        }
        
        if (data.success) {
            if (data.synced > 0) {
                showToast(`✅ Synced ${data.synced} offline orders!`, 'success');
                loadUserStats();
                loadSalesStats();
                checkUnsyncedOrders();
            } else if (data.failed > 0) {
                showToast(`⚠️ ${data.failed} orders failed. Will retry.`, 'warning');
                checkUnsyncedOrders();
            } else {
                showToast('✅ All orders are synced!', 'success');
                checkUnsyncedOrders();
            }
        } else {
            showToast('⚠️ Sync pending - orders saved offline', 'warning');
            checkUnsyncedOrders();
        }
    })
    .catch(err => {
        console.error('Sync error:', err);
        showToast('⚠️ Cannot sync - orders saved offline', 'warning');
        checkUnsyncedOrders();
    });
}

function checkUnsyncedOrders() {
    fetch('/admin/api/unsynced-count')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const statusEl = document.getElementById('syncStatus');
                const countEl = document.getElementById('unsyncedCount');
                
                if (statusEl) {
                    if (data.count > 0) {
                        statusEl.style.display = 'inline-flex';
                        statusEl.className = '';
                        if (countEl) countEl.textContent = data.count;
                        
                        let orderIds = data.orders || [];
                        let tooltip = orderIds.length > 0 ? 'Orders: ' + orderIds.join(', ') : '';
                        statusEl.title = tooltip;
                    } else {
                        statusEl.style.display = 'none';
                    }
                }
            }
        })
        .catch(err => console.error('Error checking sync status:', err));
}

function manualSync() {
    syncOfflineOrders();
}

// ============================================================
// AUTO-SYNC EVENTS
// ============================================================
window.addEventListener('online', function() {
    showToast('🔄 Back online! Syncing orders...', 'info');
    updateOnlineStatus();
    setTimeout(syncOfflineOrders, 2000);
    setTimeout(checkUnsyncedOrders, 1000);
});

// ============================================================
// SEARCH & FILTER
// ============================================================
function searchProducts(query) {
    const searchTerm = query.toLowerCase().trim();
    document.getElementById('searchClear').classList.toggle('hidden', searchTerm === '');
    
    if (searchTerm === '') {
        if (currentCategory === 'all') {
            filteredProducts = allProducts.slice(0, 50);
            document.getElementById('resultCount').textContent = `${filteredProducts.length} of ${allProducts.length} products`;
        } else {
            filteredProducts = allProducts.filter(p => p.category === currentCategory).slice(0, 50);
            document.getElementById('resultCount').textContent = `${filteredProducts.length} in "${currentCategory}"`;
        }
    } else {
        const results = allProducts.filter(p => {
            const name = (p.name || '').toLowerCase();
            const category = (p.category || '').toLowerCase();
            const id = (p.id || '').toLowerCase();
            return name.includes(searchTerm) || category.includes(searchTerm) || id.includes(searchTerm);
        });
        filteredProducts = results.slice(0, 100);
        document.getElementById('resultCount').textContent = `${results.length} found${results.length > 100 ? ' (showing 100)' : ''}`;
    }
    renderProducts();
}

function filterByCategory(category, element) {
    document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
    if (element) element.classList.add('active');
    currentCategory = category;
    const searchInput = document.getElementById('posSearch');
    if (searchInput.value.trim() === '') {
        filteredProducts = category === 'all' ? allProducts.slice(0, 50) : allProducts.filter(p => p.category === category).slice(0, 50);
        document.getElementById('resultCount').textContent = `${filteredProducts.length} products${category !== 'all' ? ' in "' + category + '"' : ''}`;
        renderProducts();
    } else {
        searchProducts(searchInput.value);
    }
}

function renderProducts() {
    const grid = document.getElementById('posProductGrid');
    if (filteredProducts.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full search-hint">
                <i class="fas fa-search"></i>
                <p>No products found</p>
                <p class="text-xs text-gray-400">Try a different search term</p>
                <div class="shortcuts">💡 Tip: Scan barcode or search by name</div>
            </div>
        `;
        return;
    }
    
    let html = '';
    filteredProducts.forEach(product => {
        const price = Number(product.price) || 0;
        const stock = Number(product.stock) || 0;
        const image = product.image || '';
        const stockClass = stock <= 0 ? 'out' : stock < 10 ? 'low' : stock < 30 ? 'medium' : 'high';
        const stockLabel = stock <= 0 ? 'Out' : stock < 10 ? 'Low' : stock < 30 ? 'Med' : 'In Stock';
        const stockNumberClass = stock <= 0 ? 'low' : stock < 10 ? 'low' : stock < 30 ? 'medium' : 'high';
        const isOutOfStock = stock <= 0;
        
        html += `
            <div class="product-pos-card group" data-id="${product.id || ''}" data-name="${product.name || ''}" data-price="${price}" data-stock="${stock}" data-image="${image}" onclick="${isOutOfStock ? '' : 'addToPOSCart(this)'}">
                <div class="relative">
                    <div class="h-14 w-full bg-gray-50 rounded-lg overflow-hidden mb-1">
                        ${image ? `<img src="${image}" alt="${product.name}" class="w-full h-full object-contain p-1" onerror="this.style.display='none'">` : `<div class="w-full h-full flex items-center justify-center text-gray-300"><i class="fas fa-box text-2xl"></i></div>`}
                    </div>
                    <span class="stock-badge ${stockClass}">${stockLabel}</span>
                    ${isOutOfStock ? '<span class="absolute inset-0 bg-white/60 flex items-center justify-center text-xs font-bold text-red-500">OUT OF STOCK</span>' : ''}
                </div>
                <p class="text-[9px] font-semibold text-[#0f172a] truncate">${product.name || 'Product'}</p>
                <p class="price-tag">KSh ${price.toLocaleString()}</p>
                <div class="stock-count">
                    <i class="fas fa-boxes"></i>
                    <span class="number ${stockNumberClass}">${stock}</span>
                    <span class="text-[8px] text-gray-400">in stock</span>
                </div>
                <button class="add-btn" ${isOutOfStock ? 'disabled' : ''}>
                    ${isOutOfStock ? 'Out of Stock' : '<i class="fas fa-plus"></i> Add'}
                </button>
            </div>
        `;
    });
    grid.innerHTML = html;
}

function clearSearch() {
    document.getElementById('posSearch').value = '';
    document.getElementById('searchClear').classList.add('hidden');
    searchProducts('');
}

function scanBarcode() {
    const scannerInput = prompt('📷 Scan barcode or enter product ID:');
    if (scannerInput && scannerInput.trim()) {
        document.getElementById('posSearch').value = scannerInput.trim();
        searchProducts(scannerInput.trim());
        showToast('🔍 Searching for: ' + scannerInput.trim(), 'info');
    }
}

// ============================================================
// CART FUNCTIONS
// ============================================================
function addToPOSCart(element) {
    const card = element.closest ? element.closest('.product-pos-card') : element;
    if (!card) { showToast('❌ Product not found'); return; }
    
    const productId = String(card.dataset.id || '').trim();
    const name = String(card.dataset.name || 'Product').trim();
    const price = parseFloat(card.dataset.price) || 0;
    const stock = parseInt(card.dataset.stock) || 0;
    const image = String(card.dataset.image || '').trim();
    
    if (!productId || price <= 0) { showToast('❌ Invalid product'); return; }
    if (stock <= 0) { showToast('⚠️ Out of stock!'); return; }
    
    const existing = posCart.find(item => item.id === productId);
    if (existing) {
        if (existing.quantity < stock) { existing.quantity++; } 
        else { showToast('⚠️ Not enough stock!'); return; }
    } else {
        posCart.push({ id: productId, name, price, image, stock, quantity: 1 });
    }
    updatePOSUI();
    showToast('✅ Added: ' + name + ' (' + stock + ' left)');
}

function updatePOSQuantity(index, delta) {
    if (!posCart[index]) return;
    const newQty = posCart[index].quantity + delta;
    if (newQty <= 0) { posCart.splice(index, 1); } 
    else if (newQty <= posCart[index].stock) { posCart[index].quantity = newQty; } 
    else { showToast('⚠️ Not enough stock!'); return; }
    updatePOSUI();
}

function removePOSItem(index) {
    posCart.splice(index, 1);
    updatePOSUI();
    showToast('🗑️ Removed');
}

function voidLastItem() {
    if (posCart.length === 0) { showToast('⚠️ Cart is empty', 'warning'); return; }
    const removed = posCart.pop();
    updatePOSUI();
    showToast('↩️ Voided: ' + removed.name, 'info');
}

function clearCart() {
    if (posCart.length > 0 && !confirm('Clear all items?')) return;
    posCart = [];
    discountValue = 0;
    document.getElementById('discountDisplay').textContent = '0%';
    updatePOSUI();
    showToast('🔄 Cart cleared');
}

function updatePOSUI() {
    const itemsList = document.getElementById('posCartItemsList');
    const emptyMessage = document.getElementById('emptyCartMessage');
    const subtotalEl = document.getElementById('posSubtotal');
    const totalEl = document.getElementById('posTotal');
    const discountEl = document.getElementById('posDiscount');
    const itemCountEl = document.getElementById('itemCount');
    const cartStatsEl = document.getElementById('cartStats');
    const placeBtn = document.getElementById('posPlaceOrderBtn');
    
    let subtotal = posCart.reduce((sum, item) => sum + (Number(item.price) || 0) * (Number(item.quantity) || 0), 0);
    const discountAmount = discountType === 'percentage' ? (subtotal * discountValue / 100) : discountValue;
    const total = Math.max(0, subtotal - discountAmount);
    
    if (subtotalEl) subtotalEl.textContent = 'KSh ' + subtotal.toLocaleString();
    if (discountEl) discountEl.textContent = '-KSh ' + discountAmount.toLocaleString();
    if (totalEl) totalEl.textContent = 'KSh ' + total.toLocaleString();
    
    const totalQty = posCart.reduce((sum, i) => sum + (Number(i.quantity) || 0), 0);
    if (itemCountEl) itemCountEl.textContent = totalQty + ' items';
    if (cartStatsEl) cartStatsEl.textContent = totalQty;
    
    if (placeBtn) {
        placeBtn.disabled = posCart.length === 0;
        placeBtn.style.opacity = posCart.length === 0 ? '0.5' : '1';
    }
    
    if (emptyMessage) emptyMessage.style.display = posCart.length === 0 ? 'block' : 'none';
    if (!itemsList) return;
    if (posCart.length === 0) { itemsList.innerHTML = ''; return; }
    
    let html = '';
    posCart.forEach((item, index) => {
        const price = Number(item.price) || 0;
        const quantity = Number(item.quantity) || 1;
        html += `
            <div class="pos-cart-item flex items-center gap-2 bg-gray-50 rounded-lg p-1.5 border border-gray-100 hover:border-green-200 transition-all">
                <div class="w-8 h-8 rounded-lg overflow-hidden bg-white flex-shrink-0 flex items-center justify-center">
                    ${item.image ? `<img src="${item.image}" class="w-full h-full object-contain p-1" onerror="this.style.display='none'">` : '<span class="text-lg">📱</span>'}
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-[10px] font-semibold truncate">${item.name || 'Product'}</p>
                    <p class="cart-item-price text-xs">KSh ${price.toLocaleString()}</p>
                    <p class="text-[8px] text-gray-400">Stock: ${item.stock}</p>
                </div>
                <div class="flex items-center gap-0.5">
                    <button onclick="updatePOSQuantity(${index}, -1)" class="w-5 h-5 rounded-full bg-gray-200 hover:bg-gray-300 text-[10px] font-bold transition-all">-</button>
                    <span class="text-xs font-bold w-5 text-center">${quantity}</span>
                    <button onclick="updatePOSQuantity(${index}, 1)" class="w-5 h-5 rounded-full bg-gray-200 hover:bg-gray-300 text-[10px] font-bold transition-all">+</button>
                    <button onclick="removePOSItem(${index})" class="text-red-400 hover:text-red-600 text-xs ml-0.5 p-1 transition-all">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
    });
    itemsList.innerHTML = html;
}

// ============================================================
// DISCOUNT
// ============================================================
function toggleDiscountModal() {
    document.getElementById('discountModal').classList.toggle('hidden');
    updateDiscountPreview();
}

function closeDiscountModal(event) {
    if (!event || event.target.classList.contains('modal-overlay') || event.target.classList.contains('close-btn')) {
        document.getElementById('discountModal').classList.add('hidden');
    }
}

function setDiscountPreset(value) {
    document.getElementById('discountType').value = 'percentage';
    document.getElementById('discountValue').value = value;
    updateDiscountPreview();
}

function updateDiscountPreview() {
    const type = document.getElementById('discountType').value;
    const value = parseFloat(document.getElementById('discountValue').value) || 0;
    const subtotal = posCart.reduce((sum, item) => sum + (Number(item.price) || 0) * (Number(item.quantity) || 0), 0);
    const discountAmount = type === 'percentage' ? (subtotal * value / 100) : value;
    const total = Math.max(0, subtotal - discountAmount);
    
    document.getElementById('discountSubtotal').textContent = 'KSh ' + subtotal.toLocaleString();
    document.getElementById('discountNewTotal').textContent = 'KSh ' + total.toLocaleString();
}

function applyDiscount() {
    discountType = document.getElementById('discountType').value;
    discountValue = parseFloat(document.getElementById('discountValue').value) || 0;
    document.getElementById('discountDisplay').textContent = discountType === 'percentage' ? discountValue + '%' : 'KSh ' + discountValue.toLocaleString();
    closeDiscountModal();
    updatePOSUI();
    showToast('✅ Discount applied!', 'success');
}

// ============================================================
// RETURNS
// ============================================================
function toggleReturnModal() {
    const modal = document.getElementById('returnModal');
    modal.classList.toggle('hidden');
    if (!modal.classList.contains('hidden')) {
        loadReturnItems();
    }
}

function closeReturnModal(event) {
    if (!event || event.target.classList.contains('modal-overlay') || event.target.classList.contains('close-btn')) {
        document.getElementById('returnModal').classList.add('hidden');
    }
}

function loadReturnItems() {
    const container = document.getElementById('returnItemsList');
    if (posCart.length === 0) {
        container.innerHTML = `<p class="text-center text-gray-400 text-sm py-4">No items in cart to return</p>`;
        document.getElementById('refundTotal').textContent = 'KSh 0';
        return;
    }
    
    returnItems = posCart.map((item, index) => ({ ...item, index, selected: true }));
    renderReturnItems();
}

function renderReturnItems() {
    const container = document.getElementById('returnItemsList');
    let html = '';
    let refundTotal = 0;
    
    returnItems.forEach((item, idx) => {
        const total = item.price * item.quantity;
        if (item.selected) refundTotal += total;
        
        html += `
            <div class="flex items-center gap-3 bg-gray-50 rounded-lg p-2 border border-gray-100 hover:border-rose-200 transition-all">
                <input type="checkbox" ${item.selected ? 'checked' : ''} 
                       onchange="toggleReturnItem(${idx})" class="w-4 h-4 accent-rose-500" />
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-semibold truncate">${item.name}</p>
                    <p class="text-xs text-gray-500">Qty: ${item.quantity} × KSh ${item.price.toLocaleString()}</p>
                </div>
                <span class="font-bold text-rose-600 text-sm">KSh ${total.toLocaleString()}</span>
            </div>
        `;
    });
    
    container.innerHTML = html;
    document.getElementById('refundTotal').textContent = 'KSh ' + refundTotal.toLocaleString();
}

function toggleReturnItem(index) {
    returnItems[index].selected = !returnItems[index].selected;
    renderReturnItems();
}

function processReturn() {
    const selectedItems = returnItems.filter(item => item.selected);
    if (selectedItems.length === 0) {
        showToast('⚠️ Select at least one item to return', 'warning');
        return;
    }
    
    const refundTotal = selectedItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const customerName = document.getElementById('posCustomer').value || 'Customer';
    
    if (!confirm(`Process return for ${selectedItems.length} item(s) totaling KSh ${refundTotal.toLocaleString()}?`)) return;
    
    const returnData = {
        items: selectedItems.map(item => ({
            id: item.id,
            name: item.name,
            price: item.price,
            quantity: item.quantity
        })),
        refund_total: refundTotal,
        customer_name: customerName,
        reason: 'Customer return'
    };
    
    const btn = document.querySelector('#returnModal .btn-primary');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    btn.disabled = true;
    
    fetch('/admin/api/process-return', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(returnData)
    })
    .then(r => { if (!r.ok) throw new Error('Network error: ' + r.status); return r.json(); })
    .then(data => {
        if (data.success) {
            const idsToRemove = selectedItems.map(item => item.id);
            posCart = posCart.filter(item => !idsToRemove.includes(item.id));
            closeReturnModal();
            updatePOSUI();
            loadSalesStats();
            showToast(`✅ Return processed! Refund: KSh ${refundTotal.toLocaleString()}`, 'success');
        } else {
            showToast('❌ Error: ' + (data.message || 'Failed to process return'), 'error');
        }
        btn.innerHTML = originalText;
        btn.disabled = false;
    })
    .catch(err => {
        showToast('❌ Error: ' + err.message, 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

// ============================================================
// PLACE ORDER
// ============================================================
function placePOSOrder() {
    if (posCart.length === 0) { showToast('⚠️ Add items first!', 'warning'); return; }
    
    const select = document.getElementById('posCustomer');
    const selectedOption = select.options[select.selectedIndex];
    const customerName = selectedOption ? selectedOption.value : 'Walk-in Customer';
    const customerEmail = selectedOption ? selectedOption.dataset.email || 'walkin@example.com' : 'walkin@example.com';
    const customerPhone = selectedOption ? selectedOption.dataset.phone || 'N/A' : 'N/A';
    
    const subtotal = posCart.reduce((sum, item) => sum + (Number(item.price) || 0) * (Number(item.quantity) || 0), 0);
    const discountAmount = discountType === 'percentage' ? (subtotal * discountValue / 100) : discountValue;
    const total = Math.max(0, subtotal - discountAmount);
    
    const orderItems = posCart.map(item => ({
        product_id: item.id,
        name: item.name || 'Product',
        price: Number(item.price) || 0,
        quantity: Number(item.quantity) || 1,
        total: (Number(item.price) || 0) * (Number(item.quantity) || 1),
        type: 'product'
    }));
    
    const orderData = {
        customer_name: customerName,
        customer_email: customerEmail,
        customer_phone: customerPhone,
        customer_address: 'In-store purchase',
        items: orderItems,
        subtotal: subtotal,
        discount: discountAmount,
        discount_type: discountType,
        discount_value: discountValue,
        shipping: 0,
        total: total,
        source: 'pos'
    };
    
    const btn = document.getElementById('posPlaceOrderBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    btn.disabled = true;
    
    fetch('/admin/pos/place-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderData)
    })
    .then(r => { if (!r.ok) throw new Error('Network error'); return r.json(); })
    .then(data => {
        if (data.success) {
            let message = '✅ Order placed! #' + data.order_id + ' | Total: KSh ' + total.toLocaleString();
            if (data.offline) {
                message += ' (Saved offline - will sync when online)';
                setTimeout(checkUnsyncedOrders, 1000);
            } else if (data.synced) {
                message += ' (Synced to cloud)';
            }
            showToast(message, data.offline ? 'warning' : 'success');
            posCart = [];
            discountValue = 0;
            document.getElementById('discountDisplay').textContent = '0%';
            updatePOSUI();
            loadSalesStats();
            loadUserStats();
        } else {
            showToast('❌ Error: ' + (data.message || 'Unknown error'), 'error');
        }
        btn.innerHTML = originalText;
        btn.disabled = false;
    })
    .catch(err => {
        showToast('❌ Error: ' + err.message, 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

// ============================================================
// HOLD ORDERS
// ============================================================
function holdOrder() {
    if (posCart.length === 0) { showToast('⚠️ Cart is empty', 'warning'); return; }
    heldOrders.push({
        id: Date.now(),
        items: [...posCart],
        customer: document.getElementById('posCustomer').value,
        timestamp: new Date().toLocaleString()
    });
    posCart = [];
    discountValue = 0;
    document.getElementById('discountDisplay').textContent = '0%';
    updatePOSUI();
    renderHeldOrders();
    showToast(`⏸️ Order held! (${heldOrders.length} held orders)`, 'info');
}

function renderHeldOrders() {
    const panel = document.getElementById('heldOrdersPanel');
    const list = document.getElementById('heldOrdersList');
    if (heldOrders.length === 0) {
        panel.classList.add('hidden');
        return;
    }
    panel.classList.remove('hidden');
    let html = '';
    heldOrders.forEach((order, idx) => {
        const total = order.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        html += `
            <div class="held-order-item">
                <span>${order.customer} - KSh ${total.toLocaleString()}</span>
                <div>
                    <button class="restore-btn" onclick="restoreOrder(${idx})">Restore</button>
                    <button class="restore-btn" onclick="removeHeldOrder(${idx})" style="color:#dc2626;background:#fce4ec;">✕</button>
                </div>
            </div>
        `;
    });
    list.innerHTML = html;
}

function restoreOrder(index) {
    if (posCart.length > 0 && !confirm('Current cart has items. Replace with held order?')) return;
    posCart = heldOrders[index].items;
    document.getElementById('posCustomer').value = heldOrders[index].customer;
    heldOrders.splice(index, 1);
    discountValue = 0;
    document.getElementById('discountDisplay').textContent = '0%';
    updatePOSUI();
    renderHeldOrders();
    showToast('✅ Order restored!', 'success');
}

function removeHeldOrder(index) {
    heldOrders.splice(index, 1);
    renderHeldOrders();
    showToast('🗑️ Held order removed');
}

// ============================================================
// CUSTOMER MODAL
// ============================================================
function toggleCustomerModal() { document.getElementById('customerModal').classList.toggle('hidden'); }

function closeCustomerModal(event) {
    if (!event || event.target.classList.contains('modal-overlay') || event.target.classList.contains('close-btn')) {
        document.getElementById('customerModal').classList.add('hidden');
    }
}

function addCustomer(event) {
    event.preventDefault();
    const name = document.getElementById('custName')?.value.trim();
    const email = document.getElementById('custEmail')?.value.trim();
    const phone = document.getElementById('custPhone')?.value.trim();
    if (!name) { showToast('⚠️ Please enter a name', 'warning'); return; }
    
    const select = document.getElementById('posCustomer');
    if (select) {
        const existing = Array.from(select.options).some(opt => opt.value === name);
        if (existing) { showToast('⚠️ Customer already exists!', 'warning'); return; }
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        option.dataset.email = email || '';
        option.dataset.phone = phone || '';
        select.appendChild(option);
        select.value = name;
    }
    document.getElementById('posCustomerEmail').value = email || '';
    document.getElementById('posCustomerPhone').value = phone || '';
    closeCustomerModal();
    showToast('✅ Customer added: ' + name);
    document.getElementById('customerForm').reset();
    loadSalesStats();
}

function selectCustomer() {
    const select = document.getElementById('posCustomer');
    const selectedOption = select.options[select.selectedIndex];
    if (selectedOption) {
        document.getElementById('posCustomerEmail').value = selectedOption.dataset.email || '';
        document.getElementById('posCustomerPhone').value = selectedOption.dataset.phone || '';
    }
}

// ============================================================
// TOAST
// ============================================================
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    if (toast && toastMessage) {
        toast.className = 'toast ' + type;
        toastMessage.textContent = message;
        toast.classList.remove('hidden');
        clearTimeout(window.toastTimeout);
        window.toastTimeout = setTimeout(() => toast.classList.add('hidden'), 4000);
    } else { alert(message); }
}

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') { closeCustomerModal(); closeDiscountModal(); closeReturnModal(); }
    if (e.ctrlKey && e.key === 'Enter') { placePOSOrder(); e.preventDefault(); }
    if (e.key === 'F1') { document.getElementById('posSearch').focus(); e.preventDefault(); }
    if (e.key === 'F2') { toggleCustomerModal(); e.preventDefault(); }
    if (e.key === 'F3') { toggleDiscountModal(); e.preventDefault(); }
    if (e.key === 'F4') { toggleReturnModal(); e.preventDefault(); }
    if (e.key === 'F5') { holdOrder(); e.preventDefault(); }
    if (e.key === 'F6') { manualSync(); e.preventDefault(); }
    if ((e.key === 'Delete' || e.key === 'Backspace') && document.activeElement.id !== 'posSearch') {
        voidLastItem();
        e.preventDefault();
    }
});

// ============================================================
// PWA - IndexedDB Support
// ============================================================

const DB_NAME = 'PricePointDB';
const DB_VERSION = 1;

function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            
            if (!db.objectStoreNames.contains('offline_orders')) {
                const store = db.createObjectStore('offline_orders', { keyPath: 'order_id' });
                store.createIndex('created_at', 'created_at');
                console.log('✅ Created offline_orders store');
            }
        };
        
        request.onsuccess = (event) => {
            console.log('✅ IndexedDB opened successfully');
            resolve(event.target.result);
        };
        
        request.onerror = (event) => {
            console.error('❌ IndexedDB error:', event.target.error);
            reject(event.target.error);
        };
    });
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('posProductGrid').innerHTML = `
        <div class="col-span-full search-hint">
            <i class="fas fa-search"></i>
            <p>Search for products</p>
            <p class="text-xs text-gray-400">${allProducts.length} products available</p>
            <div class="shortcuts">⌨️ F1: Search | F2: Customer | F3: Discount | F4: Return | F5: Hold | F6: Sync | Ctrl+Enter: Checkout</div>
        </div>
    `;
    document.getElementById('resultCount').textContent = `${allProducts.length} products available`;
    updatePOSUI();
    loadSalesStats();
    loadUserStats();
    
    // Check for unsynced orders after 2 seconds
    setTimeout(function() {
        if (navigator.onLine) {
            checkUnsyncedOrders();
            setTimeout(syncOfflineOrders, 3000);
        }
    }, 2000);
    
    console.log('✅ POS Pro v4.0 initialized with ' + allProducts.length + ' products');
    console.log('📡 Status:', navigator.onLine ? 'Online' : 'Offline');
});