#!/usr/bin/env bash
# Render build phase: install dependencies, collect static files, migrate Neon,
# then seed the bundled catalogue only if the target database is still empty.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py ensure_catalog
python manage.py apply_managed_catalog_media
# On the first Cloudinary-enabled build, uploads bundled catalogue files whose
# database names existed locally before Cloudinary was configured. It is a
# no-op when Cloudinary is not configured and skips resources already uploaded.
python manage.py sync_bundled_media_to_cloudinary
# Repairs versioned category assets in an existing Neon DB and creates only
# missing starter articles; safe to run at every deploy.
python manage.py ensure_site_content
# Creates the first admin only when secure DJANGO_SUPERUSER_* variables exist.
# It is idempotent, so ordinary deploys never overwrite an admin password.
python manage.py ensure_superuser
