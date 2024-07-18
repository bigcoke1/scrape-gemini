#third-party lib
from flask import Flask, render_template, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

#python lib
import uuid
import sqlite3
import logging
import json
from threading import Thread

#my lib
from main import *

SERVER_ERROR_MSG = "Internal server error"
PARAM_ERROR_MSG = "Invalid params error"
HTTP_ERROR_MSG = "Wrong HTTP method"

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
                cur.execute("INSERT INTO user (username, password, email) VALUES (?, ?, ?)", [username, password, email])
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

@app.route("/getresponse", methods=["POST"])
def get_response():
    query = request.form.get("query")
    username = request.form.get("username")
    if query and username:
        try:
            links = search_google(query)
            links = [link for link in links if link is not None]
            result = iter_result(links)
            text_response, data_response, format = get_AI_response(query, result)
            current_datetime = get_date()
            json_links = json.dumps(links)
            
            con = sqlite3.connect(USER_DATA)
            cur = con.cursor()
            cur.execute("INSERT INTO chat (username, query, response, date, links, data, format) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                        [username, query, text_response, current_datetime, json_links, data_response, format])
            con.commit()
            con.close()
            return jsonify([text_response, data_response, format, links])
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

def run():
    app.run(host="0.0.0.0", port=5000)

def keep_alive():
  t = Thread(target=run)
  t.start()

if __name__ == "__main__":
    keep_alive()
