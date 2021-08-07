import copy
from datetime import datetime
from gotifyLoggingHandler import GotifyHandler
import keyboard
import logging
from logging import debug, info, warning, error, critical, exception
import psycopg2
import time
import os
import schedule
import subprocess
import threading
import pygame
from itertools import chain
from glob import iglob

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

pygame.mixer.init()

# Build a cache of loaded sounds to cut sound effect latency on button press
SOUNDS = {}
SOUNDDIR = 'homeKeypads/sounds/'
for subdir, dirs, files in os.walk(SOUNDDIR):
    for file in chain.from_iterable(iglob(os.path.join(SOUNDDIR,p)) for p in ("*.wav")) :
            print(os.path.join(subdir, file))
            baseName = file[:-4]
            SOUNDS[baseName] = pygame.mixer.Sound(file)

def play_sound(soundName, blocking=False):
    SOUNDS[soundName].play()
    if blocking:
        while pygame.mixer.get_busy():
            time.sleep(0.1)

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
    except (Exception, psycopg2.Error):
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
        cursor.execute("INSERT INTO weight (weigh_time, weight_lbs) VALUES (%s,%s)", (datetime.now(), weight))
    use_pg_cursor_to(insert_values)

def insert_sleep (sleepHrs):
    def insert_values(cursor):
        info ("Inserting sleep: {}".format(sleepHrs))
        cursor.execute("INSERT INTO sleep (sleep_entering_date, first_sleep) VALUES (%s,%s) ON conflict (sleep_entering_date) do update set first_sleep = excluded.first_sleep", (datetime.now(), sleepHrs))
    use_pg_cursor_to(insert_values)

def insert_sleep_time (sleepTime):
    def insert_values(cursor):
        info ("Inserting sleep time: {}".format(sleepTime))
        cursor.execute("INSERT INTO sleep (sleep_entering_date, wake_time) VALUES (%s,%s) ON conflict (sleep_entering_date) do update set wake_time = excluded.wake_time", (datetime.now(), sleepTime))
    use_pg_cursor_to(insert_values)

#
# The keypad entry system is a state machine. 
# Inputs are scancodes, mapped to functions.
# TODO States always timeout after a while.
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
    speak_digits()

def speak_digits():
    for digit in curr_digits:
        time.sleep(0.3)
        play_sound(str(digit) if digit != '.' else 'point', blocking=True)

GENERIC_INPUT_NUM_STATE = {
    "SUBMIT_TO": None,
    "SUBMIT_SOUND": None,
    "INPUTS": {
        1: [clear_digits, move_state(MAIN_STATE)],
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
        13: speak_digits,
        96: [digit_submitter, clear_digits, move_state(MAIN_STATE)],
    }
}

ENTER_SLEEP_TIME_ENTRY_STATE = copy.deepcopy(GENERIC_INPUT_NUM_STATE)
ENTER_SLEEP_TIME_ENTRY_STATE["SUBMIT_TO"] = insert_sleep_time
ENTER_SLEEP_TIME_ENTRY_STATE["SUBMIT_SOUND"] = "savedSleepTime"
ENTER_SLEEP_ENTRY_STATE = copy.deepcopy(GENERIC_INPUT_NUM_STATE)
ENTER_SLEEP_ENTRY_STATE["SUBMIT_TO"] = insert_sleep
ENTER_SLEEP_ENTRY_STATE["SUBMIT_SOUND"] = "savedSleep"
ENTER_SLEEP_ENTRY_STATE["INPUTS"][55] = [sound_player('enterSleepTime'),move_state(ENTER_SLEEP_TIME_ENTRY_STATE)]
ENTER_WEIGHT_ENTRY_STATE = copy.deepcopy(GENERIC_INPUT_NUM_STATE)
ENTER_WEIGHT_ENTRY_STATE["SUBMIT_TO"] = insert_weight
ENTER_WEIGHT_ENTRY_STATE["SUBMIT_SOUND"] = "savedWeight"

def play_screen_timer3():
    play_sound('getBackToWork')
    return schedule.CancelJob

def play_screen_timer2():
    play_sound('lookAway')
    schedule.every(25).seconds.do(play_screen_timer3)
    return schedule.CancelJob

def play_screen_timer():
    """Method called by scheduler to make the screen timer sounds"""
    play_sound('Blip_Select9')
    schedule.every(10).seconds.do(play_screen_timer2)

def test_screen_timer():
    play_screen_timer()
    return schedule.CancelJob

screen_timer_on = False
def screen_timer_toggler():
    global screen_timer_on
    screen_timer_on = not screen_timer_on
    play_sound('screenTimerOn' if screen_timer_on else 'screenTimerOff')
    if screen_timer_on:
        schedule.every(20*60+10+25).seconds.do(play_screen_timer).tag('screen_timer')
    else:
        schedule.clear('screen_timer')

MAIN_STATE.update({
    "INPUTS": {
        13: [sound_player('enterWeight'),move_state(ENTER_WEIGHT_ENTRY_STATE)], # = enter weight
        55: [sound_player('enterSleep'),move_state(ENTER_SLEEP_ENTRY_STATE)], # * enter sleep
        98: screen_timer_toggler, # / toggle screen timer
        96: sound_player('key')
    }
})
curr_state = MAIN_STATE

# Scheduler needs to have its own loop because keyboard.read_event() is blocking
def update_scheduler_thread():
    while True:
        schedule.run_pending()
        time.sleep(0.5)
threading.Thread(target=update_scheduler_thread, daemon=True).start()

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