from django.urls import path, register_converter

from . import api
from .cart_views import cart_add, cart_clear, cart_detail, cart_remove, cart_update
from .order_views import (
    FaqView,
    card_payment_instructions,
    create_order,
    order_invoice,
    order_tracking,
    payment_result,
    payment_verify,
    torob_payment_verify,
    upload_card_receipt,
    user_orders,
    view_card_receipt,
)
from .views import (
    AboutView,
    ArticleDetailView,
    ArticleListView,
    CategoryDetailView,
    ContactView,
    HomeView,
    ProductDetailView,
    SearchView,
    SuggestedProductsView,
    TermsView,
)
from .wishlist_views import wishlist_list, wishlist_toggle

class UnicodeSlugConverter:
    regex = r"[\w\u0600-\u06FF\-]+"
    def to_python(self, value):
        return value
    def to_url(self, value):
        return value

register_converter(UnicodeSlugConverter, "uslug")

app_name = "shop"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("search/", SearchView.as_view(), name="search"),
    path("suggested/", SuggestedProductsView.as_view(), name="suggested"),
    # مقالات و وبلاگ
    path("blog/", ArticleListView.as_view(), name="article_list"),
    path("blog/<uslug:slug>/", ArticleDetailView.as_view(), name="article_detail"),
    # صفحات ثابت
    path("about/", AboutView.as_view(), name="about"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("terms/", TermsView.as_view(), name="terms"),
    path("faq/", FaqView.as_view(), name="faq"),
    # سفارش، رهگیری و پرداخت
    path("tracking/", order_tracking, name="order_tracking"),
    path("checkout/", create_order, name="checkout"),
    path("payment/verify/", payment_verify, name="payment_verify"),
    path("payment/torob/callback/", torob_payment_verify, name="torob_payment_verify"),
    path("payment/result/", payment_result, name="payment_result"),
    path("payment/card/<str:order_number>/", card_payment_instructions, name="card_payment_instructions"),
    path("payment/card/<str:order_number>/receipt/", upload_card_receipt, name="upload_card_receipt"),
    path("payment/card/<str:order_number>/receipt/view/", view_card_receipt, name="view_card_receipt"),
    path("order/invoice/<str:order_number>/", order_invoice, name="order_invoice"),
    # پروفایل کاربری و سفارشات
    path("profile/", user_orders, name="user_profile"),
    path("profile/orders/", user_orders, name="user_orders"),
    # سبد خرید
    path("cart/", cart_detail, name="cart_detail"),
    path("cart/add/<int:variant_id>/", cart_add, name="cart_add"),
    path("cart/update/<int:variant_id>/", cart_update, name="cart_update"),
    path("cart/remove/<int:variant_id>/", cart_remove, name="cart_remove"),
    path("cart/clear/", cart_clear, name="cart_clear"),
    # علاقه‌مندی
    path("wishlist/", wishlist_list, name="wishlist_list"),
    path("wishlist/toggle/<int:product_id>/", wishlist_toggle, name="wishlist_toggle"),
    # API (JSON)
    path("api/categories/", api.api_categories, name="api_categories"),
    path("api/products/", api.api_products, name="api_products"),
    path("api/product/<uslug:slug>/", api.api_product_detail, name="api_product_detail"),
    path("api/cart/", api.api_cart, name="api_cart"),
    path("api/wishlist/", api.api_wishlist, name="api_wishlist"),
    path("api/autocomplete/", api.api_autocomplete, name="api_autocomplete"),
    # دسته و محصول
    path("category/<uslug:slug>/", CategoryDetailView.as_view(), name="category"),
    path("product/<uslug:slug>/", ProductDetailView.as_view(), name="product_detail"),
]