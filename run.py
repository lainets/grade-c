#!/usr/bin/env python3

import os
import traceback
import argparse
from time import perf_counter
from pathlib import Path
import signal
from contextlib import contextmanager
from importlib.util import spec_from_file_location, module_from_spec
from typing import Type
from util import read_env

from beautify import Beautify
from report_parser import Report

from util import grading_script_error, Failed, run, process_output, read_env, RunnerBase, load_list

def give_points(points, max_points):
    if max_points is None:
        max_points = 1
    with open("/feedback/points", "w") as f:
        f.write(f"{round(points)}/{max_points}")

class Grader:
    multiplicative_types = ["multiplicative", "mult", "m"]
    cumulative_types = ["cumulative", "cum", "c"]
    def __init__(self, max_points, penalty_type = "multiplicative"):
        self.max_points = max_points
        self.fraction = 1 # fraction of points given due to penalties
        self.points = 0
        if penalty_type in Grader.multiplicative_types:
            self.penalty_type = "m"
        elif penalty_type in Grader.cumulative_types:
            self.penalty_type = "c"
        else:
            raise Exception(f"Unknown penalty_type. Allowed types: {', '.join(Grader.multiplicative_types + Grader.cumulative_types)}")

        self.compile_output = ""
        self.valgrind_output = None
        self.render = None
        self.penalties = {}

    def setPoints(self, points, max_points = None):
        if max_points is not None:
            self.max_points = max_points
        self.points = min(self.max_points, points)

    def addPoints(self, points, max_points = None):
        if max_points is None:
            max_points = self.max_points
        else:
            max_points = self.max_points + max_points
        self.setPoints(self.points + points, max_points)

    def addPenalty(self, name, penalty):
        if self.penalty_type == "m":
            self.fraction = max(0, min(1, self.fraction*(1-penalty)))
        else:
            self.fraction = max(0, min(1, self.fraction-penalty))
        if name == "warning":
            self.penalties["Warnings in compilation"] = penalty
        elif name == "valgrind":
            self.penalties["Valgrind warnings/errors"] = penalty
        else:
            self.penalties[name] = penalty

    def __enter__(self):
        return self

    def __exit__(self, typ, value, traceback):
        if grader.valgrind_output and len(grader.valgrind_output) > 0 and "valgrind" in config["penalties"]:
            grader.addPenalty("valgrind", config["penalties"]["valgrind"])

        if typ is None:
            if self.render is not None:
                try:
                    with open("/feedback/out", "w") as f:
                        f.write(self.render(compile_output=grader.compile_output, valgrind_output=grader.valgrind_output, penalties=self.penalties).replace("\0", "\1"))
                except Exception as e:
                    value = Failed("Error rendering test output. Please contact course staff if this persists.", f"Error rendering test output. (rendering Beautify)\n{str(e)}:\n{traceback.format_exc()}")
                    typ = Failed
            else:
                value = Failed("Error rendering test output. Please contact course staff if this persists.", f"Error rendering test output. (beautify is None)")
                typ = Failed

        if typ is not None:
            if typ != Failed:
                grading_script_error(f"{str(value)}:\n{traceback}")
                with open("/feedback/out", "w") as f:
                    f.write("Error in grading script. Please contact course staff if this persists.")
            else:
                grading_script_error(value.error)
                with open("/feedback/out", "w") as f:
                    f.write(value.msg)
            self.points = 0
        elif self.max_points is None:
            grading_script_error("max_points is None")
            self.points = 0

        give_points(self.points*self.fraction, self.max_points)

# the subprocess timeout doesn't seem to work correctly for long timeouts
# so we use signals
def timeout_handler(signum, frame):
    raise Failed("Submission timed out. Check that there are no infinite loops", f"Submission timed out.\ntimeout: {config['timeout']}")
signal.signal(signal.SIGALRM, timeout_handler)

@contextmanager
def Timeout(timeout):
    if timeout is None:
        signal.alarm(0)
    elif timeout == 0:
        timeout_handler(None, None)
    else:
        signal.alarm(timeout)

        try:
            yield
        finally:
            signal.alarm(0)


def has_warning(process):
    in_stdout = process.stdout is not None and ": warning:" in process.stdout.decode('utf-8')
    in_stderr = process.stderr is not None and ": warning:" in process.stderr.decode('utf-8')
    return in_stdout or in_stderr

