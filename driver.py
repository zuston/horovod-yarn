import os
import logging
import time

try:
    import horovod.tensorflow as hvd
    from horovod.runner import gloo_run
    from horovod.runner.http.http_server import RendezvousServer
    from horovod.runner.common.util.hosts import get_host_assignments, parse_hosts
except (ModuleNotFoundError, ImportError) as e:
    logging.warn("Horovod is not installed. See README for instructions to install it")
    raise e

logger = logging.getLogger("driver")

def _driver_fn():
    global_rendezv = RendezvousServer(verbose=1)
    global_rendezv_port = global_rendezv.start()
    print("redezevous server started. port: " + str(global_rendezv_port))

    # 准备好相关 host 的地址，然后构建
    worker_list = "localhost:1"
    hosts = parse_hosts(worker_list)
    host_alloc_plan = get_host_assignments(hosts, 1)
    print(host_alloc_plan)
    global_rendezv.init(host_alloc_plan)

    time.sleep(1000)

def main():
    _driver_fn()

if __name__ == '__main__':
    main()