from threading import Thread
from pm4pydistr import configuration
from flask import Flask, request, jsonify
from flask_cors import CORS
from random import randrange
from time import time
from datetime import datetime
from pm4pydistr.configuration import PARAMETER_USE_TRANSITION, DEFAULT_USE_TRANSITION
from pm4pydistr.configuration import PARAMETER_NO_SAMPLES, DEFAULT_MAX_NO_SAMPLES
from pm4pydistr.configuration import PARAMETER_NUM_RET_ITEMS, DEFAULT_MAX_NO_RET_ITEMS
from pm4pydistr.master.variable_container import MasterVariableContainer
from pm4pydistr.master.db_manager import DbManager
from pm4py.objects.log.util import xes
from pythonping import ping

import logging, json, requests

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

class MasterSocketListener(Thread):
    app = Flask(__name__)
    CORS(app)

    def __init__(self, master, port, conf):
        MasterVariableContainer.port = port
        MasterVariableContainer.master = master
        MasterVariableContainer.conf = conf
        MasterVariableContainer.dbmanager = DbManager(MasterVariableContainer.conf)

        Thread.__init__(self)

    def run(self):
        self.app.run(host="0.0.0.0", port=MasterVariableContainer.port, threaded=True)


@MasterSocketListener.app.route("/registerSlave", methods=["GET"])
def register_slave():
    keyphrase = request.args.get('keyphrase', type=str)
    ip = request.args.get('ip', type=str)
    port = request.args.get('port', type=str)
    conf = request.args.get('conf', type=str)
    MasterVariableContainer.log_assignment_done = False
    MasterVariableContainer.slave_loading_requested = False

    if keyphrase == configuration.KEYPHRASE:
        id = [randrange(0, 10), randrange(0, 10), randrange(0, 10), randrange(0, 10), randrange(0, 10),
              randrange(0, 10), randrange(0, 10)]
        id = MasterVariableContainer.dbmanager.insert_slave_into_db(conf, id)
        #conf, id, port, time, PID, memory, CPUpct, cpuload, ping, temp
        MasterVariableContainer.master.slaves[str(id)] = [conf, ip, port, time(), 1, 1, 1, 1, 1, 1]
        try:
            r2 = requests.get(
            "http://" + MasterVariableContainer.master.host + ":" + port + "/getcurrentPIDinfo?keyphrase=" + configuration.KEYPHRASE)
            response = json.loads(r2.text)
            MasterVariableContainer.master.slaves[str(id)][4] = response['PID']
        except:
            del MasterVariableContainer.master.slaves[str(id)]
            return "Error while registering Slave"
        return jsonify({"id": str(id)})


@MasterSocketListener.app.route("/updateSlave", methods=["GET"])
def update_slave():
    keyphrase = request.args.get('keyphrase', type=str)
    id = request.args.get('id', type=str)
    ip = request.args.get('ip', type=str)
    port = request.args.get('port', type=str)
    conf = request.args.get('conf', type=str)

    if keyphrase == configuration.KEYPHRASE:
        MasterVariableContainer.master.slaves[id] = [conf, ip, port, time(), 1, 1, 1, 1 ,1]
        return jsonify({"id": id})


