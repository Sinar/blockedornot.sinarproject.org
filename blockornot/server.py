__author__ = 'sweemeng'
from gevent import monkey; monkey.patch_all()
# Because socketio module uses gevent
from app import create_app
from flask import render_template
from flask import request
from flask import jsonify
from flask.ext.socketio import SocketIO
from flask.ext.socketio import emit
from flask.ext.socketio import join_room
from models import db
from models import ResultData
from worker import call_http_task
from worker import call_dns_task
from worker import call_http_dpi_tampering_task
from worker import update_entry
from worker import post_update
from celery import chain
import re
import logging
import uuid


app = create_app()
socketio = SocketIO(app)

@app.before_request
def _db_connect():
    db.connect()

@app.before_request
def _db_teardown():
    db.close()

"""
JSON Trigger
1) Call test
2) Get transaction id
3) redirect to page
"""
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

@app.route("/postback", methods=["POST"])
def postback():
    data = request.get_json(force=True)
    logging.warn(data)
    socketio.emit("result_received", data, room=data["transaction_id"], namespace="/check")
    return "OK"

@app.route("/<transaction_id>.json")
def fetch_json(transaction_id):
    result_data = ResultData.select().where(ResultData.transaction_id==transaction_id)
    output = []
    for entry in result_data:
        output.append(entry.to_json())

    return jsonify({ "results": output, "total": len(output) })

@app.route("/<transaction_id>.html")
def fetch_html(transaction_id):
    result_data = ResultData.select().where(ResultData.transaction_id==transaction_id)
    output = {}
    entry_url = ""
    for entry in result_data:
        # it is the same url, and I'm lazy
        entry_url = entry.url
        isp = output.setdefault(entry.isp, {})
        location = isp.setdefault(entry.location, [])
        location.append({ "description": entry.description, "status": entry.status, "reason": entry.reason,
                          "task_status": entry.task_status })
    current_url = "%s/%s.html" % (app.config["URL"], transaction_id)
    return render_template("index.html", output=output, share=True, url=app.config["URL"], current_url=current_url,
                           target_url= entry_url)


@socketio.on("check", namespace="/check")
def call_check(data):
    join_room(data["transaction_id"])
    url = data["url"]
    if not re.match(r"^http\://", url):
        data["url"] = "http://%s" % url
    for location in app.config["LOCATIONS"]:
        for testsuite in location["testsuites"]:

            input_data = {
                "transaction_id": data["transaction_id"],

                "location": location["location"],
                "country": location["country"],
                "ISP": location["ISP"],
                "url": data["url"],
            }
            location_queue = "%s_%s" % (location["location"].lower().replace(" ", "_"), location["ISP"].lower().replace(" ", "_"))
            logging.warn(location_queue)

            input_data["test_type"] = testsuite
            if testsuite in ("dns_google", "dns_TM", "dns_opendns"):
                for server in app.config["TESTSUITES"][testsuite]["servers"]:
                    input_data["task_id"] = str(uuid.uuid4())

                    extra_attr = {
                        "provider": app.config["TESTSUITES"][testsuite]["provider"],
                        "server": server
                    }
                    input_data["extra_attr"] = extra_attr
                    logging.warn("DNS Check")
                    description = "%s server: %s " % (app.config["TESTSUITES"][testsuite]["description"], server)
                    input_data["description"] = description
                    result_data = ResultData.from_json(input_data, extra_attr=extra_attr)
                    task = chain(
                            call_dns_task.s(result_data.to_json()).set(queue=location_queue),
                            update_entry.s().set(queue="basecamp"),
                            post_update.s().set(queue="basecamp")
                        ).apply_async()

            else:
                input_data["task_id"] = str(uuid.uuid4())

                input_data["description"] = app.config["TESTSUITES"][testsuite]["description"]
                result_data = ResultData.from_json(input_data)

                if testsuite == "http":
                    task = chain(
                        call_http_task.s(result_data.to_json()).set(queue=location_queue),
                        update_entry.s().set(queue="basecamp"),
                        post_update.s().set(queue="basecamp")
                    ).apply_async()
                elif testsuite == "http_dpi_tampering":
                    task = chain(
                        call_http_dpi_tampering_task.s(result_data.to_json()).set(queue=location_queue),
                        update_entry.s().set(queue="basecamp"),
                        post_update.s().set(queue="basecamp")
                    ).apply_async()
            emit("result_received", result_data.to_json(), room=result_data.transaction_id)

if __name__ == "__main__":
    app.debug=True
    socketio.run(app, host="0.0.0.0", port=app.config["PORT"], use_reloader=True)
    #app.run(host="0.0.0.0", debug=True)