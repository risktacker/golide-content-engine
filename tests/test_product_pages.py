"""owner 2026-11-25: a company is shown on its own site; a GitHub repo that only shares the name is never shown."""
import io
import json
from unittest import mock

from golide_engine.engine import source_capture


def _answers(table):
    def urlopen(req, timeout=20):
        url = req.full_url
        for part, body in table.items():
            if part in url:
                return io.BytesIO(json.dumps(body).encode())
        raise OSError("offline")
    return urlopen


WIKI_TESLA = {"search": [{"id": "Q1", "label": "Tesla Energy"}]}
ENT_TESLA = {"entities": {"Q1": {"claims": {"P856": [{"mainsnak": {"datavalue": {"value": "https://www.tesla.com/energy"}}}]}}}}
STRANGER = {"items": [{"name": "TeslaEnergy", "stargazers_count": 900, "homepage": "", "html_url": "https://github.com/someone/TeslaEnergy"}]}


def test_a_company_is_shown_on_its_own_site_not_a_stranger_repo():
    table = {"wbsearchentities": WIKI_TESLA, "EntityData/Q1": ENT_TESLA, "api.github.com": STRANGER}
    with mock.patch("urllib.request.urlopen", _answers(table)):
        out = source_capture.product_pages(["Tesla Energy"], set())
    assert [o["url"] for o in out] == ["https://www.tesla.com/energy"]


def test_a_named_repo_with_no_site_of_its_own_is_never_shown():
    with mock.patch("urllib.request.urlopen", _answers({"api.github.com": STRANGER})):
        assert source_capture.product_pages(["Tesla Energy"], set()) == []


def test_real_software_keeps_its_site_and_repo():
    repo = {"items": [{"name": "opencode", "stargazers_count": 30000, "homepage": "https://opencode.ai",
                       "html_url": "https://github.com/sst/opencode"}]}
    with mock.patch("urllib.request.urlopen", _answers({"api.github.com": repo})):
        out = source_capture.product_pages(["OpenCode"], set())
    assert [o["url"] for o in out] == ["https://opencode.ai", "https://github.com/sst/opencode"]
