/* ============================================================
   PRICEPOINT ADMIN · MASTER JAVASCRIPT
   Version: 2.0 · Clean · Professional · Offline Ready
   ============================================================ */

// ============================================================
// DOM READY
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    console.log('🚀 PricePoint Admin v2.0 loaded');

    // Initialize
    initSidebar();
    initNavigation();
    initTimeUpdater();
    initCharts();
    initToast();
    initModals();

    // Show dashboard by default
    showSection('dashboard');

    // Load data
    setTimeout(function() {
        loadDashboardCharts();
    }, 300);

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
});
// ============================================================
// SIDEBAR TOGGLE - GUARANTEED TO WORK
// ============================================================
function toggleSidebar() {
    console.log('🔘 ToggleSidebar called!');
    var sidebar = document.getElementById('sidebar');
    var backdrop = document.getElementById('backdrop');
    
    if (!sidebar) {
        console.error('❌ Sidebar not found!');
        return;
    }
    
    sidebar.classList.toggle('open');
    if (backdrop) {
        backdrop.classList.toggle('active');
    }
    
    console.log('📱 Sidebar open:', sidebar.classList.contains('open'));
}

// Make sure toggle is available globally
window.toggleSidebar = toggleSidebar;

// Also listen for clicks on any element with class 'sidebar-toggle'
document.addEventListener('DOMContentLoaded', function() {
    var toggleBtns = document.querySelectorAll('.sidebar-toggle');
    toggleBtns.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            toggleSidebar();
        });
    });
    
    console.log('✅ Sidebar toggle ready! Found ' + toggleBtns.length + ' toggle buttons');
});

// ============================================================
// SIDEBAR - FIXED
// ============================================================
function initSidebar() {
    var sidebar = document.getElementById('sidebar');
    var backdrop = document.getElementById('backdrop');
    var toggleBtn = document.querySelector('.sidebar-toggle');
    
    console.log('🔧 Initializing sidebar...');
    
    // If no sidebar found, exit
    if (!sidebar) {
        console.warn('⚠️ Sidebar not found');
        return;
    }
    
    // Remove all existing click listeners by cloning
    if (toggleBtn) {
        var newBtn = toggleBtn.cloneNode(true);
        toggleBtn.parentNode.replaceChild(newBtn, toggleBtn);
        toggleBtn = newBtn;
        
        // Add click listener
        toggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('🔘 Hamburger clicked!');
            sidebar.classList.toggle('open');
            if (backdrop) {
                backdrop.classList.toggle('active');
            }
            console.log('📱 Sidebar open:', sidebar.classList.contains('open'));
        });
    } else {
        console.warn('⚠️ Toggle button not found!');
        // Try to find it by any means
        var btn = document.querySelector('[onclick*="toggleSidebar"]');
        if (btn) {
            console.log('✅ Found toggle button with inline onclick');
        }
    }
    
    // Backdrop click to close
    if (backdrop) {
        backdrop.addEventListener('click', function() {
            sidebar.classList.remove('open');
            backdrop.classList.remove('active');
        });
    }
    
    // Close sidebar on nav item click (mobile)
    document.querySelectorAll('.sidebar .nav-item').forEach(function(item) {
        item.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('open');
                if (backdrop) backdrop.classList.remove('active');
            }
        });
    });
    
    // Close sidebar on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            sidebar.classList.remove('open');
            if (backdrop) backdrop.classList.remove('active');
        }
    });
    
    console.log('✅ Sidebar initialized');
}

// ============================================================
// GLOBAL TOGGLE FUNCTION (Backup)
// ============================================================
window.toggleSidebar = function() {
    var sidebar = document.getElementById('sidebar');
    var backdrop = document.getElementById('backdrop');
    if (sidebar) {
        sidebar.classList.toggle('open');
        if (backdrop) {
            backdrop.classList.toggle('active');
        }
    }
};

// ============================================================
// NAVIGATION
// ============================================================
function initNavigation() {
    var navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(function(item) {
        item.addEventListener('click', function(e) {
            var href = this.getAttribute('href');
            if (href && href.startsWith('#')) {
                e.preventDefault();
                var section = href.replace('#', '');
                showSection(section);
            }
        });
    });
}

