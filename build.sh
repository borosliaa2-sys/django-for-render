#!/usr/bin/env bash
# Render build phase: install dependencies, collect static files, migrate Neon,
# then seed the bundled catalogue only if the target database is still empty.
set -o errexit

pip install -r requirements.txt
python scripts/build_frontend_assets.py
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py ensure_catalog
# Convert legacy Cloudinary public ids back to repository-local paths whenever
# that exact bundled file is present. Browsers then stay on this site's /media/.
python manage.py normalize_local_media_references
python manage.py apply_managed_catalog_media
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