@MasterSocketListener.app.route("/pingFromSlave", methods=["GET"])
def ping_from_slave():
    received_time = int(round(time() * 1000))
    keyphrase = request.args.get('keyphrase', type=str)
    id = request.args.get('id', type=str)
    port = request.args.get('port', type=str)
    conf = request.args.get('conf', type=str)

    if keyphrase == configuration.KEYPHRASE:
        try:
            #pingadrr = str(ip) + ':' + str(port)
            #response_list = ping('8.8.8.8', size=40, count=10)
            #pinged = response_list.rtt_avg_ms
            MasterVariableContainer.master.slaves[id][3] = time()
            #MasterVariableContainer.master.slaves[id][7] = pinged
            r2 = requests.get(
                 "http://" + MasterVariableContainer.master.host + ":" + str(MasterVariableContainer.master.slaves[id][2]) + "/getMemory?keyphrase=" + configuration.KEYPHRASE)
            response = json.loads(r2.text)
            MasterVariableContainer.master.slaves[str(id)][5] = response['Memory']
            r3 = requests.get(
                "http://" + MasterVariableContainer.master.host + ":" + str(
                    MasterVariableContainer.master.slaves[id][2]) + "/getCPU?keyphrase=" + configuration.KEYPHRASE)
            response = json.loads(r3.text)
            MasterVariableContainer.master.slaves[str(id)][6] = response['CPU']
            r4 = requests.get(
                "http://" + MasterVariableContainer.master.host + ":" + str(
                    MasterVariableContainer.master.slaves[id][2]) + "/getCPUload?keyphrase=" + configuration.KEYPHRASE)
            response = json.loads(r4.text)
            MasterVariableContainer.master.slaves[str(id)][7] = response['CPUload']
            r5 = requests.get(
                "http://" + MasterVariableContainer.master.host + ":" + str(
                    MasterVariableContainer.master.slaves[id][2]) + "/getDiskUsage?keyphrase=" + configuration.KEYPHRASE)
            response = json.loads(r5.text)
            MasterVariableContainer.master.slaves[str(id)][8] = response['Disk Usage']
            r6 = requests.get(
                "http://" + MasterVariableContainer.master.host + ":" + str(
                    MasterVariableContainer.master.slaves[id][2]) + "/getTemperature?keyphrase=" + configuration.KEYPHRASE)
            response = json.loads(r6.text)
            MasterVariableContainer.master.slaves[str(id)][9] = response['Temperature']


        except:
            del MasterVariableContainer.master.slaves[id]
            return "Error while pinging slave"

        return jsonify({"id": id})


@MasterSocketListener.app.route("/getLoadingStatus", methods=["GET"])
def get_loading_status():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        finished_slaves = sum(t.slave_finished for t in MasterVariableContainer.assign_request_threads)
        return jsonify({"keyphrase_correct": True, "first_loading_done": MasterVariableContainer.first_loading_done,
                        "log_assignment_done": MasterVariableContainer.log_assignment_done, "slave_loading_requested": MasterVariableContainer.slave_loading_requested,
                        "slaves_count": len(MasterVariableContainer.master.slaves), "finished_slaves": finished_slaves})

    return jsonify({"keyphrase_correct": False})

@MasterSocketListener.app.route("/doLogAssignment", methods=["GET"])
def do_log_assignment():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        MasterVariableContainer.master.check_slaves()
        MasterVariableContainer.master.do_assignment()
        MasterVariableContainer.master.make_slaves_load()

    return jsonify({})

@MasterSocketListener.app.route("/checkSlaves", methods=["GET"])
def check_slaves():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        MasterVariableContainer.master.check_slaves()

    return jsonify({})


@MasterSocketListener.app.route("/getSlavesList", methods=["GET"])
def get_slaves_list():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        return jsonify({"slaves": MasterVariableContainer.master.slaves})
    return jsonify({})

@MasterSocketListener.app.route("/getSlavesList2", methods=["GET"])
def get_slaves_list2():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        return str(MasterVariableContainer.master.slaves.keys())
    return jsonify({})

@MasterSocketListener.app.route("/getSublogsId", methods=["GET"])
def get_sublogs_id():
    keyphrase = request.args.get('keyphrase', type=str)
    if keyphrase == configuration.KEYPHRASE:
        return jsonify({"sublogs_id": MasterVariableContainer.master.sublogs_id})
    return jsonify({})


@MasterSocketListener.app.route("/getSublogsCorrespondence", methods=["GET"])
def get_sublogs_correspondence():
    keyphrase = request.args.get('keyphrase', type=str)
    if keyphrase == configuration.KEYPHRASE:
        return jsonify({"sublogs_correspondence": MasterVariableContainer.master.sublogs_correspondence})
    return jsonify({})

