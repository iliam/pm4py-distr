from pm4pydistr.local_wrapper.distr_log_obj import DistrLogObj
from pm4pydistr.log_handlers import parquet as parquet_handler
from pm4py.objects.log.importer.parquet import factory as parquet_factory
from pathlib import Path

class ClassicDistrLogObject(DistrLogObj):
    def __init__(self, distr_log_path, parameters=None):
        DistrLogObj.__init__(self, distr_log_path, parameters=parameters)

    def get_list_logs(self):
        lp = parquet_factory.get_list_parquet(self.distr_log_path)

        return [Path(log).name for log in lp]

    def calculate_dfg(self, parameters=None):
        list_logs = self.get_list_logs()
        dfg = parquet_handler.calculate_dfg(".", self.distr_log_path, list_logs, parameters=parameters)
        return {(x.split("@@")[0], x.split("@@")[1]): dfg[x] for x in dfg}

def apply(path, parameters=None):
    if parameters is None:
        parameters = {}

    return ClassicDistrLogObject(path, parameters=parameters)