function showSection(section) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(function(el) {
        el.classList.add('hidden');
    });

    // Show target section
    var target = document.getElementById(section + '-section');
    if (target) {
        target.classList.remove('hidden');
    }

    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(function(el) {
        el.classList.remove('active');
    });
    var activeItem = document.querySelector('.nav-item[href="#' + section + '"]');
    if (activeItem) {
        activeItem.classList.add('active');
    }

    // Update page title
    var titles = {
        'dashboard': 'Dashboard',
        'analytics': 'Analytics',
        'products': 'Products',
        'add-product': 'Add Product',
        'orders': 'Orders',
        'customers': 'Customers',
        'pos': 'Point of Sale'
    };
    var titleEl = document.getElementById('pageTitle');
    if (titleEl && titles[section]) {
        titleEl.textContent = titles[section];
    }

    // Load section-specific data
    if (section === 'dashboard') {
        loadDashboardCharts();
    }
}

// ============================================================
// TIME UPDATER
// ============================================================
function initTimeUpdater() {
    function updateTime() {
        var timeEl = document.getElementById('liveTime');
        if (timeEl) {
            timeEl.textContent = new Date().toLocaleTimeString('en-KE', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
    }
    updateTime();
    setInterval(updateTime, 10000);
}

// ============================================================
// TOAST
// ============================================================
function initToast() {
    // Toast is ready
}

function showToast(message, type) {
    type = type || 'success';
    var toast = document.getElementById('toast');
    if (!toast) return;

    var icon = toast.querySelector('.toast-icon');
    var msgEl = toast.querySelector('.toast-message');

    if (icon) {
        icon.className = 'toast-icon ' + type;
        var icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        icon.className = 'toast-icon ' + type + ' ' + (icons[type] || icons.success);
    }

    if (msgEl) {
        msgEl.textContent = message;
    }

    toast.classList.remove('hidden');
    clearTimeout(window.toastTimeout);
    window.toastTimeout = setTimeout(function() {
        toast.classList.add('hidden');
    }, 3500);
}

// ============================================================
// MODALS
// ============================================================
function initModals() {
    // Close modals when clicking overlay
    document.querySelectorAll('.modal-overlay').forEach(function(modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.add('hidden');
            }
        });
    });
}

function closeAllModals() {
    document.querySelectorAll('.modal-overlay').forEach(function(modal) {
        modal.classList.add('hidden');
    });
}

function openModal(id) {
    var modal = document.getElementById(id);
    if (modal) modal.classList.remove('hidden');
}

function closeModal(id) {
    var modal = document.getElementById(id);
    if (modal) modal.classList.add('hidden');
}

// ============================================================
// FORMAT NUMBER
// ============================================================
function formatNumber(n) {
    if (n === undefined || n === null || isNaN(n)) return '0';
    return Number(n).toLocaleString('en-KE');
}

function formatCurrency(amount) {
    return 'KSh ' + formatNumber(amount);
}

// ============================================================
// CHARTS
// ============================================================
var revenueChart = null;
var categoryChart = null;

function initCharts() {
    var ctx1 = document.getElementById('revenueChart');
    if (ctx1) {
        revenueChart = new Chart(ctx1, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Revenue (KES)',
                    data: [0, 0, 0, 0, 0, 0],
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.06)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#2563eb',
                    pointRadius: 3,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(v) { return 'KSh ' + v.toLocaleString(); },
                            font: { size: 10 }
                        },
                        grid: { color: 'rgba(0,0,0,0.04)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    var ctx2 = document.getElementById('categoryChart');
    if (ctx2) {
        categoryChart = new Chart(ctx2, {
            type: 'doughnut',
            data: {
                labels: ['Phones', 'Laptops', 'Accessories', 'Wearables', 'Other'],
                datasets: [{
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: ['#2563eb', '#7c3aed', '#f59e0b', '#10b981', '#94a3b8']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            padding: 8,
                            font: { size: 10 }
                        }
                    }
                },
                cutout: '70%'
            }
        });
    }
}

