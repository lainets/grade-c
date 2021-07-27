from typing import Optional

from report_parser import Report
from beautify import Beautify

from util import grading_script_error, Failed, run, process_output, read_env, RunnerBase

class Runner(RunnerBase):
    def __init__(self):
        self.report = Report()

    @property
    def allow_zero_test_sources(self):
        return False

    def get_env(self, env):
        return read_env("/gcheck/gcheck.env")

    def additional_flags(self, env, config):
        return {
            "TESTCPPFLAGS": ["-isystem", env["GCHECK_DIR"]],
            "TESTCXXFLAGS": [f"-I{env['GCHECK_INCLUDE_DIR']}"],
            "LDFLAGS": [f"-L{env['GCHECK_LIB_DIR']}"],
            "LDLIBS": [f"-l{env['GCHECK_LIB']}"],
        }

    def run(self, cmd, config, max_points: Optional[int]):
        cmd, process = run(cmd + ["--json", "/output.json"])

        output = cmd + "\n"
        output += process_output(process)

        try:
            self.report = Report("/output.json")
        except Exception as e:
            raise Failed("Error opening test output. Please contact course staff if this persists.", f"Error opening test output.\n{str(e)}:\n{traceback.format_exc()}\n")

        if max_points:
            self.report.scale_points(max_points)

        return output

    def render(self, **kwargs):
        try:
            beautify = Beautify(self.report, "/gcheck/templates")
        except Exception as e:
            raise Failed("Error rendering test output. Please contact course staff if this persists.", f"Error rendering test output. (initializing Beautify)\n{str(e)}:\n{traceback.format_exc()}")

        return beautify.render("all.html", beautify=beautify, **kwargs)

    def points(self):
        return self.report.points

    def max_points(self) -> int:
        return round(self.report.max_points)
