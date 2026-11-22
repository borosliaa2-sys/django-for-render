#!/usr/bin/env bash
# Render build phase: install dependencies, collect static files, migrate Neon,
# then seed the bundled catalogue only if the target database is still empty.
set -o errexit

pip install -r requirements.txt
python scripts/build_frontend_assets.py
python manage.py collectstatic --noinput
python manage.py migrate --noinput
# This command loads the bundled catalogue only when the target database has
# no Product rows. On every existing deployment it exits without writing any
# product, price, stock, title, description, or image record.
python manage.py ensure_catalog
# Product records belong to the live database, not the release ZIP. Never
# normalize or replace product image references during a routine deployment:
# an administrator's current selection must win. These two legacy repair
# commands remain available for an explicit, one-time maintenance action only.
if [ "${CATALOG_MEDIA_MAINTENANCE_ON_BUILD:-0}" = "1" ]; then
  python manage.py normalize_local_media_references
  python manage.py apply_managed_catalog_media
else
  echo "Skipping catalogue media maintenance; routine deployments never modify existing products (set CATALOG_MEDIA_MAINTENANCE_ON_BUILD=1 only for an intentional one-time repair)."
fi
# Cloudinary is a recovery backup only. It never becomes the visitor-facing
# image URL and is used server-side only when a local file has disappeared.
# A receipt-only repair deliberately avoids scanning/re-uploading the catalogue.
if [ "${CLOUDINARY_SYNC_RECEIPTS_ON_BUILD:-0}" = "1" ]; then
  python manage.py sync_bundled_media_to_cloudinary --receipts-only
else
  echo "Skipping receipt-only Cloudinary sync (set CLOUDINARY_SYNC_RECEIPTS_ON_BUILD=1 for one intentional receipt repair deploy)."
fi
# Do not scan/re-upload the whole bundled catalogue on every deployment:
# this is opt-in for a deliberate first/repair backup run only.
if [ "${CLOUDINARY_SYNC_BUNDLED_MEDIA_ON_BUILD:-0}" = "1" ]; then
  python manage.py sync_bundled_media_to_cloudinary
else
  echo "Skipping bulk Cloudinary media sync (set CLOUDINARY_SYNC_BUNDLED_MEDIA_ON_BUILD=1 for a one-time intentional sync)."
fi
# Repairs versioned category assets in an existing Neon DB and creates only
# missing starter articles; safe to run at every deploy.
python manage.py ensure_site_content
# Creates the first admin only when secure DJANGO_SUPERUSER_* variables exist.
# It is idempotent, so ordinary deploys never overwrite an admin password.
python manage.py ensure_superuser