function updateCharts(data) {
    if (revenueChart) {
        var md = data.monthly_data || {};
        var months = Object.keys(md).sort();
        var labels = months.length ? months : ['No data'];
        var values = months.length ? months.map(function(m) {
            return Number(md[m].revenue || 0);
        }) : [0];

        revenueChart.data.labels = labels;
        revenueChart.data.datasets[0].data = values;
        revenueChart.update();
    }

    if (categoryChart) {
        var cd = data.category_sales || {};
        var labels = Object.keys(cd);
        var values = labels.map(function(l) {
            return Number(cd[l].revenue || 0);
        });

        if (labels.length === 0) {
            categoryChart.data.labels = ['No sales'];
            categoryChart.data.datasets[0].data = [1];
            categoryChart.data.datasets[0].backgroundColor = ['#e2e8f0'];
        } else {
            categoryChart.data.labels = labels;
            categoryChart.data.datasets[0].data = values;
            categoryChart.data.datasets[0].backgroundColor = [
                '#2563eb', '#7c3aed', '#f59e0b', '#10b981', '#14b8a6', '#ef4444', '#8b5cf6'
            ].slice(0, labels.length);
        }
        categoryChart.update();
    }
}

function loadDashboardCharts() {
    fetch('/admin/api/analytics')
        .then(function(r) { return r.json(); })
        .then(function(data) { updateCharts(data); })
        .catch(function() {});
}

// ============================================================
// ANALYTICS
// ============================================================
function loadAnalytics() {
    var mt = document.getElementById('monthlyTable');
    var pt = document.getElementById('productTable');

    if (mt) {
        mt.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-gray-400">' +
            '<i class="fas fa-spinner fa-spin mr-2"></i>Loading...</td></tr>';
    }
    if (pt) {
        pt.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-gray-400">' +
            '<i class="fas fa-spinner fa-spin mr-2"></i>Loading...</td></tr>';
    }

    fetch('/admin/api/analytics')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) return;

            // Update summary stats
            var el = document.getElementById('totalRevenue');
            if (el) el.textContent = formatCurrency(data.total_revenue);

            var cost = document.getElementById('totalCost');
            if (cost) cost.textContent = formatCurrency(data.total_cost);

            var profit = document.getElementById('totalProfit');
            if (profit) profit.textContent = formatCurrency(data.total_profit);

            var orders = document.getElementById('totalOrders');
            if (orders) orders.textContent = data.total_orders;

            var rev = document.getElementById('revRevenue');
            if (rev) rev.textContent = formatCurrency(data.total_revenue);

            var prof = document.getElementById('revProfit');
            if (prof) prof.textContent = formatCurrency(data.total_profit);

            var margin = document.getElementById('profitMargin');
            if (margin) {
                var m = data.total_revenue > 0 ? ((data.total_profit / data.total_revenue) * 100) : 0;
                margin.textContent = m.toFixed(1) + '%';
            }

            updateMonthlyTable(data.monthly_data);
            updateProductTable(data.product_sales || data.all_product_sales || {});
            updateCharts(data);
        })
        .catch(function() {
            if (mt) {
                mt.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-red-400">' +
                    'Error loading data</td></tr>';
            }
        });
}

function updateMonthlyTable(md) {
    var tbody = document.getElementById('monthlyTable');
    if (!tbody) return;

    var months = Object.keys(md).sort();
    if (months.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-gray-400">No orders yet</td></tr>';
        return;
    }

    var html = '';
    for (var i = 0; i < months.length; i++) {
        var m = months[i];
        var d = md[m];
        var margin = d.revenue > 0 ? ((d.profit / d.revenue) * 100) : 0;
        var color = margin > 20 ? 'text-green-600' : margin > 10 ? 'text-yellow-600' : 'text-red-600';

        html += '<tr class="border-b border-gray-100/50 hover:bg-gray-50/50 transition-all">';
        html += '<td class="py-2.5 font-semibold text-[#0f172a]">' + m + '</td>';
        html += '<td class="py-2.5 text-right text-gray-600">' + d.orders + '</td>';
        html += '<td class="py-2.5 text-right text-gray-600">' + d.items + '</td>';
        html += '<td class="py-2.5 text-right text-green-600 font-bold">' + formatCurrency(d.revenue) + '</td>';
        html += '<td class="py-2.5 text-right text-blue-600">' + formatCurrency(d.cost) + '</td>';
        html += '<td class="py-2.5 text-right text-purple-600 font-bold">' + formatCurrency(d.profit) + '</td>';
        html += '<td class="py-2.5 text-right ' + color + ' font-bold">' + margin.toFixed(1) + '%</td>';
        html += '</tr>';
    }
    tbody.innerHTML = html;
}

