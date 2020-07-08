import curses
import os
import subprocess

PROMPT = "watchHomeKeypads.py running. Press Ctrl+C to exit."

def main(win):
	win.nodelay(True)
	key=""
	win.clrtoeol()
	win.addstr(PROMPT)
	while 1:
		try:
			key = win.getkey()
			win.clrtoeol()
			win.addstr(PROMPT)
			win.addstr(str(key))
			if key == os.linesep:
				break
			else:
				subprocess.run(["aplay", "homeKeypads/sounds/key.wav"])
		except Exception as e:
			# No input
			pass

curses.wrapper(main)
