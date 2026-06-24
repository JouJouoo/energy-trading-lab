#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import signal
import platform

def find_python():
    candidates = ['python3', 'python', 'py']
    for candidate in candidates:
        try:
            result = subprocess.run([candidate, '--version'], capture_output=True)
            if result.returncode == 0:
                return candidate
        except FileNotFoundError:
            continue
    return None

def main():
    python = find_python()
    if not python:
        print("Error: Python not found", file=sys.stderr)
        sys.exit(1)
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.abspath('.')
    
    process = subprocess.Popen(
        [python, '-m', 'p2plab.cli', 'serve', '--port', '8765'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    def signal_handler(signum, frame):
        process.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    for _ in range(10):
        time.sleep(1)
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"Backend failed to start:", file=sys.stderr)
            print(stdout, file=sys.stderr)
            print(stderr, file=sys.stderr)
            sys.exit(1)
    
    print("Backend started successfully")
    process.wait()

if __name__ == '__main__':
    main()