function updateProductTable(ps) {
    var tbody = document.getElementById('productTable');
    if (!tbody) return;

    var products = Object.entries(ps);
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-gray-400">No sales yet</td></tr>';
        return;
    }

    var html = '';
    var limit = Math.min(products.length, 15);
    for (var i = 0; i < limit; i++) {
        var name = products[i][0];
        var d = products[i][1];
        var margin = d.revenue > 0 ? ((d.profit / d.revenue) * 100) : 0;
        var color = margin > 20 ? 'text-green-600' : margin > 10 ? 'text-yellow-600' : 'text-red-600';

        html += '<tr class="border-b border-gray-100/50 hover:bg-gray-50/50 transition-all">';
        html += '<td class="py-2.5 font-semibold text-[#0f172a] text-truncate max-w-[150px]">' + name + '</td>';
        html += '<td class="py-2.5 text-right text-gray-600">' + d.quantity + '</td>';
        html += '<td class="py-2.5 text-right text-green-600 font-bold">' + formatCurrency(d.revenue) + '</td>';
        html += '<td class="py-2.5 text-right text-blue-600">' + formatCurrency(d.cost) + '</td>';
        html += '<td class="py-2.5 text-right text-purple-600 font-bold">' + formatCurrency(d.profit) + '</td>';
        html += '<td class="py-2.5 text-right ' + color + ' font-bold">' + margin.toFixed(1) + '%</td>';
        html += '</tr>';
    }
    tbody.innerHTML = html;
}

// ============================================================
// EXPORT REPORT
// ============================================================
function exportReport() {
    showToast('📊 Generating report...', 'info');

    fetch('/admin/api/analytics')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var csv = 'Month,Revenue,Cost,Profit,Margin\n';
            var months = Object.keys(data.monthly_data || {});

            for (var i = 0; i < months.length; i++) {
                var m = months[i];
                var d = data.monthly_data[m];
                var margin = d.revenue > 0 ? ((d.profit / d.revenue) * 100).toFixed(1) : 0;
                csv += m + ',' + d.revenue + ',' + d.cost + ',' + d.profit + ',' + margin + '%\n';
            }

            var blob = new Blob([csv], { type: 'text/csv' });
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'reports_' + new Date().toISOString().slice(0, 10) + '.csv';
            a.click();
            URL.revokeObjectURL(url);

            showToast('✅ Report exported successfully!');
        })
        .catch(function() {
            showToast('❌ Error exporting report', 'error');
        });
}

// ============================================================
// PRODUCT FUNCTIONS
// ============================================================
function filterProductsTable(query) {
    var term = query.toLowerCase().trim();
    document.querySelectorAll('#productsTableBody .product-row').forEach(function(row) {
        var name = row.dataset.name?.toLowerCase() || '';
        var cat = row.dataset.category?.toLowerCase() || '';
        var id = row.dataset.id?.toLowerCase() || '';
        row.style.display = (term === '' || name.includes(term) || cat.includes(term) || id.includes(term)) ? '' : 'none';
    });
}

function saveProduct(e) {
    e.preventDefault();
    var btn = document.getElementById('saveBtn');
    if (!btn) return;

    var orig = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    btn.disabled = true;

    var data = {
        id: document.getElementById('prodId').value.trim(),
        name: document.getElementById('prodName').value.trim(),
        category: document.getElementById('prodCategory').value,
        price: parseFloat(document.getElementById('prodPrice').value) || 0,
        cost_price: parseFloat(document.getElementById('prodCost').value) || 0,
        original_price: parseFloat(document.getElementById('prodOriginal').value) || null,
        stock: parseInt(document.getElementById('prodStock').value) || 0,
        rating: parseFloat(document.getElementById('prodRating').value) || 4.5,
        badge: document.getElementById('prodBadge').value,
        image: document.getElementById('prodImage').value.trim(),
        description: document.getElementById('prodDesc').value.trim(),
        specs: document.getElementById('prodSpecs').value.split(',').map(function(s) {
            return s.trim();
        }).filter(function(s) { return s; })
    };

    fetch('/admin/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d && d.success) {
                showToast('✅ Product saved successfully!');
            } else {
                showToast('❌ Error: ' + (d.message || 'Unknown error'), 'error');
                btn.innerHTML = orig;
                btn.disabled = false;
            }
        })
        .catch(function(err) {
            showToast('❌ Error: ' + err.message, 'error');
            btn.innerHTML = orig;
            btn.disabled = false;
        });
}