config = {
    "runner": "/gcheck/run.py",
    "penalty_type": "multiplicative",
    "max_points": None,
    "penalties": {
    },
    "valgrind": False,
    "valgrind_options": [
        "--track-origins=yes",
        "--leak-check=full",
    ],
    "timeout": 180,
}

try:
    if Path("/exercise/gcheck.yaml").exists():
        import yaml
        with open("/exercise/gcheck.yaml") as f:
            config.update(yaml.safe_load(f))
    elif Path("/exercise/gcheck.json").exists():
        import json
        with open("/exercise/gcheck.json") as f:
            config.update(json.load(f))
except Exception as e:
    grading_script_error(f"Failed to read gcheck config file:\n{traceback}")

    with open("/feedback/out", "w") as f:
        f.write("Error in grading script. Please contact course staff if this persists.")
    give_points(0, 1)
    exit(0)

def absolute_path(path, default_root):
    path = Path(path)
    if path.is_absolute():
        return path
    else:
        return default_root / path

def import_runner(path) -> Type[RunnerBase]:
    path = Path(path)
    module_name = path.stem

    spec = spec_from_file_location(module_name, path)
    if not spec:
        raise Failed("Problem with exercise configuration. Please contact course staff.", "Runner source file not found")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    return getattr(module, "Runner")


