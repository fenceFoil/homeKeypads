from datetime import datetime
from gotifyLoggingHandler import GotifyHandler
import keyboard
import logging
from logging import debug, info, warning, error, critical
import psycopg2
import os
import subprocess

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

def play_sound(soundName):
    subprocess.Popen(["aplay", "homeKeypads/sounds/{}.wav".format(soundName)])

def log_self_tracking_data(table, data):
    

def log_to_debug_pg (msg):
    connection = None
    try:
        connection = psycopg2.connect(user = os.environ['KEYPADS_PG_USERNAME'],
                                    password = os.environ['KEYPADS_PG_PASSWORD'],
                                    host = os.environ['KEYPADS_PG_HOSTNAME'],
                                    port = 5432,
                                    database = os.environ["KEYPADS_PG_DB_NAME"])
        cursor = connection.cursor()
        cursor.execute("INSERT INTO debug_temp (message_time, log_entry) VALUES (%s,%s)", (datetime.now(), msg))
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        error ("Error while connecting to PostgreSQL", error)
    finally:
        #closing database connection.
        if(connection):
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")    

while True:
    log_to_debug_pg(keyboard.read_event().to_json())