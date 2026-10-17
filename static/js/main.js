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
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 10000;
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
                
                // به‌روزرسانی تعداد سبد در هدر
                const cartLink = document.querySelector('.nav-cart');
                if (cartLink) {
                    let badge = cartLink.querySelector('span');
                    if (!badge) {
                        badge = document.createElement('span');
                        cartLink.appendChild(badge);
                    }
                    badge.textContent = data.cart_count || 0;
                    window.addToCartAnim();
                }

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
