const API_BASE = "/api";
const FALLBACK_IMAGE = "https://placehold.co/600x400/141414/b91c1c?text=Guitar";

let products = [];
let categoriesList = [];
let cart = [];
let currentTab = "home";
let filteredProducts = [];
let visibleCatalogCount = 6;
let searchTimer = null;

const money = (value) => `${Number(value || 0).toLocaleString("ru-RU")} ₽`;
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[ch]));
const apiImage = (value) => value || FALLBACK_IMAGE;
const categoryByName = () => Object.fromEntries(categoriesList.map(c => [c.name, c]));

async function apiJson(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
    });
    if (!response.ok) {
        let message = `Ошибка HTTP ${response.status}`;
        try {
            const data = await response.json();
            message = data.detail?.message || data.detail || message;
        } catch (_) {}
        throw new Error(typeof message === "string" ? message : "Не удалось выполнить запрос");
    }
    return response.json();
}

async function loadCategories() {
    categoriesList = await apiJson(`${API_BASE}/categories`);
    renderCategories();
    renderSidebarCategories();
}

async function loadBrands() {
    const brands = await apiJson(`${API_BASE}/brands`);
    const container = document.getElementById("brand-filters");
    container.innerHTML = brands.map(brand => `
        <label class="flex items-center space-x-2 cursor-pointer hover:text-white transition">
            <input type="checkbox" value="${escapeHtml(brand)}" onchange="applyFilters()" class="brand-checkbox rounded bg-darkbg border-bordercol text-accentred focus:ring-0">
            <span>${escapeHtml(brand)}</span>
        </label>
    `).join("");
}

async function loadHomeProducts() {
    const data = await apiJson(`${API_BASE}/products?limit=4&offset=0&sort=default`);
    products = data.items;
    renderHomeProducts();
}

async function fetchFilteredProducts({ resetCount = true } = {}) {
    const params = new URLSearchParams();
    const categorySelect = document.getElementById("filter-category")?.value || "all";
    const sort = document.getElementById("filter-sort")?.value || "default";
    const inStockOnly = document.getElementById("filter-in-stock")?.checked || false;
    const priceRange = document.querySelector("input[name='price-range']:checked")?.value || "all";
    const q = document.getElementById("global-search")?.value.trim() || "";

    const catMap = categoryByName();
    const sidebarChecked = Array.from(document.querySelectorAll(".sidebar-cat-checkbox:checked"))
        .map(cb => cb.value)
        .filter(v => v !== "all");

    const categories = categorySelect !== "all"
        ? [categorySelect]
        : sidebarChecked.length ? sidebarChecked : [];

    categories.forEach(name => {
        const cat = catMap[name];
        if (cat) params.append("category", cat.slug);
    });

    Array.from(document.querySelectorAll(".brand-checkbox:checked")).forEach(cb => params.append("brand", cb.value));
    if (inStockOnly) params.set("in_stock_only", "true");
    if (q) params.set("q", q);

    if (priceRange === "under-20k") params.set("max_price", "19999");
    if (priceRange === "20k-50k") {
        params.set("min_price", "20000");
        params.set("max_price", "50000");
    }
    if (priceRange === "over-50k") params.set("min_price", "50001");

    params.set("limit", "100");
    params.set("offset", "0");
    params.set("sort", sort);

    const data = await apiJson(`${API_BASE}/products?${params.toString()}`);
    filteredProducts = data.items;
    products = data.items;
    if (resetCount) visibleCatalogCount = 6;
    renderCatalogProducts();
}

function renderCategories() {
    const container = document.getElementById("categories-grid");
    if (!container) return;
    container.innerHTML = categoriesList.map(cat => `
        <div onclick="switchTab('catalog', '${escapeHtml(cat.name)}')" class="group bg-darkbg hover:bg-cardhover border border-bordercol hover:border-accentred rounded p-3 cursor-pointer transition flex flex-col justify-between h-28 relative overflow-hidden shadow-md">
            <div class="absolute inset-0 opacity-25 group-hover:opacity-40 transition">
                <img src="${escapeHtml(apiImage(cat.image))}" alt="${escapeHtml(cat.name)}" class="w-full h-full object-cover" onerror="this.src='${FALLBACK_IMAGE}'">
            </div>
            <div class="relative z-10 flex justify-between items-start">
                <i class="fa-solid ${escapeHtml(cat.icon)} text-accentred text-sm"></i>
                <span class="text-[10px] text-gray-400 group-hover:text-accentred transition">→</span>
            </div>
            <div class="relative z-10">
                <h3 class="font-heading font-bold text-xs text-white uppercase tracking-tight group-hover:text-red-400 transition">${escapeHtml(cat.name)}</h3>
            </div>
        </div>
    `).join("");
}

