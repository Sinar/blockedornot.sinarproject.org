__author__ = 'sweemeng'
from app import app
from flask import render_template
from flask.ext.socketio import SocketIO
from flask.ext.socketio import emit
from worker import http_task
from worker import dns_task
import logging
import datetime
import re

socketio = SocketIO(app)


@app.route("/")
def index():
    return render_template("index.html")

# Now how do we tidy up this code
@socketio.on("check http", namespace="/checkhttp")
def check_http(json):
    data = json
    url = data["url"]
    if not re.match(r"^http\://", url):
        url = "http://%s" % url
    r = http_task.delay(url)
    result = {"task_id":r.id, "status": "PENDING"}
    emit("http received", result)

# Really you should just put it to a task somewhere to push it to socket io
@socketio.on("http result", namespace="/checkhttp")
def http_result(json):
    task_id = json["task_id"]
    result = http_task.AsyncResult(task_id)
    if result.status == "PENDING":
        output = { "task_id":result.id, "status": "PENDING" }
    elif result.status == "SUCCESS":
        data = result.get()
        output = { "task_id":result.id, "status": "SUCCESS", "status_code": data.status_code }
    else:
        output = { "task_id": result.id, "status": "error"}
    emit("http received", output)

@socketio.on("check dns", namespace="/checkdns")
def check_dns(data):
    url = data["url"]
    result = dns_task.delay(url)
    output = { "task_id":result.id, "status":"PENDING"}
    emit("dns received", output)

@socketio.on("dns result", namespace="/checkdns")
def dns_result(data):
    task_id = data["task_id"]
    result = dns_task.AsyncResult(task_id)
    if result.status == "PENDING":
        output = { "task_id": task_id, "status": "PENDING"}
    elif result.status == "SUCCESS":
        result_data = result.get()

        output = { "task_id": task_id, "status": "SUCCESS", "result":result_data}
    else:
        output = { "task_id": task_id, "status": "error"}
    emit("dns received", output)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", use_reloader=True)
    #app.run(host="0.0.0.0", debug=True)