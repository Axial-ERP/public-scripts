"""
Perform a backup of all PostgreSQL databases and proceed with uploading them to Google Drive.
Author: Alex Bochkov, Axial ERP, https://axial-erp.co
Date: May 14, 2023

Configuration:
0. Prerequisites:
  - The script folder is set to `C:\Python`.
  - PostgreSQL version 14.4-1.1C is installed in `C:\Program Files\PostgreSQL\14.4-1.1C\bin`.
1. Enable the Google Drive API in the Google Cloud Console.
2. Create a new service account and obtain its credentials in a JSON file. Save the JSON file to `C:\Python\service_account.json`.
3. Create a new folder in Google Drive and share it with the service account.
4. Create a file named `.env` in `C:\Python` and add two variables: DB_USER and DB_PASSWORD.
5. Use a PowerShell script to create a scheduled task that performs the backup regularly.
"""

# pip install psycopg2
# pip install python-dotenv
# pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import psycopg2
from datetime import datetime
import subprocess
from dotenv import load_dotenv
import os
import logging

load_dotenv()

#-------------------------------------
# Clear previous configuration (to avoid duplicated messages in Spider during the debug)
logger = logging.getLogger()

# Remove all handlers associated with the root logger
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
#-------------------------------------
path = os.environ["PATH"]

# Define the path to PostgreSQL bin directory
pg_path = r"C:\Program Files\PostgreSQL\14.4-1.1C\bin"

# Add the PostgreSQL bin directory to the system PATH
os.environ["PATH"] = path + os.pathsep + pg_path
#-------------------------------------

# Set up logging
logging.basicConfig(filename='db_backup.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Create a stream handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)

# Set the same formatter for console handler
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
console.setFormatter(formatter)

# Add the handler to the root logger
logging.getLogger('').addHandler(console)

def backup_postgres_db(host, user, password, folder_id):
    try:
        conn_string = f"host='{host}' user='{user}' password='{password}' dbname='postgres'"
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cur = conn.cursor()

        # get the list of databases
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        db_list = cur.fetchall()

        for db in db_list:
            dbname = db[0]
            
            logging.info("Processing [{0}] database".format(dbname))

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')  # format the timestamp
            backup_file = f'C:\\Python\\backups\\{dbname}_{timestamp}_backup.sql'  # add the timestamp to the backup file name

            # use pg_dump to backup the database
            command = f"pg_dump -F c -Z 9 --username={user} --dbname={dbname} --file={backup_file}"        
            os.putenv('PGPASSWORD', password)  # Set PGPASSWORD environment variable
            subprocess.call(command, shell=True)
            os.unsetenv('PGPASSWORD')  # Unset PGPASSWORD environment variable

            if os.path.exists(backup_file):
                logging.info("Uploading the backups file to GDrive...")
                upload_to_google_drive(backup_file, folder_id)
                os.remove(backup_file)  # delete the backup file after upload
            else:
                logging.error("The database backup file doesn't exist")

        cur.close()
        conn.close()
    except Exception as e:
        logging.error("An error occurred during the backup process: %s", str(e))

def upload_to_google_drive(local_filename, folder_id):
    try:
        creds = Credentials.from_service_account_file("C:\\Python\\service_account.json", 
                                                      scopes=['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=creds)

        media = MediaFileUpload(local_filename, mimetype='application/octet-stream', resumable=True)

        request = drive_service.files().create(
            media_body=media,
            body={
                'name': local_filename.split('/')[-1],
                'parents': [folder_id]
            }
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logging.info("Uploaded %d%%." % int(status.progress() * 100))

        logging.info("Upload complete.")
    except Exception as e:
        logging.error("An error occurred during the upload process: %s", str(e))



# Google Drive folder ID which is shared with the service account
folder_id = '......'
host = 'localhost'
user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')

backup_postgres_db(host, user, password, folder_id)
