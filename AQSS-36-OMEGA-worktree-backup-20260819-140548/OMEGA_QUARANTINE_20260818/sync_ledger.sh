#!/bin/sh
git add .
git commit -m "Manual Sync: $(date)"
git push origin main
