#!/usr/bin/env python3
import os
import sys
import subprocess

# Get PORT from environment, default to 8000
port = os.environ.get('PORT', '8000')

# Run uvicorn with the port
cmd = [
    sys.executable, '-m', 'uvicorn',
    'app.main:app',
    '--host', '0.0.0.0',
    '--port', str(port)
]

print(f"Starting server on port {port}...")
subprocess.run(cmd)
