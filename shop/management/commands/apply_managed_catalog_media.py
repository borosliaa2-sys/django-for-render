"""Apply the deliberate AI replacement images for selected catalogue products.

Only the original bundled catalogue image (or an empty field) is replaced.  A
newer image selected by an administrator is treated as intentional and is never
overwritten by a deployment.
"""

from django.core.management.base import BaseCommand

from shop.models import Product


# slug: (repository media path, token uniquely identifying the legacy source)
MANAGED_REPLACEMENTS = {
    "نسکافه-محمود-کافی": (
        "products/catalog/ai-mahmoud-coffee.webp",
        "existing-155-product",
    ),
    "کاپوچینو": (
        "products/catalog/ai-cappuccino.webp",
        "existing-156-product",
    ),
    "نمک-دریایی": (
        "products/catalog/ai-sea-salt.webp",
        "existing-159-product",
    ),
    "حلواارده": (
        "products/catalog/ai-halva-tahini.webp",
        "existing-161-product",
    ),
    "سه-شیره-توت-خرما-انگور": (
        "products/catalog/ai-three-syrups.webp",
        "existing-162-product",
    ),
    "نبات": (
        "products/catalog/ai-rock-candy.webp",
        "existing-169-product",
    ),
    "نخودچی-توت-کشمش": (
        "products/catalog/ai-chickpea-mulberry-raisin.webp",
        "existing-171-product",
    ),
    "پر-کیوی": (
        "products/catalog/ai-kiwi-petal.webp",
        "existing-172-product",
    ),
    "میوه-خشک-چند-میوه": (
        "products/catalog/ai-mixed-dried-fruit.webp",
        "existing-176-product",
    ),
    "قارا-بسته-دو-عددی": (
        "products/catalog/ai-qara-two-pack.webp",
        "existing-178-product",
    ),
}


class Command(BaseCommand):
    help = (
        "Apply managed AI catalogue images without overwriting unrelated "
        "administrator-selected images."
    )

    def handle(self, *args, **options):
        changed = unchanged = protected = missing = 0
        for slug, (replacement, legacy_token) in MANAGED_REPLACEMENTS.items():
            try:
                product = Product.objects.get(slug=slug)
            except Product.DoesNotExist:
                missing += 1
                self.stderr.write(f"Product not found: {slug}")
                continue

            current = str(product.image_file.name or "")
            if current == replacement:
                unchanged += 1
                continue

            # Names returned by django-cloudinary-storage include its configured
            # prefix and may append a collision suffix. The legacy token remains
            # stable, so this safely upgrades the known former catalogue image.
            if not current or legacy_token in current:
                product.image_file.name = replacement
                product.save(update_fields=["image_file"])
                changed += 1
                self.stdout.write(f"Updated {product.name}")
            else:
                protected += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Kept admin-selected image for {product.name}: {current}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Managed catalogue media complete: "
                f"updated={changed}, already-current={unchanged}, "
                f"admin-protected={protected}, missing={missing}."
            )
        )