@MasterSocketListener.app.route("/setFilters", methods=["POST"])
def set_filters():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)
    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    try:
        filters = json.loads(request.data)["filters"]
    except:
        filters = json.loads(request.data.decode('utf-8'))["filters"]
    if keyphrase == configuration.KEYPHRASE:
        MasterVariableContainer.master.set_filter(session, process, filters, use_transition, no_samples)
    return jsonify({})


@MasterSocketListener.app.route("/doCaching", methods=["GET"])
def do_caching():
    keyphrase = request.args.get('keyphrase', type=str)
    process = request.args.get('process', type=str)
    session = request.args.get('session', type=str)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        res = MasterVariableContainer.master.do_caching(session, process, use_transition, no_samples)

    return jsonify({})

@MasterSocketListener.app.route("/calculateDfg", methods=["GET"])
def calculate_dfg():
    keyphrase = request.args.get('keyphrase', type=str)
    process = request.args.get('process', type=str)
    session = request.args.get('session', type=str)
    attribute_key = request.args.get('attribute_key', type=str, default=xes.DEFAULT_NAME_KEY)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        overall_dfg = MasterVariableContainer.master.calculate_dfg(session, process, use_transition, no_samples, attribute_key)

        return jsonify({"dfg": overall_dfg})

    return jsonify({})


@MasterSocketListener.app.route("/calculatePerformanceDfg", methods=["GET"])
def calculate_performance_dfg():
    keyphrase = request.args.get('keyphrase', type=str)
    process = request.args.get('process', type=str)
    session = request.args.get('session', type=str)
    attribute_key = request.args.get('attribute_key', type=str, default=xes.DEFAULT_NAME_KEY)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        overall_dfg = MasterVariableContainer.master.calculate_performance_dfg(session, process, use_transition, no_samples, attribute_key)

        return jsonify({"dfg": overall_dfg})

    return jsonify({})


@MasterSocketListener.app.route("/calculateCompositeObj", methods=["GET"])
def calculate_composite_obj():
    keyphrase = request.args.get('keyphrase', type=str)
    process = request.args.get('process', type=str)
    session = request.args.get('session', type=str)
    attribute_key = request.args.get('attribute_key', type=str, default=xes.DEFAULT_NAME_KEY)
    performance_required = request.args.get('performance_required', type=str, default="False")
    if performance_required == "True":
        performance_required = True
    else:
        performance_required = False

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        overall_obj = MasterVariableContainer.master.calculate_composite_obj(session, process, use_transition, no_samples, attribute_key, performance_required=performance_required)

        return jsonify({"obj": overall_obj})

    return jsonify({})


@MasterSocketListener.app.route("/getEndActivities", methods=["GET"])
def calculate_end_activities():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)
    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        overall_ea = MasterVariableContainer.master.get_end_activities(session, process, use_transition, no_samples)

        return jsonify({"end_activities": overall_ea})

    return jsonify({})


@MasterSocketListener.app.route("/getStartActivities", methods=["GET"])
def calculate_start_activities():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)
    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        overall_sa = MasterVariableContainer.master.get_start_activities(session, process, use_transition, no_samples)

        return jsonify({"start_activities": overall_sa})
    return jsonify({"start_activities": {}})


@MasterSocketListener.app.route("/getAttributeValues", methods=["GET"])
def calculate_attribute_values():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)
    attribute_key = request.args.get('attribute_key', type=str, default=xes.DEFAULT_NAME_KEY)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        values = MasterVariableContainer.master.get_attribute_values(session, process, use_transition, no_samples, attribute_key)

        return jsonify({"values": values})

    return jsonify({})


@MasterSocketListener.app.route("/getAttributesNames", methods=["GET"])
def calculate_attributes_names():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        names = MasterVariableContainer.master.get_attributes_names(session, process, use_transition, no_samples)

        return jsonify({"names": names})
    return jsonify({"names": {}})


