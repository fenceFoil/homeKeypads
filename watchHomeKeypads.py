import copy
from datetime import datetime
from gotifyLoggingHandler import GotifyHandler
import keyboard
import logging
from logging import debug, info, warning, error, critical, exception
import psycopg2
import time
import os
import subprocess

# ---- LOGGER SETUP ----

logFormat = "[%(levelname)s] %(asctime)s: %(message)s"
logFormatter = logging.Formatter(logFormat)

# Log to a file and to the error stream
logging.basicConfig(filename='homeKeypadLog.txt', level=logging.DEBUG, format=logFormat)
streamHandler = logging.StreamHandler()
streamHandler.setFormatter(logFormatter)
streamHandler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(streamHandler)

gotifyHandler = GotifyHandler(os.environ['GOTIFY_ADDRESS'], os.environ['GOTIFY_APIKEY'], os.environ['GOTIFY_PRIORITY'])
gotifyHandler.setLevel(logging.WARNING)
gotifyHandler.setFormatter(logging.Formatter("[%(levelname)s]: %(message)s"))
logging.getLogger().addHandler(gotifyHandler)

# Test gotify error logging
if not os.path.isfile('.gotifyWasTestedForHomeKeypads'):
    warning("New gotify logger set up. This is a test message.")
    open('.gotifyWasTestedForHomeKeypads', 'a').close()

info ("New instance started")

# ---- END LOGGER SETUP ----

def play_sound(soundName, blocking=False):
    if blocking:
        subprocess.Popen(["aplay", "homeKeypads/sounds/{}.wav".format(soundName)]).wait()
    else:
        subprocess.Popen(["aplay", "homeKeypads/sounds/{}.wav".format(soundName)])

def sound_player(soundName):
    def player():
        play_sound(soundName)
    return player

def use_pg_cursor_to (cursorFunc):
    connection = None
    try:
        connection = psycopg2.connect(user = os.environ['KEYPADS_PG_USERNAME'],
                                    password = os.environ['KEYPADS_PG_PASSWORD'],
                                    host = os.environ['KEYPADS_PG_HOSTNAME'],
                                    port = 5432,
                                    database = os.environ["KEYPADS_PG_DB_NAME"])
        cursor = connection.cursor()
        #cursor.execute("INSERT INTO debug_temp (message_time, log_entry) VALUES (%s,%s)", (datetime.now(), msg))
        cursorFunc(cursor)
        connection.commit()
    except (Exception, psycopg2.Error) as ex:
        exception ("Error while connecting to PostgreSQL")
        play_sound("error")
    finally:
        #closing database connection.
        if(connection):
            cursor.close()
            connection.close()
            debug("PostgreSQL connection is closed")

def insert_weight (weight):
    def insert_values(cursor):
        info ("Inserting weight: {}".format(weight))
        cursor.execute("INSERT INTO weight (weight_time, weight_lbs) VALUES (%s,%s)", (datetime.now(), weight))
    use_pg_cursor_to(insert_values)

def insert_sleep (sleepHrs):
    def insert_values(cursor):
        info ("Inserting sleep: {}".format(sleepHrs))
        cursor.execute("INSERT INTO sleep (sleep_entering_date, first_sleep) VALUES (%s,%s)", (datetime.now(), sleepHrs))
    use_pg_cursor_to(insert_values)

#
# The keypad entry system is a state machine. 
# Inputs are scancodes, mapped to functions.
# States always timeout after a while.
# Unknown scancodes make mad beeps.
# 

last_scancode = 0
curr_state = None
MAIN_STATE = {} # Avoid catch-22 as sub-states note they want to return to MAIN_STATE

def move_state(newState):
    def state_mover():
        global curr_state
        curr_state = newState
    return state_mover

curr_digits = ''

def append_digit():
    DIGIT_MAP = {
        71: 7,
        72: 8,
        73: 9,
        75: 4,
        76: 5,
        77: 6,
        79: 1,
        80: 2,
        81: 3,
        82: 0,
        83: '.'
    }
    global curr_digits
    if '.' in curr_digits and last_scancode == 83:
        play_sound('nope')
    else:
        curr_digits += str(DIGIT_MAP[last_scancode])
        play_sound(str(DIGIT_MAP[last_scancode]) if DIGIT_MAP[last_scancode] != '.' else 'point')

def remove_digit():
    global curr_digits
    if len(curr_digits) > 0:
        curr_digits = curr_digits[:-1]
        play_sound('backspace')
    else:
        play_sound('nope')
    
def clear_digits():
    global curr_digits
    curr_digits = ''

def digit_submitter():
    curr_state["SUBMIT_TO"](curr_digits)
    if curr_state["SUBMIT_SOUND"]:
        play_sound(curr_state["SUBMIT_SOUND"], blocking=True)
    for digit in curr_digits:
        time.sleep(1)
        play_sound(str(digit) if digit != '.' else 'point', blocking=True)

GENERIC_INPUT_NUM_STATE = {
    "SUBMIT_TO": None,
    "SUBMIT_SOUND": None,
    "INPUTS": {
        71: append_digit,
        72: append_digit,
        73: append_digit,
        75: append_digit,
        76: append_digit,
        77: append_digit,
        79: append_digit,
        80: append_digit,
        81: append_digit,
        82: append_digit,
        83: append_digit,
        14: remove_digit,
        96: [digit_submitter, clear_digits, move_state(MAIN_STATE)],
    }
}

ENTER_SLEEP_ENTRY_STATE = copy.deepcopy(GENERIC_INPUT_NUM_STATE)
ENTER_SLEEP_ENTRY_STATE["SUBMIT_TO"] = insert_sleep
ENTER_SLEEP_ENTRY_STATE["SUBMIT_SOUND"] = "savedSleep"
ENTER_WEIGHT_ENTRY_STATE = copy.deepcopy(GENERIC_INPUT_NUM_STATE)
ENTER_WEIGHT_ENTRY_STATE["SUBMIT_TO"] = insert_weight
ENTER_WEIGHT_ENTRY_STATE["SUBMIT_SOUND"] = "savedWeight"

MAIN_STATE.update({
    "INPUTS": {
        13: [sound_player('enterWeight'),move_state(ENTER_WEIGHT_ENTRY_STATE)],
        55: [sound_player('enterSleep'),move_state(ENTER_SLEEP_ENTRY_STATE)],
        96: sound_player('key')
    }
})
curr_state = MAIN_STATE

try:
    print ("Entered Home Keypad Entry state engine. If you want bash, press Ctrl+C")
    while True:
        keyEvent = keyboard.read_event()
        if keyEvent.event_type != 'down':
            continue

        last_scancode = keyEvent.scan_code
        if last_scancode in curr_state["INPUTS"]:
            if hasattr(curr_state["INPUTS"][last_scancode], "__iter__"):
                for action in curr_state["INPUTS"][last_scancode]:
                    action()
            else:
                curr_state["INPUTS"][last_scancode]()
        else:
            play_sound("nope")
except KeyboardInterrupt:
    exit(0)
except Exception as ex:
    exception("Unexpected error in keypad entry state machine")
    play_sound("error")