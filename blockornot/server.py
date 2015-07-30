__author__ = 'sweemeng'
from app import create_app
from flask import render_template
from flask.ext.socketio import SocketIO
from flask.ext.socketio import emit
from results import HTTPResult
from results import DNSResult
from results import HttpDpiTamperingResult
import re
import logging
import uuid


app = create_app()
socketio = SocketIO(app)


# TODO: create uuid to be passed around.
@app.route("/")
def index():
    # TODO: WTF, simplify this
    transaction_id = str(uuid.uuid4())
    isps = set()
    locations = {}
    testsuites = {}
    for location in app.config["LOCATIONS"]:
        isps.add(location["ISP"])
        temp_location = locations.setdefault(location["ISP"], [])
        temp_location.append(location["location"])
        isp_testsuites = testsuites.setdefault(location["ISP"], {})
        isp_testsuites[location["location"]] = location["testsuites"]

    testdetail = app.config["TESTSUITES"]
    return render_template("index.html", isps=isps, locations=locations, testsuites=testsuites, testdetail=testdetail,
                           transaction_id=transaction_id)

# Now how do we tidy up this code
test_results = {
    "http" : HTTPResult,
    "dns_TM" : DNSResult,
    "dns_opendns" : DNSResult,
    "dns_google" : DNSResult,
    "http_dpi_tampering" : HttpDpiTamperingResult,

}

@socketio.on("check", namespace="/check")
def call_check(data):
    url = data["url"]
    if not re.match(r"^http\://", url):
        url = "http://%s" % url
    for location in app.config["LOCATIONS"]:
        for testsuite in location["testsuites"]:
            # This is a special case, how to consolidate it
            if test_results[testsuite] == DNSResult:
                test_config = app.config["TESTSUITES"][testsuite]
                for server in test_config["servers"]:

                    test_promise = test_results[testsuite](
                        location["ISP"],
                        location["location"],
                        server,
                        test_config["provider"],
                        testsuite,
                        data["transaction_id"],
                        param = url
                    )
                    test_promise.run()
                    emit("result_received", test_promise.to_json())

            else:
                logging.warn(data)
                test_promise = test_results[testsuite](
                    location["ISP"],
                    location["location"],
                    testsuite,
                    data["transaction_id"],
                    param=url
                )
                test_promise.run()
                emit("result_received", test_promise.to_json())

@socketio.on("check_result", namespace="/check")
def check_result(data):

    if test_results[data["test_type"]] == DNSResult:
        test_promise = test_results[data["test_type"]](
            data["ISP"],
            data["location"],
            data["server"],
            data["provider"],
            data["test_type"],
            data["transaction_id"],
            task_id=data["task_id"]
        )
    else:
        test_promise = test_results[data["test_type"]](
            data["ISP"],
            data["location"],
            data["test_type"],
            data["transaction_id"],
            task_id=data["task_id"]
        )

    test_promise.run()
    emit("result_received", test_promise.to_json())


if __name__ == "__main__":
    app.debug=True
    socketio.run(app, host="0.0.0.0", port=app.config["PORT"], use_reloader=True)
    #app.run(host="0.0.0.0", debug=True)