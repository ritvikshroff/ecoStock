/* ============================================================
   ecoStock 🥬 — App Frontend
   Complete single-page app with auth, dashboard, and FEFO
   ============================================================ */

const API = {
    base: '',
    async get(path) {
        const res = await fetch(`${this.base}${path}`, {
            headers: this.getHeaders()
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Request failed');
        return res.json();
    },
    async post(path, data) {
        const res = await fetch(`${this.base}${path}`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Request failed');
        return res.json();
    },
    async patch(path, data) {
        const res = await fetch(`${this.base}${path}`, {
            method: 'PATCH',
            headers: this.getHeaders(),
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Request failed');
        return res.json();
    },
    getHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        const token = localStorage.getItem('ecostock_token');
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return headers;
    }
};

// ============================================================
// STATE
// ============================================================
let state = {
    token: localStorage.getItem('ecostock_token'),
    user: JSON.parse(localStorage.getItem('ecostock_user') || 'null'),
};

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================
function toast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), 4000);
}

// ============================================================
// AUTH
// ============================================================
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const result = await API.post('/api/v1/auth/login', { email, password });
        state.token = result.access_token;
        localStorage.setItem('ecostock_token', result.access_token);

        // Get user info
        const user = await API.get('/api/v1/auth/me');
        state.user = user;
        localStorage.setItem('ecostock_user', JSON.stringify(user));

        document.getElementById('loginModal').classList.remove('active');
        updateUI();
        toast('Welcome back, ' + user.full_name + '! 🎉', 'success');
        loadAllData();
    } catch (err) {
        toast(err.message, 'error');
    }
    return false;
}

async function handleRegister(e) {
    e.preventDefault();
    const data = {
        full_name: document.getElementById('regName').value,
        email: document.getElementById('regEmail').value,
        password: document.getElementById('regPassword').value,
        role: document.getElementById('regRole').value,
    };

    try {
        await API.post('/api/v1/auth/register', data);
        document.getElementById('registerModal').classList.remove('active');
        toast('Account created! Please sign in 🎉', 'success');
        showLogin();
    } catch (err) {
        toast(err.message, 'error');
    }
    return false;
}

function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem('ecostock_token');
    localStorage.removeItem('ecostock_user');
    updateUI();
    document.getElementById('loginModal').classList.add('active');
    toast('Logged out', 'info');
}

function showRegister() {
    document.getElementById('loginModal').classList.remove('active');
    document.getElementById('registerModal').classList.add('active');
}

function showLogin() {
    document.getElementById('registerModal').classList.remove('active');
    document.getElementById('loginModal').classList.add('active');
}

// ============================================================
// UI UPDATE
// ============================================================
function updateUI() {
    const isLoggedIn = !!state.token && !!state.user;

    document.getElementById('sidebarUserName').textContent =
        isLoggedIn ? state.user.full_name : 'Guest';
    document.getElementById('sidebarUserRole').textContent =
        isLoggedIn ? state.user.role.replace('_', ' ') : 'Not logged in';
    document.getElementById('userBadge').textContent =
        isLoggedIn ? state.user.full_name.split(' ')[0] : 'Guest';

    if (!isLoggedIn) {
        document.getElementById('loginModal').classList.add('active');
    } else {
        document.getElementById('loginModal').classList.remove('active');
    }
}

// ============================================================
// NAVIGATION
// ============================================================
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', function(e) {
        e.preventDefault();
        const page = this.dataset.page;

        // Update nav
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        this.classList.add('active');

        // Update page
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`page-${page}`).classList.add('active');

        // Update title
        const titles = {
            dashboard: '📊 Dashboard',
            inventory: '📦 Inventory',
            fefo: '🔍 FEFO Scan',
            alerts: '🔔 Alerts',
            products: '🏷️ Products',
            stores: '🏪 Stores',
        };
        document.getElementById('pageTitle').textContent = titles[page] || page;

        // Close sidebar on mobile
        document.getElementById('sidebar').classList.remove('open');

        // Load page data
        if (page === 'dashboard') loadDashboard();
        if (page === 'inventory') loadInventory();
        if (page === 'products') loadProducts();
        if (page === 'stores') loadStores();
        if (page === 'alerts') loadAlerts();
    });
});

// Hamburger toggle
document.getElementById('hamburger').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
});
document.getElementById('sidebarClose').addEventListener('click', () => {
    document.getElementById('sidebar').classList.remove('open');
});

// Logout
document.getElementById('logoutBtn').addEventListener('click', logout);

// ============================================================
// DATA LOADING
// ============================================================
async function loadAllData() {
    if (!state.token) return;
    loadDashboard();
    loadInventory();
    loadProducts();
    loadStores();
    loadAlerts();
}

