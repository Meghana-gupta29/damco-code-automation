"""Pytest plugin: records one result row per test, keyed by test-case id (@pytest.mark.tc)."""
import json
import time

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "tc(id): links a test to a test-plan case id, e.g. TC-001")
    config._qa_rows = []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    out = yield
    rep = out.get_result()
    m = item.get_closest_marker("tc")
    if rep.when == "call" or (rep.when == "setup" and rep.outcome != "passed"):
        item.config._qa_rows.append({
            "tc": m.args[0] if m else None,
            "test": item.nodeid,
            "outcome": {"passed": "passed", "failed": "failed", "skipped": "skipped"}[rep.outcome],
            "duration_s": round(rep.duration, 3),
            "error": (rep.longreprtext[-1800:] if rep.outcome == "failed" else None),
            "phase": rep.when,
        })


def pytest_sessionfinish(session, exitstatus):
    path = session.config.getoption("--qa-results", default=None)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"suite": "api", "finished": time.time(), "rows": session.config._qa_rows}, f, indent=2)


def pytest_addoption(parser):
    parser.addoption("--qa-results", default=None, help="write QA results JSON here")
