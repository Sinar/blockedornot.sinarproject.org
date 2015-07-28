__author__ = 'sweemeng'
from app import create_app
from flask import render_template
from flask.ext.socketio import SocketIO
from flask.ext.socketio import emit
from worker import http_task
from worker import dns_task
from utils import HTTPResult
from utils import DNSResult
import re


app = create_app()
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
    for entry in app.config["LOCATIONS"]:
        result = HTTPResult(entry["ISP"], entry["location"], param=url)
        result.run()

        emit("http received", result.to_json())

# Really you should just put it to a task somewhere to push it to socket io
@socketio.on("http result", namespace="/checkhttp")
def http_result(json):
    task_id = json["task_id"]
    result = HTTPResult(json["ISP"], json["location"], task_id=task_id)
    result.run()
    emit("http received", result.to_json())

@socketio.on("check dns", namespace="/checkdns")
def check_dns(data):
    url = data["url"]
    for targets in app.config["DNS_TARGETS"]:
        result = DNSResult(targets["server"], targets["provider"], param=url)
        result.run()

        emit("dns received", result.to_json())

@socketio.on("dns result", namespace="/checkdns")
def dns_result(data):
    task_id = data["task_id"]
    result = DNSResult(data["server"], data["provider"], task_id=task_id)
    result.run()

    emit("dns received", result.to_json())

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", use_reloader=True)
    #app.run(host="0.0.0.0", debug=True)