// ============================================================
// DASHBOARD
// ============================================================
async function loadDashboard() {
    if (!state.token) return;
    try {
        const [batches, fefo, alerts] = await Promise.all([
            API.get('/api/v1/inventory/batches'),
            API.get('/api/v1/inventory/fefo/scan'),
            API.get('/api/v1/alerts/alerts?unresolved=true'),
        ]);

        const total = batches.length;
        const expiring = fefo.filter(b =>
            b.suggested_action === 'discount' || b.suggested_action === 'flag_for_routing'
        ).length;
        const discounted = batches.filter(b => b.status === 'discounted').length;

        document.getElementById('statBatches').textContent = total;
        document.getElementById('statExpiring').textContent = expiring;
        document.getElementById('statDiscounted').textContent = discounted;
        document.getElementById('statAlerts').textContent = alerts.length;

        // Recent alerts
        const container = document.getElementById('recentAlerts');
        if (alerts.length === 0) {
            container.innerHTML = '<p class="empty-state">✅ No pending alerts — everything looks good!</p>';
        } else {
            container.innerHTML = alerts.slice(0, 5).map(a => `
                <div class="alert-item">
                    <div class="alert-icon">${a.alert_type.includes('markdown') ? '💰' : a.alert_type.includes('food_bank') ? '🚛' : '🔔'}</div>
                    <div class="alert-content">
                        <div class="alert-title">${a.title}</div>
                        <div class="alert-message">${a.message}</div>
                        <div class="alert-time">${new Date(a.created_at).toLocaleString()}</div>
                    </div>
                </div>
            `).join('');
        }
    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

// ============================================================
// INVENTORY
// ============================================================
async function loadInventory() {
    if (!state.token) return;
    try {
        const batches = await API.get('/api/v1/inventory/batches');
        const tbody = document.getElementById('inventoryBody');

        if (batches.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">No inventory batches yet</td></tr>';
            return;
        }

        tbody.innerHTML = batches.map(b => {
            const daysLeft = Math.ceil((new Date(b.expiry_date) - new Date()) / (1000*60*60*24));
            const badgeClass = daysLeft <= 1 ? 'badge-expired' :
                              daysLeft <= 3 ? 'badge-flagged' :
                              b.status === 'discounted' ? 'badge-discounted' : 'badge-active';
            return `<tr>
                <td><strong>${b.batch_number || 'Batch #' + b.id}</strong></td>
                <td>${b.expiry_date} <span class="badge ${badgeClass}">${daysLeft}d</span></td>
                <td>${b.current_quantity}</td>
                <td>₹${b.current_price.toFixed(2)}</td>
                <td><span class="badge ${badgeClass}">${b.status}</span></td>
            </tr>`;
        }).join('');
    } catch (err) {
        document.getElementById('inventoryBody').innerHTML =
            '<tr><td colspan="5" class="loading">Error loading inventory</td></tr>';
    }
}

function refreshInventory() { loadInventory(); toast('Inventory refreshed!', 'success'); }

// ============================================================
// FEFO SCAN
// ============================================================
async function runScan() {
    if (!state.token) { toast('Please login first', 'error'); return; }
    const tbody = document.getElementById('fefoBody');
    tbody.innerHTML = '<tr><td colspan="5" class="loading">Scanning inventory...</td></tr>';
    try {
        const results = await API.get('/api/v1/inventory/fefo/scan');
        if (results.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">✅ No batches need attention</td></tr>';
            toast('All inventory is fresh! 🥬', 'success');
            return;
        }

        tbody.innerHTML = results.map(b => {
            const actionColors = {
                'ok': 'badge-active', 'sell_now': 'badge-discounted',
                'discount': 'badge-flagged', 'flag_for_routing': 'badge-expired',
                'expired': 'badge-expired'
            };
            return `<tr>
                <td><strong>${b.product_name}</strong><br><small>${b.sku}</small></td>
                <td>${b.expiry_date}</td>
                <td><strong>${b.days_until_expiry}</strong> days</td>
                <td>${b.current_quantity}</td>
                <td><span class="badge ${actionColors[b.suggested_action] || 'badge-active'}">${b.suggested_action.replace('_', ' ')}</span></td>
            </tr>`;
        }).join('');

        const needsAttention = results.filter(b =>
            ['discount', 'flag_for_routing', 'expired'].includes(b.suggested_action)
        ).length;
        toast(`Scan complete: ${needsAttention} items need attention`, needsAttention > 0 ? 'info' : 'success');
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading">Error: ' + err.message + '</td></tr>';
    }
}

// ============================================================
// FEFO ACTIONS
// ============================================================
async function runPipeline() {
    if (!state.token) { toast('Please login first', 'error'); return; }
    try {
        toast('Running FEFO pipeline... ⚙️', 'info');
        const result = await API.post('/api/v1/inventory/fefo/run-pipeline');
        toast(result.message, 'success');
        loadDashboard();
        runScan();
    } catch (err) { toast(err.message, 'error'); }
}

async function applyDiscounts() {
    if (!state.token) { toast('Please login first', 'error'); return; }
    try {
        toast('Applying discounts... 💰', 'info');
        const result = await API.post('/api/v1/inventory/fefo/apply-discounts');
        toast(result.message, 'success');
        loadDashboard();
        loadInventory();
    } catch (err) { toast(err.message, 'error'); }
}

async function flagRouting() {
    if (!state.token) { toast('Please login first', 'error'); return; }
    try {
        toast('Checking for routing needs... 🚛', 'info');
        const result = await API.post('/api/v1/inventory/fefo/flag-routing');
        toast(result.message, 'success');
        loadDashboard();
    } catch (err) { toast(err.message, 'error'); }
}

// ============================================================
// ALERTS
// ============================================================
async function loadAlerts(unresolved = false) {
    if (!state.token) return;
    try {
        const path = unresolved ? '/api/v1/alerts/alerts?unresolved=true' : '/api/v1/alerts/alerts';
        const alerts = await API.get(path);
        const container = document.getElementById('alertsList');

        if (alerts.length === 0) {
            container.innerHTML = '<p class="empty-state">✅ No alerts to show</p>';
            return;
        }

        container.innerHTML = alerts.map(a => {
            const icons = {
                'markdown_applied': '💰', 'food_bank_dispatch': '🚛',
                'rotation_needed': '🔄', 'reorder_suggested': '📋'
            };
            const priorityLabel = a.priority === 1 ? '🔴 High' : a.priority === 2 ? '🟡 Med' : '🟢 Low';
            return `<div class="alert-item">
                <div class="alert-icon">${icons[a.alert_type] || '🔔'}</div>
                <div class="alert-content">
                    <div class="alert-title">${a.title} <span style="font-size:11px;color:var(--gray-400)">${priorityLabel}</span></div>
                    <div class="alert-message">${a.message}</div>
                    <div class="alert-time">${new Date(a.created_at).toLocaleString()}</div>
                </div>
                <div class="alert-actions">
                    ${!a.is_read ? `<button class="btn-alert btn-read" onclick="markRead(${a.id})">Read</button>` : ''}
                    ${!a.is_resolved ? `<button class="btn-alert btn-resolve" onclick="resolveAlert(${a.id})">Resolve</button>` : ''}
                </div>
            </div>`;
        }).join('');
    } catch (err) {
        document.getElementById('alertsList').innerHTML =
            '<p class="empty-state">Error loading alerts</p>';
    }
}

async function markRead(id) {
    try {
        await API.patch(`/api/v1/alerts/alerts/${id}/read`);
        loadAlerts();
    } catch (err) { toast(err.message, 'error'); }
}

async function resolveAlert(id) {
    try {
        await API.patch(`/api/v1/alerts/alerts/${id}/resolve`);
        toast('Alert resolved ✅', 'success');
        loadAlerts();
        loadDashboard();
    } catch (err) { toast(err.message, 'error'); }
}

// ============================================================
// PRODUCTS
// ============================================================
async function loadProducts() {
    if (!state.token) return;
    try {
        const products = await API.get('/api/v1/inventory/products');
        const tbody = document.getElementById('productsBody');

        if (products.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">No products yet</td></tr>';
            return;
        }

        tbody.innerHTML = products.map(p => `
            <tr>
                <td><code>${p.sku}</code></td>
                <td><strong>${p.name}</strong></td>
                <td><span class="badge badge-active">${p.category}</span></td>
                <td>₹${p.base_price.toFixed(2)}</td>
                <td>${p.typical_shelf_life_days} days</td>
            </tr>
        `).join('');
    } catch (err) {
        document.getElementById('productsBody').innerHTML =
            '<tr><td colspan="5" class="loading">Error loading products</td></tr>';
    }
}

function refreshProducts() { loadProducts(); toast('Products refreshed!', 'success'); }

// ============================================================
// STORES
// ============================================================
async function loadStores() {
    if (!state.token) return;
    try {
        const stores = await API.get('/api/v1/stores/stores');
        const tbody = document.getElementById('storesBody');

        if (stores.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading">No stores yet</td></tr>';
            return;
        }

        tbody.innerHTML = stores.map(s => `
            <tr>
                <td>#${s.id}</td>
                <td><strong>${s.name}</strong></td>
                <td>${s.location || '—'}</td>
                <td><span class="badge ${s.is_active ? 'badge-active' : 'badge-expired'}">${s.is_active ? 'Active' : 'Inactive'}</span></td>
            </tr>
        `).join('');
    } catch (err) {
        document.getElementById('storesBody').innerHTML =
            '<tr><td colspan="4" class="loading">Error loading stores</td></tr>';
    }
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    updateUI();
    if (state.token) {
        loadAllData();
        runScan();
    }
});

// Auto-refresh every 30 seconds
setInterval(() => {
    if (state.token) {
        loadDashboard();
    }
}, 30000);

