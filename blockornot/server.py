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
import urlparse


app = create_app()
socketio = SocketIO(app)


@app.route("/")
def index():
    # TODO: WTF, simplify this
    isps = []
    locations = {}
    testsuites = {}
    for location in app.config["LOCATIONS"]:
        isps.append(location["ISP"])
        temp_location = locations.setdefault(location["ISP"], [])
        temp_location.append(location["location"])
        isp_testsuites = testsuites.setdefault(location["ISP"], {})
        isp_testsuites[location["location"]] = location["testsuites"]

    testdetail = app.config["TESTSUITES"]
    return render_template("index.html", isps=isps, locations=locations, testsuites=testsuites, testdetail=testdetail)

# Now how do we tidy up this code
@socketio.on("check http", namespace="/checkhttp")
def check_http(json):
    data = json
    url = data["url"]
    if not re.match(r"^http\://", url):
        url = "http://%s" % url
    for entry in app.config["LOCATIONS"]:
        if "http" in entry["testsuites"]:
            result = HTTPResult(entry["ISP"], entry["location"], "http", param=url)
            result.run()

        emit("http received", result.to_json())

# Really you should just put it to a task somewhere to push it to socket io
@socketio.on("http result", namespace="/checkhttp")
def http_result(json):
    task_id = json["task_id"]
    result = HTTPResult(json["ISP"], json["location"], json["test_id"], task_id=task_id)
    result.run()
    emit("http received", result.to_json())

@socketio.on("check dns", namespace="/checkdns")
def check_dns(data):
    url = data["url"]
    if not re.match(r"^http\://", url):
        url = "http://%s" % url

    parsed = urlparse.urlparse(url)
    url = parsed.netloc

    for entry in app.config["LOCATIONS"]:
        for dns_test in ["dns_TM", "dns_opendns", "dns_google"]:
            if dns_test in entry["testsuites"]:
                targets = app.config["TESTSUITES"][dns_test]
                # TODO: can bite if we decide to only test certain server.
                pos = 1
                for server in targets["servers"]:
                    test_id = "%s_%s" % (dns_test, pos)
                    result = DNSResult(entry["ISP"], entry["location"], server, targets["provider"], test_id, param=url)
                    result.run()

                    emit("dns received", result.to_json())
                    pos = pos + 1


@socketio.on("dns result", namespace="/checkdns")
def dns_result(data):
    task_id = data["task_id"]
    result = DNSResult(data["ISP"], data["location"], data["server"], data["provider"], data["test_id"], task_id=task_id)
    result.run()

    emit("dns received", result.to_json())

if __name__ == "__main__":
    app.debug=True
    socketio.run(app, host="0.0.0.0", port=app.config["PORT"], use_reloader=True)
    #app.run(host="0.0.0.0", debug=True)