from threading import Thread


class BasicMasterRequest(Thread):
    def __init__(self, target_host, target_port, content):
        Thread.__init__(self)

    def run(self):
        pass
