import os
import logging
import time

from optparse import OptionParser
import sys
import signal
import json

try:
    import horovod.tensorflow as hvd
    from horovod.runner import gloo_run
    from horovod.runner.http.http_server import RendezvousServer
    from horovod.runner.common.util.hosts import get_host_assignments, parse_hosts
except (ModuleNotFoundError, ImportError) as e:
    logging.warn("Horovod is not installed. See README for instructions to install it")
    raise e

PORT_FILE_NAME_SUFFIX = "____HOROVOD_REDENVOUS_SERVER____"

def _driver_fn():
    global_rendezv = RendezvousServer(verbose=1)
    global_rendezv_port = global_rendezv.start()
    print("redezevous server started. port: " + str(global_rendezv_port))

    # 准备好相关 host 的地址，然后构建
    # worker_list = "localhost:1"
    hosts = parse_hosts(worker_list)
    host_alloc_plan = get_host_assignments(hosts, 1)
    print(host_alloc_plan)

    global_rendezv.init(host_alloc_plan)
    return (global_rendezv_port, host_alloc_plan)

def _get_host_plan_json(host_alloc_plan):
    hosts = []
    for plan in host_alloc_plan:
        hosts.append({
            "hostname": plan.hostname, 
            "rank": plan.rank,
            "local_rank": plan.local_rank,
            "cross_rank": plan.cross_rank,
            "size": plan.size,
            "local_size": plan.local_size,
            "cross_size": plan.cross_size
            })
    print(json.dumps(hosts))
    return json.dumps(hosts)

def _setOption():
    parser = OptionParser()
    parser.add_option(
        "-a", "--num_proc", dest="num_process", type="str", help="number process of training", default="1")
    parser.add_option(
        "-w", "--worker_list", dest="worker_list", type="str", help="worker list"
    )
    (options, args) = parser.parse_args(sys.argv)

    global worker_list
    worker_list = options.worker_list

def __port_file_path(port):
    path_dir = os.path.dirname(os.path.abspath(__file__))
    port_file_path = os.path.join(path_dir, str(port) + PORT_FILE_NAME_SUFFIX)
    return port_file_path


def create_port_file(port, host_alloc_plan):
    port_file = __port_file_path(port)
    logging.info("Creating port file %s", port_file)
    with open(__port_file_path(port), 'w') as fo:
        fo.write(_get_host_plan_json(host_alloc_plan))
        logging.info("Port file for %s created", port_file)
        pass


def delete_port_file(port):
    port_file = __port_file_path(port)
    logging.info("Deleting port file %s", port_file)
    try:
        os.remove(__port_file_path(port))
        logging.info("Port file %s deleted", port_file)
    except OSError:
        pass


def handle_exit(*args):
    try:
        logging.info("Closing redenvous server...")
        # todo: Close redenvous server.
        logging.info("Closed redenvous server")

        delete_port_file(port)
    except:
        logging.exception("Failed to close redenvous server")
        
    sys.exit(0)


if __name__ == '__main__':  
    try:  
        _setOption()
        global port
        (port, host_alloc_plan) = _driver_fn()
        create_port_file(port, host_alloc_plan)
        signal.signal(signal.SIGTERM, handle_exit)
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGILL, handle_exit)
    except:
        logging.exception("errors on staring horovod redenvous server")
        handle_exit()

    time.sleep(2000)
    handle_exit()