function renderSidebarCategories() {
    const container = document.getElementById("sidebar-category-filters");
    if (!container) return;
    container.innerHTML = `
        <label class="flex items-center space-x-2 cursor-pointer hover:text-white transition">
            <input type="checkbox" value="all" checked onchange="handleSidebarCategoryChange(this)" class="sidebar-cat-checkbox rounded bg-darkbg border-bordercol text-accentred focus:ring-0">
            <span>Все категории</span>
        </label>
    ` + categoriesList.map(c => `
        <label class="flex items-center space-x-2 cursor-pointer hover:text-white transition">
            <input type="checkbox" value="${escapeHtml(c.name)}" onchange="handleSidebarCategoryChange(this)" class="sidebar-cat-checkbox rounded bg-darkbg border-bordercol text-accentred focus:ring-0">
            <span>${escapeHtml(c.name)}</span>
        </label>
    `).join("");
}

function handleSidebarCategoryChange(checkbox) {
    const all = document.querySelector(".sidebar-cat-checkbox[value='all']");
    if (checkbox.value === "all") {
        if (checkbox.checked) {
            document.querySelectorAll(".sidebar-cat-checkbox:not([value='all'])").forEach(cb => cb.checked = false);
            document.getElementById("filter-category").value = "all";
        }
    } else {
        if (all) all.checked = false;
        const checked = Array.from(document.querySelectorAll(".sidebar-cat-checkbox:checked"));
        document.getElementById("filter-category").value = checked.length === 1 ? checked[0].value : "all";
        if (checked.length === 0 && all) all.checked = true;
    }
    applyFilters();
}