@MasterSocketListener.app.route("/getLogSummary", methods=["GET"])
def calculate_log_summary():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        summary = MasterVariableContainer.master.get_log_summary(session, process, use_transition, no_samples)

        return jsonify({"summary": summary})
    return jsonify({"summary": {}})


@MasterSocketListener.app.route("/getVariants", methods=["GET"])
def get_variants():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)
    max_no_ret_items = request.args.get(PARAMETER_NUM_RET_ITEMS, type=int, default=DEFAULT_MAX_NO_RET_ITEMS)

    if keyphrase == configuration.KEYPHRASE:
        variants = MasterVariableContainer.master.get_variants(session, process, use_transition, no_samples, max_ret_items=max_no_ret_items)

        return jsonify(variants)
    return jsonify({"variants": [], "events": 0, "cases": 0})


@MasterSocketListener.app.route("/getCases", methods=["GET"])
def get_cases():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)
    max_no_ret_items = request.args.get(PARAMETER_NUM_RET_ITEMS, type=int, default=DEFAULT_MAX_NO_RET_ITEMS)

    if keyphrase == configuration.KEYPHRASE:
        cases = MasterVariableContainer.master.get_cases(session, process, use_transition, no_samples, max_ret_items=max_no_ret_items)

        return jsonify(cases)
    return jsonify({"cases_list": [], "events": 0, "cases": 0})


@MasterSocketListener.app.route("/getEvents", methods=["GET"])
def get_events():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)
    case_id = request.args.get('case_id', type=str)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        events = MasterVariableContainer.master.get_events(session, process, use_transition, no_samples, case_id)

        return jsonify({"events": events})

    return jsonify({})


@MasterSocketListener.app.route("/getEventsPerDotted", methods=["GET"])
def get_events_per_dotted():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)
    max_no_ret_items = request.args.get(PARAMETER_NUM_RET_ITEMS, type=int, default=DEFAULT_MAX_NO_RET_ITEMS)

    attribute1 = request.args.get("attribute1", type=str)
    attribute2 = request.args.get("attribute2", type=str)
    attribute3 = request.args.get("attribute3", type=str, default=None)

    if keyphrase == configuration.KEYPHRASE:
        ret = MasterVariableContainer.master.get_events_per_dotted(session, process, use_transition, no_samples, attribute1, attribute2, attribute3, max_ret_items=max_no_ret_items)

        return jsonify({"traces": ret[0], "types": ret[1], "attributes": ret[2], "third_unique_values": ret[3]})

    return jsonify({})


@MasterSocketListener.app.route("/getEventsPerTime", methods=["GET"])
def get_events_per_time():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)
    max_no_ret_items = request.args.get(PARAMETER_NUM_RET_ITEMS, type=int, default=DEFAULT_MAX_NO_RET_ITEMS)

    if keyphrase == configuration.KEYPHRASE:
        points = MasterVariableContainer.master.get_events_per_time(session, process, use_transition, no_samples, max_ret_items=max_no_ret_items)

        return jsonify({"points": points})

    return jsonify({})


@MasterSocketListener.app.route("/getCaseDuration", methods=["GET"])
def get_case_duration():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)
    max_no_ret_items = request.args.get(PARAMETER_NUM_RET_ITEMS, type=int, default=DEFAULT_MAX_NO_RET_ITEMS)

    if keyphrase == configuration.KEYPHRASE:
        points = MasterVariableContainer.master.get_case_duration(session, process, use_transition, no_samples, max_ret_items=max_no_ret_items)

        return jsonify({"points": points})

    return jsonify({})


