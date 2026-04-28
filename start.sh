#!/bin/bash
cd "$(dirname "$0")"
source ./myenv/bin/activate
python3.12 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload