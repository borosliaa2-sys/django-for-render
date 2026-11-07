#!/usr/bin/env bash
# Render build phase: install dependencies, collect static files, migrate Neon,
# then seed the bundled catalogue only if the target database is still empty.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py ensure_catalog
# Creates the first admin only when secure DJANGO_SUPERUSER_* variables exist.
# It is idempotent, so ordinary deploys never overwrite an admin password.
python manage.py ensure_superuser
