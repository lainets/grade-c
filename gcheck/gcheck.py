#!/usr/bin/env python3

import os
import sys
import subprocess
import traceback
import argparse
from time import perf_counter
from pathlib import Path

from report_parser import Report, Type
from beautify import Beautify

def grading_script_error(str):
    print(str)

def give_points(points, max_points):
    if max_points is None:
        max_points = 1
    with open("/feedback/points", "w") as f:
        f.write(f"{round(points)}/{max_points}")

class Failed(BaseException):
    def __init__(self, msg, error):
        self.msg = msg
        self.error = error

    def __str__(self):
        return str(self.msg)

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
        self.beautify = None
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
            if self.beautify is not None:
                try:
                    with open("/feedback/out", "w") as f:
                        f.write(self.beautify.render("all.html", beautify=self.beautify, compile_output=grader.compile_output, valgrind_output=grader.valgrind_output, penalties=self.penalties).replace("\0", "\x00"))
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

def run(cmd, **kwargs):
    return " ".join(cmd), subprocess.run(cmd, capture_output=True, **kwargs)

def load_list(config, key, additions=[], default=[]):
    data = config.get(key, default)
    if isinstance(data, str):
        data = data.split(" ")
        data = [d for d  in data if d != ""]
    return data + additions

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

def has_warning(process):
    in_stdout = process.stdout is not None and ": warning:" in process.stdout.decode('utf-8')
    in_stderr = process.stderr is not None and ": warning:" in process.stderr.decode('utf-8')
    return in_stdout or in_stderr

try:
    config = {
        "penalty_type": "multiplicative",
        "max_points": None,
        "penalties": {
        },
        "valgrind": False,
        "valgrind_options": [
            "--track-origins=yes",
            "--leak-check=full",
        ]
    }

    if Path("/exercise/gcheck.yaml").exists():
        import yaml
        with open("/exercise/gcheck.yaml") as f:
            config.update(yaml.safe_load(f))
    elif Path("/exercise/gcheck.json").exists():
        import json
        with open("/exercise/gcheck.json") as f:
            config.update(json.load(f))
except:
    pass

with Grader(config["max_points"], config["penalty_type"]) as grader:
    env = {}
    with open("/gcheck.env") as f:
        lines = f.readlines()
        pairs = [line.strip().split("=", 1) for line in lines]
        pairs = [p for p in pairs if len(p) == 2]
        env = {k: v for k, v in pairs}

    testsources = []
    if config.get("testsource", None):
        if Path(config["testsource"]).is_absolute():
            testsources = [config["testsource"]]
        else:
            testsources = [str(Path("/exercise") / config["testsource"])]
    elif config.get("testsourcedir", "/exercise"):
        path = Path(config.get("testsourcedir", "/exercise"))
        if not path.is_absolute():
            path = Path("/exercise") / path
        for file in os.listdir(path):
            if not file.endswith(".cpp"):
                continue
            file = path / file
            if file.is_file():
                testsources.append(str(file))

    if not testsources:
        raise Failed("Problem with exercise configuration. Please contact course staff.", "No test sources found. Make sure the exercise config is correct.")

    includedirs = load_list(config, "includedirs")
    includedirs = [d if Path(d).is_absolute() else "/exercise/" + d for d in includedirs]
    includedirs = ["-I" + d for d in includedirs]

    submission_files = []
    for dirpath, dirnames, filenames in os.walk("/submission/user"):
        path = Path(dirpath)
        submission_files.extend(str(path / f) for f in filenames)

    submission_files_c = [f for f in submission_files if f.endswith(".c")]
    submission_files_cpp = [f for f in submission_files if f.endswith(".cpp")]

    TESTCPPFLAGS = load_list(config, "TESTCPPFLAGS", ["-c", "-isystem", env["GCHECK_DIR"]] + includedirs)
    TESTCXXFLAGS = load_list(config, "TESTCXXFLAGS", [f"-I{env['GCHECK_INCLUDE_DIR']}"])
    CPPFLAGS = load_list(config, "CPPFLAGS", ["-c"] + includedirs, env['CPPFLAGS'])
    CFLAGS = load_list(config, "CFLAGS", default=env['CFLAGS'])
    CXXFLAGS = load_list(config, "CXXFLAGS", default=env['CXXFLAGS'])
    LDFLAGS = load_list(config, "LDFLAGS", [f"-L{env['GCHECK_LIB_DIR']}"], env['LDFLAGS'])
    LDLIBS = load_list(config, "LDLIBS", [f"-l{env['GCHECK_LIB']}"], env['LDLIBS'])

    if not any(p.strip().startswith("-std=") for p in TESTCXXFLAGS):
        TESTCXXFLAGS = TESTCXXFLAGS + ["-std=c++17"]
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

    TESTOBJECTS = []
    for cppfile in testsources:
        outfile = cppfile[:-4] + ".o"
        outfile = "/submission/user/" + str(Path(outfile).name)
        cmd, process = run(["g++", *TESTCPPFLAGS, *TESTCXXFLAGS, cppfile, "-o", outfile])
        compile_error = compile_error or process.returncode != 0
        compile_warning = compile_warning or has_warning(process)
        grader.compile_output += cmd + "\n"
        grader.compile_output += process_output(process)
        TESTOBJECTS.append(outfile)

    cmd, process = run(["g++", *TESTOBJECTS, *CPPOBJECTS, *COBJECTS, *LDFLAGS, *LDLIBS, "-o", "test"])
    compile_error = compile_error or process.returncode != 0
    compile_warning = compile_warning or has_warning(process)
    grader.compile_output += cmd + "\n"
    grader.compile_output += process_output(process)

    if compile_warning and "warning" in config["penalties"]:
        grader.addPenalty('warning', config['penalties']['warning'])

    if not compile_error:
        if config["valgrind"]:
            valgrind_filename = "/valgrind_out.txt"
            cmd, process = run(["valgrind", "-q", "--trace-children=yes", "--log-file=" + valgrind_filename] + config["valgrind_options"] + ["./test", "--safe", "--json", "/output.json"])

            try:
                with open(valgrind_filename, 'r') as f:
                    grader.valgrind_output = f.read()
            except Exception as e:
                raise Failed("Error opening valgrind output. Please contact course staff if this persists.", f"Error opening valgrind output.\n{str(e)}:\n{traceback.format_exc()}")
        else:
            cmd, process = run(["./test", "--safe", "--json", "/output.json"])

        grader.compile_output += cmd + "\n"
        grader.compile_output += process_output(process)

        try:
            report = Report("/output.json")
        except Exception as e:
            grader.beautify = Beautify(Report(), "/templates")
            grader.compile_output += "\nFailed to open test output\n"
            grading_script_error(f"Error opening test output.\n{str(e)}:\n{traceback.format_exc()}\n")
        else:
            """for t in report.tests:
                for r in t.results:
                    for c in r.cases:
                        c.output.string += '\0'"""
            if grader.max_points is not None:
                report.scale_points(grader.max_points)

            grader.addPoints(report.points)

            try:
                grader.beautify = Beautify(report, "/templates")
            except Exception as e:
                raise Failed("Error rendering test output. Please contact course staff if this persists.", f"Error rendering test output. (initializing Beautify)\n{str(e)}:\n{traceback.format_exc()}")
    else:
        grader.beautify = Beautify(Report(), "/templates")