function switchTab(tabId, categoryParam = null) {
    document.querySelectorAll(".view-section").forEach(el => el.classList.add("hidden"));

    if (tabId === "home") {
        document.getElementById("view-home")?.classList.remove("hidden");
        currentTab = "home";
    } else if (tabId === "catalog") {
        document.getElementById("view-catalog")?.classList.remove("hidden");
        currentTab = "catalog";
        if (categoryParam) {
            document.getElementById("filter-category").value = categoryParam;
            document.querySelectorAll(".sidebar-cat-checkbox").forEach(cb => cb.checked = cb.value === categoryParam);
        }
        applyFilters();
    } else if (["about", "contacts", "product"].includes(tabId)) {
        document.getElementById(`view-${tabId}`)?.classList.remove("hidden");
        currentTab = tabId;
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function productCardTemplate(p) {
    const category = p.category?.name || "Категория";
    return `
        <div class="bg-cardbg hover:bg-cardhover border border-bordercol rounded overflow-hidden flex flex-col justify-between transition group">
            <div class="relative h-48 bg-darkbg overflow-hidden cursor-pointer" onclick="openProductDetail(${p.id})">
                <img src="${escapeHtml(apiImage(p.image))}" alt="${escapeHtml(p.name)}" class="w-full h-full object-cover group-hover:scale-105 transition duration-300 filter brightness-95" onerror="this.src='${FALLBACK_IMAGE}'">
                <span class="absolute top-2 left-2 text-[10px] font-semibold px-2 py-0.5 rounded ${p.in_stock ? "bg-green-900/80 text-green-300 border border-green-700/50" : "bg-red-900/80 text-red-300 border border-red-700/50"}">
                    ${p.in_stock ? "В наличии" : "Под заказ"}
                </span>
            </div>
            <div class="p-4 flex flex-col justify-between flex-grow">
                <div>
                    <span class="text-[10px] text-accentred uppercase tracking-widest font-semibold">${escapeHtml(category)}</span>
                    <h3 onclick="openProductDetail(${p.id})" class="font-heading font-bold text-sm text-white mt-1 hover:text-accentred cursor-pointer transition line-clamp-1">${escapeHtml(p.name)}</h3>
                    <p class="text-gray-400 text-xs mt-1.5 line-clamp-2 font-light">${escapeHtml(p.description)}</p>
                </div>
                <div class="mt-4 pt-3 border-t border-bordercol flex items-center justify-between">
                    <span class="font-heading font-bold text-sm text-white">${money(p.price)}</span>
                    <button onclick="addToCart(${p.id})" class="bg-cardhover hover:bg-accentred border border-bordercol hover:border-accentred text-gray-200 hover:text-white text-xs font-semibold px-3 py-1.5 rounded transition">В корзину</button>
                </div>
            </div>
        </div>
    `;
}

function renderHomeProducts() {
    const container = document.getElementById("home-products-grid");
    if (!container) return;
    container.innerHTML = products.slice(0, 4).map(productCardTemplate).join("");
}

function renderCatalogProducts() {
    const container = document.getElementById("catalog-products-grid");
    if (!container) return;
    const items = filteredProducts.slice(0, visibleCatalogCount);
    if (!items.length) {
        container.innerHTML = `<div class="col-span-full py-12 text-center text-gray-400 text-xs">По вашему запросу ничего не найдено. Попробуйте изменить фильтры.</div>`;
        document.getElementById("load-more-btn").style.display = "none";
        return;
    }
    container.innerHTML = items.map(productCardTemplate).join("");
    const btn = document.getElementById("load-more-btn");
    btn.style.display = visibleCatalogCount >= filteredProducts.length ? "none" : "inline-block";
}

async function applyFilters() {
    try {
        await fetchFilteredProducts({ resetCount: true });
    } catch (error) {
        showNotification(error.message || "Не удалось загрузить каталог", true);
    }
}

async function loadMoreProducts() {
    visibleCatalogCount += 4;
    renderCatalogProducts();
}

function resetFilters() {
    document.getElementById("filter-category").value = "all";
    document.getElementById("filter-sort").value = "default";
    document.getElementById("filter-in-stock").checked = false;
    document.querySelectorAll(".brand-checkbox").forEach(cb => cb.checked = false);
    document.querySelectorAll(".sidebar-cat-checkbox").forEach(cb => cb.checked = cb.value === "all");
    const allPrice = document.querySelector("input[name='price-range'][value='all']");
    if (allPrice) allPrice.checked = true;
    document.getElementById("global-search").value = "";
    applyFilters();
}

function handleSearchInput(query) {
    clearTimeout(searchTimer);
    if (currentTab !== "catalog") switchTab("catalog");
    searchTimer = setTimeout(() => applyFilters(), 250);
}

async function openProductDetail(id) {
    try {
        const p = products.find(item => item.id === id) || await apiJson(`${API_BASE}/products/${id}`);
        if (!p) return;
        const container = document.getElementById("product-detail-content");
        const category = p.category?.name || "Категория";
        container.innerHTML = `
            <div class="space-y-4">
                <div class="bg-darkbg border border-bordercol rounded overflow-hidden h-80 md:h-96">
                    <img src="${escapeHtml(apiImage(p.image))}" alt="${escapeHtml(p.name)}" class="w-full h-full object-cover" onerror="this.src='${FALLBACK_IMAGE}'">
                </div>
            </div>
            <div class="space-y-6 flex flex-col justify-between">
                <div class="space-y-3">
                    <span class="text-xs text-accentred uppercase tracking-widest font-semibold">${escapeHtml(category)} / ${escapeHtml(p.brand)}</span>
                    <h1 class="font-heading font-black text-xl md:text-2xl text-white">${escapeHtml(p.name)}</h1>
                    <div class="text-xl font-heading font-bold text-accentred">${money(p.price)}</div>
                    <div class="text-xs ${p.in_stock ? "text-green-400" : "text-red-400"} font-medium">${p.in_stock ? "● В наличии на складе" : "○ Под заказ (ожидание 3–5 дней)"}</div>
                    <p class="text-gray-300 text-xs md:text-sm leading-relaxed pt-2">${escapeHtml(p.description)}</p>
                    <div class="bg-darkbg border border-bordercol p-3 rounded text-xs space-y-1">
                        <div class="font-semibold text-white uppercase tracking-wider mb-1">Характеристики:</div>
                        <div class="text-gray-400">${escapeHtml(p.specs)}</div>
                    </div>
                </div>
                <div class="pt-4 border-t border-bordercol flex items-center gap-4">
                    <button onclick="addToCart(${p.id})" class="flex-1 bg-accentred hover:bg-red-700 text-white font-semibold text-xs py-3 rounded transition uppercase tracking-wider shadow-lg shadow-red-950">Добавить в корзину</button>
                </div>
            </div>
        `;
        switchTab("product");
    } catch (error) {
        showNotification(error.message || "Не удалось открыть товар", true);
    }
}

function goBackFromDetail() {
    switchTab("catalog");
}

function toggleCart() {
    document.getElementById("cart-drawer")?.classList.toggle("hidden");
}

async function addToCart(id) {
    let product = products.find(p => p.id === id);
    if (!product) {
        try { product = await apiJson(`${API_BASE}/products/${id}`); } catch (_) { return; }
    }
    const existing = cart.find(item => item.id === id);
    if (existing) existing.qty += 1;
    else cart.push({ ...product, qty: 1 });
    updateCartUI();
    const drawer = document.getElementById("cart-drawer");
    if (drawer?.classList.contains("hidden")) drawer.classList.remove("hidden");
}

function updateCartQuantity(id, change) {
    const item = cart.find(i => i.id === id);
    if (!item) return;
    item.qty += change;
    if (item.qty <= 0) cart = cart.filter(i => i.id !== id);
    updateCartUI();
}

function removeFromCart(id) {
    cart = cart.filter(i => i.id !== id);
    updateCartUI();
}

function updateCartUI() {
    const counter = document.getElementById("cart-counter");
    const container = document.getElementById("cart-items-container");
    const totalPriceEl = document.getElementById("cart-total-price");
    if (!counter || !container || !totalPriceEl) return;

    counter.textContent = cart.reduce((sum, item) => sum + item.qty, 0);
    if (!cart.length) {
        container.innerHTML = `<div class="py-8 text-center text-gray-400 text-xs">Корзина пуста</div>`;
        totalPriceEl.textContent = "0 ₽";
        return;
    }

    let total = 0;
    container.innerHTML = cart.map(item => {
        total += item.price * item.qty;
        return `
            <div class="py-3 flex items-center justify-between gap-3">
                <div class="flex items-center space-x-3 min-w-0">
                    <img src="${escapeHtml(apiImage(item.image))}" alt="${escapeHtml(item.name)}" class="w-12 h-12 object-cover rounded bg-darkbg" onerror="this.src='${FALLBACK_IMAGE}'">
                    <div class="min-w-0"><h4 class="font-heading font-bold text-xs text-white line-clamp-1">${escapeHtml(item.name)}</h4><div class="text-[10px] text-accentred font-semibold mt-0.5">${money(item.price)}</div></div>
                </div>
                <div class="flex items-center space-x-2 shrink-0">
                    <div class="flex items-center border border-bordercol rounded bg-darkbg text-xs"><button onclick="updateCartQuantity(${item.id}, -1)" class="px-2 py-1 text-gray-400 hover:text-white">-</button><span class="px-2 text-white font-medium">${item.qty}</span><button onclick="updateCartQuantity(${item.id}, 1)" class="px-2 py-1 text-gray-400 hover:text-white">+</button></div>
                    <button onclick="removeFromCart(${item.id})" class="text-gray-500 hover:text-accentred p-1 text-xs"><i class="fa-solid fa-trash"></i></button>
                </div>
            </div>
        `;
    }).join("");
    totalPriceEl.textContent = money(total);
}

async function checkoutOrder() {
    if (!cart.length) {
        showNotification("Корзина пуста", true);
        return;
    }
    const name = document.getElementById("customer-name")?.value.trim();
    const phone = document.getElementById("customer-phone")?.value.trim();
    if (!name || name.length < 2) {
        showNotification("Укажите имя", true);
        document.getElementById("customer-name")?.focus();
        return;
    }
    if (!phone) {
        showNotification("Укажите телефон", true);
        document.getElementById("customer-phone")?.focus();
        return;
    }

    try {
        const result = await apiJson(`${API_BASE}/orders`, {
            method: "POST",
            body: JSON.stringify({
                customer_name: name,
                customer_phone: phone,
                items: cart.map(item => ({ product_id: item.id, quantity: item.qty })),
            }),
        });
        cart = [];
        updateCartUI();
        document.getElementById("customer-name").value = "";
        document.getElementById("customer-phone").value = "";
        toggleCart();
        showNotification(`Заказ №${result.id} принят. Менеджер свяжется с вами.`);
    } catch (error) {
        showNotification(error.message || "Не удалось оформить заказ", true);
    }
}

function showNotification(message, isError = false) {
    const notif = document.createElement("div");
    notif.className = `fixed bottom-5 right-5 z-50 ${isError ? "bg-red-950 border-red-700" : "bg-cardbg border-accentred"} border text-white text-xs px-4 py-3 rounded shadow-2xl flex items-center space-x-2 transition`;
    notif.innerHTML = `<i class="fa-solid ${isError ? "fa-circle-exclamation text-red-400" : "fa-circle-check text-accentred"}"></i><span>${escapeHtml(message)}</span>`;
    document.body.appendChild(notif);
    setTimeout(() => notif.remove(), 3500);
}

function toggleMobileMenu() {
    document.getElementById("mobile-menu")?.classList.toggle("hidden");
}

async function initShop() {
    try {
        await Promise.all([loadCategories(), loadBrands(), loadHomeProducts()]);
        filteredProducts = [...products];
        await fetchFilteredProducts({ resetCount: true });
        updateCartUI();
    } catch (error) {
        console.error(error);
        showNotification("Не удалось загрузить каталог. Проверьте, что сервер FastAPI запущен.", true);
    }
}

window.addEventListener("DOMContentLoaded", initShop);
