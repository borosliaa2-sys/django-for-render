"""Load the bundled production catalogue only when the target database is empty."""
from django.core.management import BaseCommand, call_command
from django.db import transaction

from shop.models import Product


class Command(BaseCommand):
    help = "Load the bundled Attarbashi catalogue fixture when no products exist."

    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write("Catalog already exists; fixture was not reloaded.")
            return

        with transaction.atomic():
            call_command("loaddata", "catalog", verbosity=options.get("verbosity", 1))

        count = Product.objects.count()
        if not count:
            raise RuntimeError("Catalog fixture finished but no products were created.")
        self.stdout.write(self.style.SUCCESS(f"Catalogue initialized with {count} products."))