@MasterSocketListener.app.route("/getNumericAttributeValues", methods=["GET"])
def get_numeric_attribute_values():
    process = request.args.get('process', type=str)
    keyphrase = request.args.get('keyphrase', type=str)
    session = request.args.get('session', type=str)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)
    max_no_ret_items = request.args.get(PARAMETER_NUM_RET_ITEMS, type=int, default=DEFAULT_MAX_NO_RET_ITEMS)

    attribute_key = request.args.get("attribute_key", type=str)

    if keyphrase == configuration.KEYPHRASE:
        points = MasterVariableContainer.master.get_numeric_attribute_values(session, process, use_transition, no_samples, attribute_key, max_ret_items=max_no_ret_items)

        return jsonify({"points": points})

    return jsonify({})

@MasterSocketListener.app.route("/getRunningProcesses", methods=["GET"])
def get_running_processes():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        points = MasterVariableContainer.master.get_running_processes()
        return jsonify({"processes": points})

    return jsonify({})

@MasterSocketListener.app.route("/getOS", methods=["GET"])
def get_OS():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        points = MasterVariableContainer.master.get_OS()
        return jsonify({"OS": points})

    return jsonify({})

@MasterSocketListener.app.route("/getCPU", methods=["GET"])
def get_CPU():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        points = MasterVariableContainer.master.get_CPU()
        return jsonify({"CPUpct": points})

    return jsonify({})

@MasterSocketListener.app.route("/getCPUload", methods=["GET"])
def get_CPUload():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        points = MasterVariableContainer.master.get_CPUload()
        return jsonify({"CPUload": points})

    return jsonify({})

@MasterSocketListener.app.route("/getcurrentPIDinfo", methods=["GET"])
def get_current_PID_info():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        points = MasterVariableContainer.master.get_current_PID_info()
        return jsonify({"PID": points})

    return jsonify({})

@MasterSocketListener.app.route("/getMemory", methods=["GET"])
def get_memory():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        points = MasterVariableContainer.master.get_memory()
        return jsonify({"Memory": points})

    return jsonify({})

@MasterSocketListener.app.route("/getTemperature", methods=["GET"])
def get_temp():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        points = MasterVariableContainer.master.get_temperature()
        return jsonify({"Temperature": points})

    return jsonify({})

@MasterSocketListener.app.route("/getDiskUsage", methods=["GET"])
def get_diskusage():
    keyphrase = request.args.get('keyphrase', type=str)

    if keyphrase == configuration.KEYPHRASE:
        points = MasterVariableContainer.master.get_disk_usage()
        return jsonify({"Disk Usage": points})

    return jsonify({})

@MasterSocketListener.app.route("/simpleIMD", methods=["GET"])
def simple_IMD():
    keyphrase = request.args.get('keyphrase', type=str)
    process = request.args.get('process', type=str)
    session = request.args.get('session', type=str)
    attribute_key = request.args.get('attribute_key', type=str, default=xes.DEFAULT_NAME_KEY)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        discoverimdfb = MasterVariableContainer.master.simple_imd(session, process, use_transition, no_samples, attribute_key)
        #return discoverimdfb
        return discoverimdfb
    return jsonify({"Process Tree": {}})

@MasterSocketListener.app.route("/distributedIMD", methods=["GET"])
def distr_IMD():
    keyphrase = request.args.get('keyphrase', type=str)
    process = request.args.get('process', type=str)
    session = request.args.get('session', type=str)
    attribute_key = request.args.get('attribute_key', type=str, default=xes.DEFAULT_NAME_KEY)

    use_transition = request.args.get(PARAMETER_USE_TRANSITION, type=str, default=str(DEFAULT_USE_TRANSITION))
    no_samples = request.args.get(PARAMETER_NO_SAMPLES, type=int, default=DEFAULT_MAX_NO_SAMPLES)

    if keyphrase == configuration.KEYPHRASE:
        discoverimdfb = MasterVariableContainer.master.distr_imd(session, process, use_transition, no_samples, attribute_key)
        #return discoverimdfb
        return discoverimdfb
    return jsonify({"Process Tree": {}})
