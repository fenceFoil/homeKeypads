from datetime import datetime
import keyboard
import psycopg2
import os

connection = None
try:
    connection = psycopg2.connect(user = os.environ['KEYPADS_PG_USERNAME'],
                                  password = os.environ['KEYPADS_PG_PASSWORD'],
                                  host = os.environ['KEYPADS_PG_HOSTNAME'],
                                  port = 5432,
                                  database = os.environ["KEYPADS_PG_DB_NAME"])
    cursor = connection.cursor()
    cursor.execute("INSERT INTO debug_temp (message_time, log_entry) VALUES (%s,%s)", (datetime.now(), "hello world"))
    connection.commit()
except (Exception, psycopg2.Error) as error:
    print ("Error while connecting to PostgreSQL", error)
finally:
    #closing database connection.
    if(connection):
        cursor.close()
        connection.close()
        print("PostgreSQL connection is closed")    