function editProduct(id) {
    showToast('📦 Loading product data...', 'info');

    fetch('/api/products/' + id)
        .then(function(r) { return r.json(); })
        .then(function(p) {
            showSection('add-product');
            document.getElementById('prodId').value = p.id || '';
            document.getElementById('prodName').value = p.name || '';
            document.getElementById('prodCategory').value = p.category || '';
            document.getElementById('prodPrice').value = p.price || 0;
            document.getElementById('prodCost').value = p.cost_price || 0;
            document.getElementById('prodOriginal').value = p.original_price || '';
            document.getElementById('prodStock').value = p.stock || 0;
            document.getElementById('prodRating').value = p.rating || 4.5;
            document.getElementById('prodBadge').value = p.badge || '';
            document.getElementById('prodImage').value = p.image || '';
            document.getElementById('prodDesc').value = p.description || '';
            document.getElementById('prodSpecs').value = (p.specs || []).join(', ');
            document.getElementById('saveBtn').innerHTML = '<i class="fas fa-save"></i> Update Product';
            showToast('✏️ Editing: ' + p.name);
        })
        .catch(function(err) {
            showToast('❌ Error loading product: ' + err.message, 'error');
        });
}

function deleteProduct(id) {
    if (!confirm('⚠️ Are you sure you want to delete this product?')) return;

    fetch('/admin/products/' + id, { method: 'DELETE' })
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.success) {
                showToast('✅ Product deleted successfully!');
            } else {
                showToast('❌ Error deleting product', 'error');
            }
        })
        .catch(function(err) {
            showToast('❌ Error: ' + err.message, 'error');
        });
}

function saveEditedProduct(e) {
    e.preventDefault();
    var btn = document.getElementById('editSaveBtn');
    if (!btn) return;

    var orig = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
    btn.disabled = true;

    var data = {
        id: document.getElementById('editProdId').value,
        name: document.getElementById('editProdName').value,
        category: document.getElementById('editProdCategory').value,
        price: parseFloat(document.getElementById('editProdPrice').value),
        cost_price: parseFloat(document.getElementById('editProdCost').value) || 0,
        original_price: parseFloat(document.getElementById('editProdOriginal').value) || null,
        stock: parseInt(document.getElementById('editProdStock').value),
        rating: parseFloat(document.getElementById('editProdRating').value),
        badge: document.getElementById('editProdBadge').value,
        image: document.getElementById('editProdImage').value,
        description: document.getElementById('editProdDesc').value,
        specs: document.getElementById('editProdSpecs').value.split(',').map(function(s) {
            return s.trim();
        }).filter(function(s) { return s; })
    };

    fetch('/admin/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d && d.success) {
                showToast('✅ Product updated successfully!');
                closeModal('editProductModal');
            } else {
                showToast('❌ Error: ' + (d.message || 'Unknown error'), 'error');
                btn.innerHTML = orig;
                btn.disabled = false;
            }
        })
        .catch(function(err) {
            showToast('❌ Error: ' + err.message, 'error');
            btn.innerHTML = orig;
            btn.disabled = false;
        });
}

// ============================================================
// ORDER FUNCTIONS
// ============================================================
function updateOrderStatus(orderId, newStatus) {
    fetch('/admin/orders/' + orderId + '/status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
    })
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.success) {
                showToast('✅ Order status updated!');
            } else {
                showToast('❌ Error updating status', 'error');
            }
        })
        .catch(function(err) {
            showToast('❌ Error: ' + err.message, 'error');
        });
}

