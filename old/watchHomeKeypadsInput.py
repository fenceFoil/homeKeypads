import subprocess

import psycopg2

while True:
    inLine = input("watchHomeKeypads.py running. Press Ctrl+C to exit.")
    subprocess.Popen(["aplay", "homeKeypads/sounds/key.wav"])