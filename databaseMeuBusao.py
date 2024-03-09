import psycopg2 
import os

def getConnectionCursor(database):
    server = os.environ['SERVER'] 
    conn = psycopg2.connect(
    host=server,
    database=database,
    user=os.environ['USER'],
    password=os.environ['MOT'])
    
    conn.set_client_encoding('UTF8')
    
    cursor = conn.cursor()

    return cursor

def getVersion():
    cursor = getConnectionCursor()

    cursor.execute("SELECT @@version;") 
    row = cursor.fetchone()

    ret = ""

    while row: 
        print(row[0])
        ret = row[0]
        row = cursor.fetchone()
    
    return ret