function viewOrder(orderId) {
    var modal = document.getElementById('orderModal');
    var details = document.getElementById('orderDetails');
    if (!modal || !details) return;

    details.innerHTML = '<p class="text-gray-400 text-center py-4">' +
        '<i class="fas fa-spinner fa-spin mr-2"></i>Loading...</p>';
    modal.classList.remove('hidden');

    fetch('/api/orders/' + orderId)
        .then(function(r) { return r.json(); })
        .then(function(order) {
            var badge = {
                'pending': 'badge-warning',
                'confirmed': 'badge-info',
                'shipped': 'badge-purple',
                'delivered': 'badge-success'
            } [order.status] || 'badge-warning';

            var itemsHtml = '';
            if (order.items && order.items.length > 0) {
                for (var i = 0; i < order.items.length; i++) {
                    var item = order.items[i];
                    itemsHtml += '<div class="flex justify-between items-center py-2 border-b border-gray-100/50 last:border-0">';
                    itemsHtml += '<div><span class="font-medium text-sm">' + (item.name || 'Product') +
                        '</span><span class="text-xs text-gray-400 ml-2">× ' + (item.quantity || 0) + '</span></div>';
                    itemsHtml += '<span class="font-semibold text-sm">' + formatCurrency(item.total) + '</span>';
                    itemsHtml += '</div>';
                }
            } else {
                itemsHtml = '<p class="text-gray-400 text-sm">No items found</p>';
            }

            details.innerHTML =
                '<div class="detail-row"><span class="label">Order ID</span><span class="value font-mono font-bold">' +
                (order.order_id || 'N/A') + '</span></div>' +
                '<div class="detail-row"><span class="label">Customer</span><span class="value font-semibold">' +
                (order.customer?.name || 'Customer') + '</span></div>' +
                '<div class="detail-row"><span class="label">Email</span><span class="value">' +
                (order.customer?.email || 'N/A') + '</span></div>' +
                '<div class="detail-row"><span class="label">Phone</span><span class="value">' +
                (order.customer?.phone || 'N/A') + '</span></div>' +
                '<div class="detail-row"><span class="label">Address</span><span class="value">' +
                (order.customer?.address || 'N/A') + '</span></div>' +
                '<div class="detail-row"><span class="label">Source</span><span class="value"><span class="badge badge-info">' +
                (order.source || 'web') + '</span></span></div>' +
                '<div class="detail-row"><span class="label">Status</span><span class="value"><span class="badge ' +
                badge + '">' + (order.status || 'Pending') + '</span></span></div>' +
                '<div class="detail-row"><span class="label">Date</span><span class="value">' +
                (order.created_at ? order.created_at.slice(0, 10) : 'N/A') + '</span></div>' +
                '<div class="detail-row" style="border-top:2px solid #2563eb;padding-top:12px;margin-top:4px;">' +
                '<span class="label font-bold text-[#0f172a]">Total</span><span class="value font-extrabold text-blue-600 text-lg">' +
                formatCurrency(order.total) + '</span></div>' +
                '<div style="margin-top:16px;padding-top:16px;border-top:1px solid #eef2f6;">' +
                '<h4 class="font-bold text-[#0f172a] text-sm mb-3">Order Items</h4>' + itemsHtml + '</div>';
        })
        .catch(function(err) {
            details.innerHTML = '<p class="text-red-500 text-center py-4">❌ Error loading order: ' + err.message +
                '</p>';
        });
}

// ============================================================
// CUSTOMER FUNCTIONS
// ============================================================
function toggleCustomerModal() {
    var modal = document.getElementById('customerModal');
    if (modal) modal.classList.toggle('hidden');
}

function addCustomer(e) {
    e.preventDefault();
    var name = document.getElementById('custName')?.value.trim();
    if (!name) {
        showToast('⚠️ Please enter customer name', 'warning');
        return;
    }

    var select = document.getElementById('posCustomer');
    if (select) {
        var opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        select.appendChild(opt);
        select.value = name;
    }

    document.getElementById('posCustomerEmail').value = document.getElementById('custEmail')?.value || '';
    document.getElementById('posCustomerPhone').value = document.getElementById('custPhone')?.value || '';

    closeModal('customerModal');
    showToast('✅ Customer added: ' + name);
    document.getElementById('customerForm')?.reset();
}

