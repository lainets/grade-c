import subprocess
from typing import Optional

def grading_script_error(str):
    print(str)

class Failed(BaseException):
    def __init__(self, msg, error):
        self.msg = msg
        self.error = error

    def __str__(self):
        return str(self.msg)

class RunnerBase:
    @property
    def allow_zero_test_sources(self):
        return True

    def get_env(self, env):
        return env

    def additional_flags(self, env, config):
        return {}

    def run(self, cmd, config, max_points: Optional[int]):
        raise NotImplementedError()

    def render(self, **kwargs):
        raise NotImplementedError()

    def points(self):
        raise NotImplementedError()

    def max_points(self) -> int:
        raise NotImplementedError()

def run(cmd, **kwargs):
    return " ".join(cmd), subprocess.run(cmd, capture_output=True, **kwargs)

def process_output(process):
    output = ""
    if process.stdout is not None:
        output += process.stdout.decode('UTF-8')
    if process.stderr is not None:
        if output:
            output += "\n"
        output += process.stderr.decode('UTF-8')
    if output:
        output += "\n"
    return output

def read_env(filename):
    env = {}
    with open(filename) as f:
        lines = f.readlines()
        pairs = [line.strip().split("=", 1) for line in lines]
        pairs = [p for p in pairs if len(p) == 2]
        env = {k: v for k, v in pairs}
    return env

def load_list(config, key, additions=[], default=[]):
    def listify(data):
        if isinstance(data, str):
            data = data.split(" ")
            data = [d for d in data if d != ""]
        return data

    data = config.get(key, default)
    data = listify(data)

    minusdata = config.get(key+"-", None)
    if minusdata is not None:
        minusdata = listify(minusdata)
        data = [d for d in data if d not in minusdata]

    adddata = config.get(key+"+", None)
    if adddata is not None:
        adddata = listify(adddata)
        data += adddata

    return data + additions
