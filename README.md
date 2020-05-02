# homeKeypads
You can buy wireless numpads, nail them to the wall like a picture frame, and remote control a Raspberry Pi to do things like handle logging self tracking data.

## Keypad Used

https://www.amazon.com/dp/B07W6W1PF6

Scancodes for each key:

![](Scancodes.png)

To test scancodes, restore the git tag scancodeTestingTool, and watchHomeKeypads.py (with the setup below for environment variables) will log scancodes to postgresql.

## Setup

Add to .bashrc to appear as the default app accepting keyboard input when you boot the pi:

export KEYPADS_PG_USERNAME="yourdatabaseusername"
export KEYPADS_PG_PASSWORD="password you chose for that user"
export KEYPADS_PG_HOSTNAME="your database's address"
export KEYPADS_PG_DB_NAME="selftracking"
export GOTIFY_ADDRESS=""
export GOTIFY_APIKEY=""
export GOTIFY_PRIORITY="8"
sudo -E python3 /home/pi/homeKeypads/watchHomeKeypads.py

## TODO

* Figure out licensing for res sounds from corsica

## Icon Credit

Keypad by Scott Lewis from the Noun Project