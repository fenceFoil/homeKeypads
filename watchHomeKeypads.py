import subprocess

while True:
    inLine = input("watchHomeKeypads.py running. Press Ctrl+C to exit.")
    subprocess.run(["aplay", "homeKeypads/sounds/key.wav"])