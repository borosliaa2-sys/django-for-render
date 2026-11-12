"""XML sitemap classes for every indexable storefront resource."""
from __future__ import annotations

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Article, Category, Product


class StaticPageSitemap(Sitemap):
    protocol = "https"
    priority = 0.7
    changefreq = "monthly"

    def items(self):
        return ("shop:home", "shop:suggested", "shop:article_list", "shop:about", "shop:contact", "shop:faq", "shop:terms")

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == "shop:home" else 0.7

    def changefreq(self, item):
        return "daily" if item in {"shop:home", "shop:suggested"} else "weekly"


class CategorySitemap(Sitemap):
    protocol = "https"
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return Category.objects.filter(is_active=True).order_by("id")

    def location(self, item):
        return item.get_absolute_url()


class ProductSitemap(Sitemap):
    protocol = "https"
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return Product.objects.filter(is_active=True).order_by("id")

    def lastmod(self, item):
        return item.updated_at

    def location(self, item):
        return item.get_absolute_url()


class ArticleSitemap(Sitemap):
    protocol = "https"
    priority = 0.7
    changefreq = "monthly"

    def items(self):
        return Article.objects.filter(is_published=True).order_by("id")

    def lastmod(self, item):
        return item.updated_at

    def location(self, item):
        return item.get_absolute_url()


sitemaps = {
    "pages": StaticPageSitemap,
    "categories": CategorySitemap,
    "products": ProductSitemap,
    "articles": ArticleSitemap,
}
