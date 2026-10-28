"""wine2e probe (NOT for main): replay the TUI-gateway turn and dump every event payload plus
periodic all-thread tracebacks of the tui_gateway child, so a hung agent build shows where."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.e2e.core.windows._helpers import REPO_ROOT, make_home
from tests.e2e.core.windows._rpc import StdioGateway
from tests.fakes.fake_llm_provider import FakeLLMServer, Text

pytestmark = [pytest.mark.platforms("windows"), pytest.mark.integration]

_SITE = "import faulthandler, sys\nfaulthandler.dump_traceback_later(40, repeat=True, file=sys.stderr)\n"


def test_probe_tui_gateway_turn(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    (site / "sitecustomize.py").write_text(_SITE, encoding="utf-8")
    with FakeLLMServer([Text("probe reply TAGP")]) as srv:
        home = make_home(tmp_path, srv.base_url)
        home.extra_env["PYTHONPATH"] = f"{site}{os.pathsep}{REPO_ROOT}"
        gw = StdioGateway(home)
        err = ""
        try:
            try:
                gw.turn("hello TAGP")
            except AssertionError as e:
                err = str(e)[:500]
        finally:
            gw.close()
        events = "\n".join(json.dumps(ev)[:800] for ev in gw.events if ev.get("type") != "gateway.ready")
        stderr = gw.stderr
        reqs = len(srv.main_requests())
    raise AssertionError(
        f"PROBE err={err!r} main_requests={reqs}\n--- EVENTS ---\n{events}\n"
        f"--- STDERR ({len(stderr)} chars) ---\n{stderr[:60000]}")