// ============================================================
// IMAGE UPLOAD
// ============================================================
function switchImageMethod(method) {
    var url = document.getElementById('urlMethod');
    var up = document.getElementById('uploadMethod');
    var urlTab = document.getElementById('urlTab');
    var upTab = document.getElementById('uploadTab');

    if (method === 'url') {
        url.style.display = 'flex';
        up.style.display = 'none';
        urlTab.classList.add('active');
        upTab.classList.remove('active');
    } else {
        url.style.display = 'none';
        up.style.display = 'block';
        upTab.classList.add('active');
        urlTab.classList.remove('active');
    }
}

function handleFileUpload(input) {
    var file = input.files[0];
    if (!file) return;

    var fd = new FormData();
    fd.append('image', file);

    fetch('/admin/upload-image', {
        method: 'POST',
        body: fd
    })
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.success) {
                document.getElementById('prodImage').value = d.url;
                var preview = document.getElementById('imagePreview');
                preview.src = d.url;
                preview.classList.add('visible');
                showToast('✅ Image uploaded successfully!');
            } else {
                showToast('❌ ' + d.message, 'error');
            }
        })
        .catch(function(err) {
            showToast('❌ Upload failed: ' + err.message, 'error');
        });
}

// ============================================================
// POS FUNCTIONS
// ============================================================
var posCart = [];

function addToPOSCart(element) {
    var card = element.closest ? element.closest('.product-pos-card') : element;
    if (!card) {
        showToast('❌ Product not found', 'error');
        return;
    }

    var id = card.dataset.id || '';
    var name = card.dataset.name || 'Product';
    var price = parseFloat(card.dataset.price) || 0;
    var stock = parseInt(card.dataset.stock) || 0;
    var image = card.dataset.image || '';

    if (!id || price <= 0) {
        showToast('❌ Invalid product', 'error');
        return;
    }
    if (stock <= 0) {
        showToast('⚠️ Out of stock!', 'warning');
        return;
    }

    var existing = posCart.find(function(item) { return item.id === id; });
    if (existing) {
        if (existing.quantity < stock) {
            existing.quantity++;
        } else {
            showToast('⚠️ Not enough stock!', 'warning');
            return;
        }
    } else {
        posCart.push({
            id: id,
            name: name,
            price: price,
            image: image,
            stock: stock,
            quantity: 1
        });
    }

    updatePOSUI();
    showToast('✅ Added: ' + name);
}

function updatePOSQuantity(index, delta) {
    if (posCart[index]) {
        var newQty = posCart[index].quantity + delta;
        if (newQty <= 0) {
            posCart.splice(index, 1);
        } else if (newQty <= posCart[index].stock) {
            posCart[index].quantity = newQty;
        } else {
            showToast('⚠️ Not enough stock!', 'warning');
            return;
        }
        updatePOSUI();
    }
}

function removePOSItem(index) {
    posCart.splice(index, 1);
    updatePOSUI();
    showToast('🗑️ Item removed');
}

