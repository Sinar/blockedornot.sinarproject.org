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
# TODO: Iterate through server list, call worker from different location
@socketio.on("check http", namespace="/checkhttp")
def check_http(json):
    data = json
    url = data["url"]
    if not re.match(r"^http\://", url):
        url = "http://%s" % url
    result = HTTPResult("TM", "Subang Jaya", param=url)
    result.run()

    emit("http received", result.to_json())

# Really you should just put it to a task somewhere to push it to socket io
@socketio.on("http result", namespace="/checkhttp")
def http_result(json):
    task_id = json["task_id"]
    result = HTTPResult("TM", "Subang Jaya", task_id=task_id)
    result.run()
    emit("http received", result.to_json())

# TODO: Test with different DNS server
# TODO: Have a list of dns server to test
@socketio.on("check dns", namespace="/checkdns")
def check_dns(data):
    url = data["url"]
    result = DNSResult("8.8.8.8", "google", param=url)
    result.run()

    emit("dns received", result.to_json())

@socketio.on("dns result", namespace="/checkdns")
def dns_result(data):
    task_id = data["task_id"]
    result = DNSResult("8.8.8.8", "google", task_id=task_id)
    result.run()

    emit("dns received", result.to_json())

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", use_reloader=True)
    #app.run(host="0.0.0.0", debug=True)