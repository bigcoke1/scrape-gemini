#third-party lib
from flask import Flask, render_template, request, Response, jsonify, session, redirect
from flask_cors import CORS
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import Flow
from PIL import Image
from argon2 import PasswordHasher
import markdown

#python lib
import uuid
import logging
from threading import Thread
import base64
import os
import sqlite3
import time
import datetime
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)
USER_DATA = "user_data.db"

@app.before_request
def before_request():
    if request.headers.get('X-Forwarded-Proto') == 'https':
        request.url = request.url.replace('http://', 'https://')

#my lib
from google_init import *
from rag import *
from weaviate_init import init_db

SERVER_ERROR_MSG = "Internal server error"
PARAM_ERROR_MSG = "Invalid params error"
HTTP_ERROR_MSG = "Wrong HTTP method"
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRETS_FILE = "credentials.json"
URL = "http://127.0.0.1:5000/"

ph = PasswordHasher()

@app.route('/')
def init():
    unique_id = str(uuid.uuid4())
    return render_template('index.html', unique_id=unique_id)

@app.route("/register", methods=["POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        try:
            con = sqlite3.connect(USER_DATA)
            cur = con.cursor()
        
            res = cur.execute("SELECT username FROM user WHERE username = ?", [username])
            if username and password and email and not res.fetchone():
                password = ph.hash(password)
                cur.execute("INSERT INTO user (username, password, email, databases) VALUES (?, ?, ?, ?)", [username, password, email , "[]"])
                con.commit()
                con.close()
                return Response("successful", status=200, mimetype="text/plain")
            else:
                return Response(PARAM_ERROR_MSG, status=400, mimetype="text/plain")
        except:
            logging.error("An error occured", exc_info=True)
            return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")
    else:
        return Response(HTTP_ERROR_MSG, status=400, mimetype="text/plain")

@app.route("/login", methods=["POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username and password:
            try:
                con = sqlite3.connect(USER_DATA)
                cur = con.cursor()
                res = cur.execute("SELECT password FROM user WHERE username = ?", [username])
                real_password = res.fetchone()[0]
                con.close()
                if ph.verify(real_password, password):
                    return Response("successful", status=200, mimetype="text/plain")
                else:
                    return Response("Wrong username or password", status=400, mimetype="text/plain")
            except:
                logging.error("An error occured", exc_info=True)
                return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")
        else:
            return Response(PARAM_ERROR_MSG, status=400, mimetype="text/plain")
    else:
        return Response(HTTP_ERROR_MSG, status=400, mimetype="text/plain")

def get_date():
    current_datetime = datetime.datetime.now()
    format_string = "%m-%d-%y"
    return current_datetime.strftime(format_string)

@app.route("/getresponse", methods=["POST"])
def get_response():
    query = request.form.get("query")
    username = request.form.get("username")
    if query and username:
        try:
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_dspy = executor.submit(get_dspy_answer, query, username)
                future_links = executor.submit(search_google, query)
                
            text_response, data_response, format = future_dspy.result()
            text_response = markdown.markdown(text_response, extensions=['nl2br'])
           
            links = future_links.result()
            print(f"Got AI response in {time.time() - start_time} seconds")
            links = [link for link in links if link is not None]
            links = list(set(links))
            json_links = json.dumps(links)
            
            con = sqlite3.connect(USER_DATA)
            cur = con.cursor()
            cur.execute("INSERT INTO chat (username, query, response, date, links, data, format) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                        [username, query, text_response, get_date(), json_links, data_response, format])
            con.commit()
            id = cur.lastrowid
            con.close()
            return jsonify([text_response, data_response, format, links, id])
        except:
            logging.error("An error occurred", exc_info=True)
            return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")
    else:
        return Response(PARAM_ERROR_MSG, status=400, mimetype="text/plain")

@app.route("/get-all-chat/<username>", methods=["GET"])
def get_all_chat(username):
    try:
        con = sqlite3.connect(USER_DATA)
        cur = con.cursor()
        results = cur.execute("SELECT * FROM chat WHERE username = ?", [username])
        results = results.fetchall()
        if not results:
            results = []
        con.close()
        return jsonify([list(result) for result in results])
    except:
        return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")

@app.route("/delete", methods=["POST"])
def delete():
    id = request.form["id"]
    if id:
        try:
            con = sqlite3.connect(USER_DATA)
            cur = con.cursor()
            cur.execute("DELETE FROM chat WHERE id = ?", [id])
            con.commit()
            con.close()
            return Response("successful", status=200, mimetype="text/plain")
        except:
            return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")
    else:
        return Response(PARAM_ERROR_MSG, status=400, mimetype="text/plain")

@app.route("/clear", methods=["POST"])
def clear():
    username = request.form["username"]
    if username:
        try:
            con = sqlite3.connect(USER_DATA)
            cur = con.cursor()
            cur.execute("DELETE FROM chat WHERE username = ?", [username])
            con.commit()
            con.close()
            return Response("successful", status=200, mimetype="text/plain")
        except:
            logging.error("An error occured", exc_info=True)
            return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")
    else:
        return Response(PARAM_ERROR_MSG, status=400, mimetype="text/plain")

@app.route("/account/<username>", methods=["GET"])
def account(username):
    try:
        con = sqlite3.connect(USER_DATA)
        cur = con.cursor()
        response = cur.execute("SELECT email FROM user WHERE username = ?", [username])
        email = response.fetchone()[0]
        con.close()
        return Response(email, status=200, mimetype="text/plain")
    except:
        logging.error("An error occured", exc_info=True)
        return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")

@app.route("/save-image", methods=["POST"])
def save_image():
    try:
        username = request.form.get("username")
        image = request.files.get("image")

        file_path = f"static/images/pfps/{username}.png"
        img = Image.open(image.stream)
        # Save the image as PNG
        img.save(file_path, 'PNG')
        return Response("image saved", status=200, mimetype="text/plain")
    except:
        return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")

@app.route('/google')
def google():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = f'{URL}/oauth2callback'

    authorization_url, state = flow.authorization_url(
        access_type='offline', include_granted_scopes='true', prompt='consent')

    session['state'] = state
    return redirect(authorization_url)

@app.route("/oauth2callback")
def oauth2callback():
    state = session['state']
    username = session["username"]
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = f'{URL}/oauth2callback'

    authorization_response = request.url
    print(f'request url: {request.url}')
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    token_path = f'tokens/token_{username}.json'
    with open(token_path, 'w') as token_file:
        token_file.write(credentials.to_json())

    return redirect(URL)

def get_credentials(username):
    try:
        """Fetches credentials for a specific user."""
        token_path = f'tokens/token_{username}.json'
        if not os.path.exists(token_path):
            session["username"] = username
            return redirect(f'{URL}/google')

        with open(token_path, 'r') as token_file:
            creds = Credentials.from_authorized_user_info(json.load(token_file), SCOPES)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'w') as token_file:
                token_file.write(creds.to_json())
        
        return creds
    except:
        logging.error("An error occured", exc_info=True)

def get_or_create_folder(service, folder_name):
    try:
        # Query to search for the folder by name
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
        
        # Execute the search query
        results = service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
        items = results.get('files', [])
        
        if items:
            # Folder exists
            print(f"Folder '{folder_name}' exists with ID: {items[0]['id']}")
            return items[0]['id']
        else:
            # Folder does not exist, create it
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            print(f"Created folder '{folder_name}' with ID: {folder.get('id')}")
            return folder.get('id')
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def upload_file(chat_id, username, data):
    creds = get_credentials(username)
    if isinstance(creds, Response):
        return creds
    service = build('drive', 'v3', credentials=creds)
    parent = get_or_create_folder(service, "scrape-insight")
    if data.startswith("data:image/png;base64"):
        base64_string = data.split(',')[1]
        image_data = base64.b64decode(base64_string)
        # File to be uploaded
        save_path = f'chart/{chat_id}.png'
        with open(save_path, "wb") as file:
            file.write(image_data)

        file_metadata = {'name': f'{chat_id}_chart.png','parents': [parent]}
        media = MediaFileUpload(save_path, mimetype='image/png')
    else:
        save_path = f'chart/{chat_id}.csv'
        with open(save_path, "w") as file:
            file.write(data)

        file_metadata = {'name': f'{chat_id}_table.csv','parents': [parent]}
        media = MediaFileUpload(save_path, mimetype='text/csv')

    # Upload the file
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f'File ID: {file.get("id")}')
    os.remove(save_path)

    return file.get("id")
    
@app.route("/upload", methods=["POST"])
def upload():
    try:
        id = request.form["id"]
        data = request.form["data"]

        con = sqlite3.connect(USER_DATA)
        cur = con.cursor()
        response = cur.execute("SELECT username FROM chat WHERE id = ?", [id])
        username = response.fetchone()[0]
        con.close()
        return upload_file(chat_id=id, username=username, data=data)
    except:
        logging.error("An error occured", exc_info=True)
        return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")

@app.route('/upload-db', methods=['POST'])
def upload_db():
    try:
        files = request.files.getlist('files[]')
        filenames = request.form.getlist("filenames[]")
        username = request.form["username"]
        if files and filenames and username:
            con = sqlite3.connect(USER_DATA)
            cur = con.cursor()
            if not os.path.exists(f"user_databases/{username}"):
                os.makedirs(f"user_databases/{username}")
            for index in range(0, len(files)):
                with open(f"user_databases/{username}/{filenames[index]}", 'w') as regular_file:
                    json.dump(json.load(files[index].stream), regular_file)
            result = cur.execute("SELECT databases FROM user WHERE username = ?", [username])
            existing_files = result.fetchone()[0]
            existing_files = json.loads(existing_files)
            if existing_files is None:
                existing_files = []
            filenames.extend(existing_files)
            filenames = list(set(filenames))
            init_db(filenames, username)
            filenames_str = json.dumps(filenames)
            print(filenames)
            print("Databse intialized")
            cur.execute("UPDATE user SET databases = ? WHERE username = ?", [filenames_str, username])
            con.commit()
            con.close()
            return jsonify(filenames)
        else:
            return Response(PARAM_ERROR_MSG, status=400, mimetype="text/plain")
    except:
        logging.error("An error occured", exc_info=True)
        return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")

@app.route("/get-databases/<username>", methods=["GET"])
def get_databases(username):
    try:
        con = sqlite3.connect(USER_DATA)
        cur = con.cursor()
        result = cur.execute("SELECT databases FROM user WHERE username = ?", [username])
        databases = result.fetchone()[0]
        databases = json.loads(databases)
        return jsonify(databases)
    except:
        logging.error("An error occured", exc_info=True)
        return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")

@app.route("/delete-database", methods=["POST"])
def delete_database():
    try:
        filename = request.form["filename"]
        username = request.form["username"]

        con = sqlite3.connect(USER_DATA)
        cur = con.cursor()
        result = cur.execute("SELECT databases FROM user WHERE username = ?", [username])
        databases = result.fetchone()[0]
        databases = json.loads(databases)
        databases.remove(filename)
        databases_str = json.dumps(databases)
        print(databases_str)
        cur.execute("UPDATE user SET databases = ? WHERE username = ?", [databases_str, username])
        con.commit()
        con.close()
        
        path = f"user_databases/{username}/{filename}"
        if os.path.exists(path):
            os.remove(path)
        
        init_db(files=databases, username=username)
        print("Database updated")
        return jsonify(databases)

    except:
        logging.error("An error occured", exc_info=True)
        return Response(SERVER_ERROR_MSG, status=500, mimetype="text/plain")
 
def run():
    app.run(host="0.0.0.0", port=5000)

def keep_alive():
  t = Thread(target=run)
  t.start()

if __name__ == "__main__":
    keep_alive()