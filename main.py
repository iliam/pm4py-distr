import os
from pm4pydistr.configuration import PYTHON_PATH
from threading import Thread

import time
import socket

class ExecutionThread(Thread):
    def __init__(self, command):
        self.command = command
        Thread.__init__(self)

    def run(self):
        os.system(self.command)


host = socket.gethostbyname(socket.gethostname())
t1 = ExecutionThread(PYTHON_PATH + " launch.py --type master --conf master --port 5001")
t1.start()
time.sleep(0.5)
t2 = ExecutionThread(
    PYTHON_PATH + " launch.py --type slave --conf slave1 --port 5002 --master-host " + host + " --master-port 5001")
t2.start()
t3 = ExecutionThread(
    PYTHON_PATH + " launch.py --type slave --conf slave2 --port 5003 --master-host " + host + " --master-port 5001")
t3.start()
t4 = ExecutionThread(
    PYTHON_PATH + " launch.py --type slave --conf slave3 --port 5004 --master-host " + host + " --master-port 5001")
t4.start()
