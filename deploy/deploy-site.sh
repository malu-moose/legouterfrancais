#!/usr/bin/env bash
# Sync the site's static files (index.html, images/) to the VPS.
# Run this from your own machine (where SSH to the VPS works), from the repo root.
#
# Usage: bash deploy/deploy-site.sh [user@host]
# Default target: ubuntu@54.39.20.153

set -euo pipefail

TARGET="${1:-ubuntu@54.39.20.153}"
REMOTE_PATH="/var/www/legouterfrancais"

rsync -avz --delete \
  index.html images/ \
  "${TARGET}:${REMOTE_PATH}/"

ssh "${TARGET}" "sudo chown -R www-data:www-data ${REMOTE_PATH}"

echo "Deployed to ${TARGET}:${REMOTE_PATH}"
