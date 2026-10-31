#!/usr/bin/env bash
set -e
python -m pip install -r requirements.txt
python create_admin.py
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
