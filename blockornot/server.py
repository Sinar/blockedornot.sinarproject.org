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
from worker import call_full_request_task
from celery import chain
import re
import logging
from logging.handlers import RotatingFileHandler
import uuid
import os


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
@app.route("/about")
def about():
    return render_template("about.html")

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

@app.route("/dump")
def dump_json():
    ITEM_PER_PAGE = 10
    page = request.args.get("page")
    if not page:
        page = 1
    page = int(page)
    output = []
    result_data = ResultData.select()
    count = result_data.count()
    result_page = result_data.paginate(page, paginate_by=ITEM_PER_PAGE)
    num_page = count / ITEM_PER_PAGE + 1
    for entry in result_page:
        output.append(entry.to_json())
    json_output = {
        "pages": num_page,
        "total": count,
        "page": page,
        "item_per_page": ITEM_PER_PAGE,
        "results": output
    }
    if page > 1:
        json_output["prev_url"] = "%s/dump?page=%s" % (app.config["URL"], page - 1)
    if page < num_page:
        json_output["next_url"] = "%s/dump?page=%s" % (app.config["URL"], page + 1)

    return jsonify(json_output)



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
            # TODO: Simplify this
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
                    emit("result_received", result_data.to_json(), room=result_data.transaction_id)

            elif testsuite in ("http_google", "http_TM", "http_opendns"):
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
                            call_full_request_task.s(result_data.to_json()).set(queue=location_queue),
                            update_entry.s().set(queue="basecamp"),
                            post_update.s().set(queue="basecamp")
                        ).apply_async()
                    emit("result_received", result_data.to_json(), room=result_data.transaction_id)

            elif testsuite in ("http", "http_dpi_tampering"):
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
    current_path = os.path.dirname(__file__)
    path = os.path.join(current_path, "log", "blockedornot.log")

    handler = RotatingFileHandler(path, maxBytes=10000, backupCount=2)
    # This project is in development. So yeah I need it.
    # Reduce level once we consider this out of development
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    socketio.run(app, host="0.0.0.0", port=app.config["PORT"], use_reloader=True)
    #app.run(host="0.0.0.0", debug=True)