with Grader(config["max_points"], config["penalty_type"]) as grader:
    runner_cls = import_runner(config["runner"])
    runner = runner_cls()

    env = read_env("/compile.env")
    env = runner.get_env(env)

    testsources = []
    if "testsource" in config:
        paths = load_list(config, "testsource")
        testsources = [str(absolute_path(f, "/exercise")) for f in paths]

    if len(testsources) == 0 or "testsourcedir" in config:
        paths = load_list(config, "testsourcedir", ["/exercise"])
        for path in paths:
            path = absolute_path(path, "/exercise")
            for file in os.listdir(path):
                if file.endswith(".cpp") or file.endswith(".c"):
                    file = path / file
                    if file.is_file():
                        testsources.append(str(file))

    if not runner.allow_zero_test_sources and not testsources:
        raise Failed("Problem with exercise configuration. Please contact course staff.", "No test sources found. Make sure the exercise config is correct.")

    testsources_c = [f for f in testsources if f.endswith(".c")]
    testsources_cpp = [f for f in testsources if f.endswith(".cpp")]

    includedirs = load_list(config, "includedirs")
    includedirs = [d if Path(d).is_absolute() else "/exercise/" + d for d in includedirs]
    includedirs = ["-I" + d for d in includedirs]

    submission_files = []
    for dirpath, dirnames, filenames in os.walk("/submission/user"):
        path = Path(dirpath)
        submission_files.extend(str(path / f) for f in filenames)

    submission_files_c = [f for f in submission_files if f.endswith(".c")]
    submission_files_cpp = [f for f in submission_files if f.endswith(".cpp")]

    add_flags = runner.additional_flags(env, config)

    TESTCPPFLAGS = load_list(config, "TESTCPPFLAGS", ["-c"] + add_flags.get("TESTCPPFLAGS", []) + includedirs)
    TESTCFLAGS = load_list(config, "TESTCFLAGS", add_flags.get("TESTCFLAGS", []), env['TESTCFLAGS'])
    TESTCXXFLAGS = load_list(config, "TESTCXXFLAGS", add_flags.get("TESTCXXFLAGS", []))
    CPPFLAGS = load_list(config, "CPPFLAGS", ["-c"] + add_flags.get("CPPFLAGS", []) + includedirs, env['CPPFLAGS'])
    CFLAGS = load_list(config, "CFLAGS", add_flags.get("CFLAGS", []) + [], env['CFLAGS'])
    CXXFLAGS = load_list(config, "CXXFLAGS", add_flags.get("CXXFLAGS", []), env['CXXFLAGS'])
    LDFLAGS = load_list(config, "LDFLAGS", add_flags.get("LDFLAGS", []), env['LDFLAGS'])
    LDLIBS = load_list(config, "LDLIBS", add_flags.get("LDLIBS", []), env['LDLIBS'])

    if not any(p.strip().startswith("-std=") for p in TESTCXXFLAGS):
        TESTCXXFLAGS = TESTCXXFLAGS + ["-std=c++17"]
    if not any(p.strip().startswith("-std=") for p in TESTCFLAGS):
        TESTCFLAGS = TESTCFLAGS + ["-std=c99"]
    if not any(p.strip().startswith("-std=") for p in CXXFLAGS):
        CXXFLAGS = CXXFLAGS + ["-std=c++17"]
    if not any(p.strip().startswith("-std=") for p in CFLAGS):
        CFLAGS = CFLAGS + ["-std=c99"]

    compile_error = False
    compile_warning = False

    COBJECTS = []
    for cfile in submission_files_c:
        cmd, process = run(["gcc", *CPPFLAGS, *CFLAGS, cfile, "-o", cfile[:-2] + ".o"])
        compile_error = compile_error or process.returncode != 0
        compile_warning = compile_warning or has_warning(process)
        grader.compile_output += cmd + "\n"
        grader.compile_output += process_output(process)
        COBJECTS.append(cfile[:-2] + ".o")

    CPPOBJECTS = []
    for cppfile in submission_files_cpp:
        cmd, process = run(["g++", *CPPFLAGS, *CXXFLAGS, cppfile, "-o", cppfile[:-4] + ".o"])
        compile_error = compile_error or process.returncode != 0
        compile_warning = compile_warning or has_warning(process)
        grader.compile_output += cmd + "\n"
        grader.compile_output += process_output(process)
        CPPOBJECTS.append(cppfile[:-4] + ".o")

    TESTCOBJECTS = []
    for cfile in testsources_c:
        outfile = cfile[:-2] + ".o"
        outfile = "/submission/user/" + str(Path(outfile).name)
        cmd, process = run(["gcc", *TESTCPPFLAGS, *TESTCFLAGS, cfile, "-o", outfile])
        compile_error = compile_error or process.returncode != 0
        compile_warning = compile_warning or has_warning(process)
        grader.compile_output += cmd + "\n"
        grader.compile_output += process_output(process)
        TESTCOBJECTS.append(outfile)

    TESTCPPOBJECTS = []
    for cppfile in testsources_cpp:
        outfile = cppfile[:-4] + ".o"
        outfile = "/submission/user/" + str(Path(outfile).name)
        cmd, process = run(["g++", *TESTCPPFLAGS, *TESTCXXFLAGS, cppfile, "-o", outfile])
        compile_error = compile_error or process.returncode != 0
        compile_warning = compile_warning or has_warning(process)
        grader.compile_output += cmd + "\n"
        grader.compile_output += process_output(process)
        TESTCPPOBJECTS.append(outfile)

    cmd, process = run(["g++", *TESTCPPOBJECTS, *TESTCOBJECTS, *CPPOBJECTS, *COBJECTS, *LDFLAGS, *LDLIBS, "-o", "test"])
    compile_error = compile_error or process.returncode != 0
    compile_warning = compile_warning or has_warning(process)
    grader.compile_output += cmd + "\n"
    grader.compile_output += process_output(process)

    if compile_warning and "warning" in config["penalties"]:
        grader.addPenalty('warning', config['penalties']['warning'])

    if not compile_error:
        grader.render = runner.render
        if config["valgrind"]:
            valgrind_filename = "/valgrind_out.txt"

            with Timeout(config["timeout"]):
                output = runner.run(["valgrind", "-q", "--trace-children=yes", "--log-file=" + valgrind_filename] + config["valgrind_options"] + ["./test"], config, grader.max_points)

            try:
                with open(valgrind_filename, 'r') as f:
                    grader.valgrind_output = f.read()
            except Exception as e:
                raise Failed("Error opening valgrind output. Please contact course staff if this persists.", f"Error opening valgrind output.\n{str(e)}:\n{traceback.format_exc()}")
        else:
            with Timeout(config["timeout"]):
                output = runner.run(["./test"], config, grader.max_points)

        grader.compile_output += output + "\n"

        grader.setPoints(runner.points(), runner.max_points())
    else:
        def default_renderer(**kwargs):
            beautify = Beautify(Report(), "/gcheck/templates")
            return beautify.render("all.html", beautify=beautify, **kwargs)
        grader.render = default_renderer
