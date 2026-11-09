/**
 * main.js — عطارباشی
 * مدیریت منوی موبایل، هدر اسکرول، تعاملات AJAX سبد خرید و علاقه‌مندی‌ها بدون رفرش صفحه
 */

// ۱. عناصر ناوبری و منو
const menuBtn = document.querySelector('#menu-btn');
const navUserWrap = document.querySelector('.nav-user-wrap');

// مدیریت باز و بسته شدن دراپ‌داون کاربر با کلیک و تاچ
if (navUserWrap) {
    const userBtn = navUserWrap.querySelector('.nav-user');
    if (userBtn) {
        userBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            navUserWrap.classList.toggle('is-open');
        });
    }
    document.addEventListener('click', function(e) {
        if (!navUserWrap.contains(e.target)) {
            navUserWrap.classList.remove('is-open');
        }
    });
}

// کنترل اسلایدر و کاروسل محصولات (Carousel Controls)
window.slideCarousel = function(carouselId, direction) {
    const slider = document.getElementById(carouselId);
    if (!slider) return;
    const card = slider.querySelector('.pro-box');
    const step = card ? (card.offsetWidth + 16) * 2 : 360;
    // در چیدمان راست‌به‌چپ (RTL)، اسکرول با جهت منفی/مثبت اعمال می‌شود
    slider.scrollBy({ left: direction * step, behavior: 'smooth' });
};

const navLinks = document.querySelectorAll('.menu a');

navLinks.forEach((link) => {
    link.addEventListener('click', function () {
        if (window.innerWidth <= 768 && menuBtn) {
            menuBtn.checked = false;
        }
    });
});

// زیرمنوی دسته‌بندی‌ها: در موبایل فقط با لمس دکمه باز می‌شود؛ در دسکتاپ
// CSS آن را با hover نمایش می‌دهد.
const categoryMenuTrigger = document.querySelector('[data-category-menu-trigger]');
const categoryMenu = document.querySelector('[data-category-menu]');
const categoryMenuItem = categoryMenuTrigger ? categoryMenuTrigger.closest('.nav-category-item') : null;
if (categoryMenuTrigger && categoryMenuItem) {
    categoryMenuTrigger.addEventListener('click', function (event) {
        if (window.innerWidth > 768) return;
        event.preventDefault();
        event.stopPropagation();
        const open = categoryMenuItem.classList.toggle('is-open');
        categoryMenuTrigger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
}

// بستن منوی موبایل با لمس هر نقطه بیرون پنل (و نه فقط ضربدر همبرگری).
const navigation = document.querySelector('.navigation');
const menuIcon = document.querySelector('.menu-icon');
document.addEventListener('click', function (event) {
    if (window.innerWidth > 768 || !menuBtn || !menuBtn.checked || !navigation) return;
    // A label activation dispatches a follow-up click on the hidden checkbox;
    // that checkbox is part of opening the drawer, not an outside click.
    if (navigation.contains(event.target) || event.target === menuBtn || (menuIcon && menuIcon.contains(event.target))) return;
    menuBtn.checked = false;
    if (categoryMenuItem) categoryMenuItem.classList.remove('is-open');
    if (categoryMenuTrigger) categoryMenuTrigger.setAttribute('aria-expanded', 'false');
});

// ۲. مدیریت اسکرول هدر
const header = document.querySelector('header');
let lastScroll = 0;
let ticking = false;

function updateHeaderOnScroll() {
    if (!header) return;
    const currentScroll = window.pageYOffset;

    if (currentScroll <= 0) {
        header.classList.remove('header-scrolled');
        header.style.transform = 'translateY(0)';
        return;
    }

    if (currentScroll > 60) {
        header.classList.add('header-scrolled');
    } else {
        header.classList.remove('header-scrolled');
    }

    if (currentScroll > lastScroll && currentScroll > 120) {
        // اسکرول به پایین — مخفی کردن هدر
        header.style.transform = 'translateY(-100%)';
    } else {
        // اسکرول به بالا — نمایش هدر
        header.style.transform = 'translateY(0)';
    }

    lastScroll = currentScroll;
}

window.addEventListener('scroll', function () {
    if (!ticking) {
        window.requestAnimationFrame(function () {
            updateHeaderOnScroll();
            ticking = false;
        });
        ticking = true;
    }
});

// ۳. تقویم شمسی هیرو
(function () {
    const el = document.getElementById('shamsi-date');
    if (!el) return;
    try {
        const d = new Date();
        const fmt = new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            weekday: 'long'
        });
        const txt = fmt.format(d);
        const span = el.querySelector('span');
        if (span) span.textContent = 'امروز؛ ' + txt;
    } catch (e) {
        const span2 = el.querySelector('span');
        if (span2) span2.textContent = 'امروز — ' + (new Date()).toLocaleDateString('fa-IR');
    }
})();