function updatePOSUI() {
    var list = document.getElementById('posCartItemsList');
    var empty = document.getElementById('emptyCartMessage');
    var sub = document.getElementById('posSubtotal');
    var total = document.getElementById('posTotal');
    var count = document.getElementById('itemCount');
    var btn = document.getElementById('posPlaceOrderBtn');

    var subtotal = posCart.reduce(function(sum, item) {
        return sum + (Number(item.price) || 0) * (Number(item.quantity) || 0);
    }, 0);

    if (sub) sub.textContent = formatCurrency(subtotal);
    if (total) total.textContent = formatCurrency(subtotal);

    var qty = posCart.reduce(function(sum, item) {
        return sum + (Number(item.quantity) || 0);
    }, 0);
    if (count) count.textContent = qty + ' items';

    if (btn) {
        btn.disabled = posCart.length === 0;
        btn.style.opacity = posCart.length === 0 ? '0.5' : '1';
    }

    if (empty) {
        empty.style.display = posCart.length === 0 ? 'block' : 'none';
    }

    if (!list) return;
    if (posCart.length === 0) {
        list.innerHTML = '';
        return;
    }

    var html = '';
    posCart.forEach(function(item, index) {
        var p = Number(item.price) || 0;
        var q = Number(item.quantity) || 1;
        html += '<div class="pos-cart-item flex items-center gap-2 bg-gray-50 rounded-lg p-2 border border-gray-100">';
        html += '<div class="w-10 h-10 rounded-lg overflow-hidden bg-white flex-shrink-0 flex items-center justify-center">';
        if (item.image) {
            html += '<img src="' + item.image +
                '" class="w-full h-full object-contain p-1" onerror="this.style.display=\'none\'">';
        } else {
            html += '<span class="text-2xl">📱</span>';
        }
        html += '</div>';
        html += '<div class="flex-1 min-w-0"><p class="text-xs font-semibold truncate">' + item.name +
            '</p><p class="cart-item-price text-green-600 font-bold text-sm">' + formatCurrency(p) + '</p></div>';
        html += '<div class="flex items-center gap-1">';
        html += '<button onclick="updatePOSQuantity(' + index +
            ', -1)" class="w-6 h-6 rounded-full bg-gray-200 hover:bg-gray-300 text-xs font-bold">-</button>';
        html += '<span class="text-sm font-bold w-6 text-center">' + q + '</span>';
        html += '<button onclick="updatePOSQuantity(' + index +
            ', 1)" class="w-6 h-6 rounded-full bg-gray-200 hover:bg-gray-300 text-xs font-bold">+</button>';
        html += '<button onclick="removePOSItem(' + index +
            ')" class="text-red-400 hover:text-red-600 text-sm ml-1 p-1"><i class="fas fa-times"></i></button>';
        html += '</div></div>';
    });
    list.innerHTML = html;
}

function clearCart() {
    if (posCart.length > 0 && !confirm('Clear all items from current order?')) return;
    posCart = [];
    updatePOSUI();
    showToast('🔄 Cart cleared');
}

function placePOSOrder() {
    if (posCart.length === 0) {
        showToast('⚠️ Add items first!', 'warning');
        return;
    }

    var customer = document.getElementById('posCustomer')?.value || 'Walk-in Customer';
    var email = document.getElementById('posCustomerEmail')?.value || 'walkin@example.com';
    var phone = document.getElementById('posCustomerPhone')?.value || 'N/A';

    var items = posCart.map(function(item) {
        return {
            product_id: item.id,
            name: item.name,
            price: Number(item.price) || 0,
            quantity: Number(item.quantity) || 1,
            total: (Number(item.price) || 0) * (Number(item.quantity) || 1),
            type: 'product'
        };
    });

    var subtotal = posCart.reduce(function(sum, item) {
        return sum + (Number(item.price) || 0) * (Number(item.quantity) || 0);
    }, 0);

    var data = {
        customer_name: customer,
        customer_email: email,
        customer_phone: phone,
        customer_address: 'In-store purchase',
        items: items,
        subtotal: subtotal,
        shipping: 0,
        total: subtotal,
        source: 'pos'
    };

    var btn = document.getElementById('posPlaceOrderBtn');
    if (!btn) return;

    var orig = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    btn.disabled = true;

    fetch('/admin/pos/place-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
        .then(function(r) {
            if (!r.ok) throw new Error('Network error');
            return r.json();
        })
        .then(function(d) {
            if (d.success) {
                showToast('✅ Order placed successfully! #' + d.order_id);
                posCart = [];
                updatePOSUI();
            } else {
                showToast('❌ Error: ' + (d.message || 'Unknown error'), 'error');
            }
            btn.innerHTML = orig;
            btn.disabled = false;
        })
        .catch(function(err) {
            showToast('❌ Error: ' + err.message, 'error');
            btn.innerHTML = orig;
            btn.disabled = false;
        });
}

function filterPOSProducts(query) {
    var term = query.toLowerCase().trim();
    document.querySelectorAll('.product-pos-card').forEach(function(c) {
        var name = c.dataset.name?.toLowerCase() || '';
        var id = c.dataset.id?.toLowerCase() || '';
        c.style.display = (term === '' || name.includes(term) || id.includes(term)) ? '' : 'none';
    });
}