// ۴. سیستم پیام‌های پاپ‌آپ مدرن (Toast Notifications)
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            bottom: max(20px, env(safe-area-inset-bottom));
            left: 50%;
            transform: translateX(-50%);
            z-index: 2147483000;
            display: flex;
            flex-direction: column;
            gap: 8px;
            pointer-events: none;
            width: min(92%, 420px);
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const isSuccess = type === 'success';
    const isError = type === 'error';
    const isWarning = type === 'warning';

    const bg = isSuccess ? '#10b981' : (isError ? '#ef4444' : '#f59e0b');
    const icon = isSuccess ? 'ri-checkbox-circle-fill' : (isError ? 'ri-error-warning-fill' : 'ri-alert-fill');

    toast.style.cssText = `
        background: #ffffff;
        color: #2b1f15;
        border-right: 5px solid ${bg};
        border-radius: 12px;
        padding: 12px 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15), 0 2px 6px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        gap: 12px;
        font-family: inherit;
        font-size: 0.9rem;
        font-weight: 700;
        pointer-events: auto;
        animation: toastIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        box-sizing: border-box;
    `;

    toast.innerHTML = `
        <i class="${icon}" style="color:${bg}; font-size:1.35rem; flex-shrink:0;"></i>
        <span style="flex:1; line-height:1.4;">${message}</span>
        <button type="button" style="border:none; background:transparent; cursor:pointer; color:#999; font-size:1.1rem; padding:0 4px;" onclick="this.parentElement.remove()">✕</button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ۵. انیمیشن سبد خرید
window.addToCartAnim = function () {
    const cartIcon = document.querySelector('.nav-cart');
    if (!cartIcon) return;
    cartIcon.style.animation = 'none';
    void cartIcon.offsetWidth;
    cartIcon.style.animation = 'cartAdd 0.5s ease';
};

// تابع کمکی برای گرفتن توکن CSRF
function getCsrfToken() {
    const hiddenInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (hiddenInput) return hiddenInput.value;
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

function formatPersianNumber(value) {
    return Number(value || 0).toLocaleString('fa-IR');
}

function updateCartBadge(cartCount) {
    const cartLink = document.querySelector('.nav-cart');
    if (!cartLink) return;
    let badge = cartLink.querySelector('span');
    if (!badge) {
        badge = document.createElement('span');
        cartLink.appendChild(badge);
    }
    badge.textContent = cartCount || 0;
    window.addToCartAnim();
}

function cartUpdateUrlFor(form) {
    if (form.dataset.updateUrl) return form.dataset.updateUrl;
    return (form.action || '').replace('/cart/add/', '/cart/update/');
}

function showStockLimit(form, stock) {
    const message = `حداکثر موجودی انتخاب شده (${formatPersianNumber(stock)} عدد)`;
    // Shake the compact control in place, but keep the explanatory notice in
    // the fixed toast layer so it cannot be cropped by a product card.
    form.classList.remove('is-at-stock');
    void form.offsetWidth;
    form.classList.add('is-at-stock');
    window.setTimeout(() => form.classList.remove('is-at-stock'), 600);
    showToast(message, 'warning');
}

function upgradeToQuantityStepper(form, quantity, stock) {
    if (!form || !form.hasAttribute('data-cart-action-form')) return;
    const safeQty = Math.max(1, Number(quantity) || 1);
    const safeStock = Math.max(0, Number(stock) || 0);
    form.dataset.stock = safeStock;
    form.dataset.quantity = safeQty;
    form.innerHTML = `
        <div class="cart-stepper" role="group" aria-label="تعداد محصول در سبد">
            <button type="button" class="cart-stepper__button" data-cart-qty-action="increase" aria-label="افزایش تعداد">+</button>
            <output class="cart-stepper__count" data-cart-qty-count>${formatPersianNumber(safeQty)}</output>
            <button type="button" class="cart-stepper__button" data-cart-qty-action="decrease" aria-label="کاهش تعداد">−</button>
        </div>
        <span class="cart-stock-warning" role="status">حداکثر موجودی انتخاب شده</span>`;
}

function restoreAddButton(form) {
    const csrf = getCsrfToken();
    const buttonClass = form.dataset.buttonClass || 'pro-cart-btn';
    const buttonText = form.dataset.buttonText || 'افزودن به سبد';
    form.dataset.quantity = '0';
    form.innerHTML = `${csrf ? `<input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">` : ''}
        <input type="hidden" name="qty" value="1">
        <button type="submit" class="${buttonClass}"><i class="ri-shopping-bag-4-line"></i><span>${buttonText}</span></button>`;
}

function updateStepperCount(form, quantity) {
    form.dataset.quantity = quantity;
    const count = form.querySelector('[data-cart-qty-count]');
    if (count) count.textContent = formatPersianNumber(quantity);
}

// Quantity changes are server-validated as well as clamped in the UI. This
// covers a second tab, stale stock, or a manually altered request.
document.addEventListener('click', function (event) {
    const button = event.target.closest('[data-cart-qty-action]');
    if (!button) return;
    const form = button.closest('form[data-cart-action-form]');
    if (!form || button.disabled) return;
    event.preventDefault();
    event.stopPropagation();

    const current = Math.max(1, Number(form.dataset.quantity) || 1);
    const stock = Math.max(0, Number(form.dataset.stock) || 0);
    const increasing = button.dataset.cartQtyAction === 'increase';
    if (increasing && current >= stock) {
        showStockLimit(form, stock);
        return;
    }
    const targetQuantity = increasing ? current + 1 : current - 1;
    button.disabled = true;

    fetch(cartUpdateUrlFor(form), {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCsrfToken() },
        body: new URLSearchParams({ qty: String(Math.max(0, targetQuantity)), ajax: '1' })
    })
    .then(response => response.json().then(data => ({ status: response.status, data })))
    .then(({ status, data }) => {
        if (status >= 200 && status < 300 && data.success) {
            updateCartBadge(data.cart_count);
            if (data.action === 'removed' || targetQuantity <= 0) {
                restoreAddButton(form);
            } else {
                const actualQty = Number(data.item_qty) || targetQuantity;
                form.dataset.stock = Number(data.stock) || stock;
                updateStepperCount(form, actualQty);
                if (increasing && actualQty >= Number(form.dataset.stock)) showStockLimit(form, form.dataset.stock);
            }
        } else {
            showToast(data.message || 'تغییر تعداد انجام نشد.', 'error');
            if (increasing && data.stock !== undefined) showStockLimit(form, data.stock);
        }
    })
    .catch(() => showToast('خطا در برقراری ارتباط با سرور.', 'error'))
    .finally(() => { button.disabled = false; });
}, true);

// ۶. هندلر سراسری AJAX برای سبد خرید
document.addEventListener('submit', function (e) {
    const form = e.target;
    if (!form || !form.action) return;

    if (form.classList.contains('cart-add-form') || form.id === 'addToCartForm' || form.action.includes('/cart/add/')) {
        e.preventDefault();

        const submitBtn = form.querySelector('button[type="submit"]');
        const originalBtnHtml = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="ri-loader-4-line" style="animation:spin 0.8s linear infinite;"></i> <span>در حال افزودن...</span>';
        }

        const formData = new FormData(form);
        formData.append('ajax', '1');

        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => {
            return response.json().then(data => ({ status: response.status, data }));
        })
        .then(({ status, data }) => {
            if (status >= 200 && status < 300 && data.success) {
                showToast(data.message || 'به سبد خرید اضافه شد.', 'success');
                
                // به‌روزرسانی تعداد سبد در هدر و تبدیل دکمه کارت به کنترل تعداد.
                updateCartBadge(data.cart_count);
                upgradeToQuantityStepper(form, data.item_qty, data.stock);

                // اگر مودال پیش‌نمایش باز بود، ببندیم
                if (typeof closeQuickPreview === 'function') closeQuickPreview();
                if (typeof closePreview === 'function') closePreview();
            } else {
                showToast(data.message || 'خطا در افزودن به سبد خرید.', 'error');
            }
        })
        .catch(err => {
            console.error('Cart add error:', err);
            showToast('خطا در برقراری ارتباط با سرور.', 'error');
        })
        .finally(() => {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHtml;
            }
        });
    }
});

// تابع سراسری تغییر وضعیت علاقه‌مندی بدون ریلود شدن صفحه
window.toggleWishlistAjax = function(e, btn) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
        if (e.stopImmediatePropagation) e.stopImmediatePropagation();
    }
    if (!btn) return;

    const url = btn.dataset.url || btn.getAttribute('href');
    if (!url) return;

    fetch(url, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, data.is_wishlisted ? 'success' : 'warning');

            const prodId = data.product_id;
            const allMatchingBtns = document.querySelectorAll(`[data-product-id="${prodId}"].fav-btn, [data-product-id="${prodId}"].btn-heart, [data-product-id="${prodId}"].btn-wishlist-detail, [data-product-id="${prodId}"].btn-wishlist-toggle, [data-url*="/wishlist/toggle/${prodId}/"]`);

            allMatchingBtns.forEach(b => {
                const icon = b.querySelector('i');
                const textSpan = b.querySelector('span');

                if (data.is_wishlisted) {
                    b.classList.add('active');
                    if (icon) {
                        icon.className = icon.className.includes('ri-') ? 'ri-heart-3-fill' : 'fas fa-heart';
                        icon.style.color = '#e74c3c';
                    }
                    if (textSpan && b.classList.contains('btn-wishlist-detail')) {
                        textSpan.textContent = 'در علاقه‌مندی‌ها';
                    }
                } else {
                    b.classList.remove('active');
                    if (icon) {
                        icon.className = icon.className.includes('ri-') ? 'ri-heart-3-line' : 'far fa-heart';
                        icon.style.color = '';
                    }
                    if (textSpan && b.classList.contains('btn-wishlist-detail')) {
                        textSpan.textContent = 'علاقه‌مندی';
                    }
                }
            });

            // به‌روزرسانی بج هدر
            const navWish = document.querySelector('.nav-wish');
            if (navWish) {
                let badge = navWish.querySelector('span');
                const heartIcon = navWish.querySelector('i');
                if (data.wishlist_count > 0) {
                    if (!badge) {
                        badge = document.createElement('span');
                        navWish.appendChild(badge);
                    }
                    badge.textContent = data.wishlist_count;
                    if (heartIcon) heartIcon.style.color = '#e74c3c';
                } else {
                    if (badge) badge.remove();
                    if (heartIcon) heartIcon.style.color = '';
                }
            }
        }
    })
    .catch(err => {
        console.error('Wishlist toggle error:', err);
        showToast('خطا در تغییر وضعیت علاقه‌مندی.', 'error');
    });
};

// ۷. هندلر سراسری AJAX برای لیست علاقه‌مندی‌ها (Wishlist)
document.addEventListener('click', function (e) {
    const wishBtn = e.target.closest('a[href*="/wishlist/toggle/"], .fav-btn, .btn-heart, .btn-wishlist-detail, .btn-wishlist-toggle');
    if (!wishBtn) return;

    const url = wishBtn.dataset.url || wishBtn.getAttribute('href');
    if (!url || !url.includes('/wishlist/toggle/')) return;

    window.toggleWishlistAjax(e, wishBtn);
});

// استایل‌های پویا برای Toast و چرخش لودر
const animStyle = document.createElement('style');
animStyle.textContent = `
    @keyframes toastIn {
        from { opacity: 0; transform: translateY(20px) scale(0.95); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes toastOut {
        from { opacity: 1; transform: translateY(0) scale(1); }
        to { opacity: 0; transform: translateY(20px) scale(0.95); }
    }
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    @keyframes cartAdd {
        0% { transform: scale(1); }
        25% { transform: scale(0.85); }
        50% { transform: scale(1.15); }
        75% { transform: scale(0.95); }
        100% { transform: scale(1); }
    }
`;
document.head.appendChild(animStyle);
