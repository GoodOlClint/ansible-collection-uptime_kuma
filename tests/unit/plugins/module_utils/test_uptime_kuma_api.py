# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/module_utils/uptime_kuma_api.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from enum import Enum
import threading
from unittest.mock import MagicMock
from ansible.module_utils.urls import ProxyError

import pytest
import socketio

from plugins.module_utils import uptime_kuma_api
from plugins.module_utils.uptime_kuma_api import (
    compute_diff,
    needs_update,
    normalize_result,
    serialize_value,
    uptime_kuma_argument_spec,
)


def _client(sio, timeout=30):
    client = object.__new__(uptime_kuma_api.UptimeKumaClient)
    client.module = MagicMock()
    client.module.params = {"validate_certs": True}
    client.timeout = timeout
    client.url = "http://kuma"
    client._sio = sio
    client._lists = {}
    client._events = {name: threading.Event() for name in uptime_kuma_api._PUSHED_LISTS}
    return client


def _connecting(monkeypatch, params=None, push_info=True):
    """Patch socketio.Client so UptimeKumaClient.__init__ can run without a server."""
    sio = MagicMock()
    handlers = {}
    sio.on.side_effect = handlers.__setitem__
    if push_info:
        sio.connect.side_effect = lambda url, wait_timeout: handlers["info"]({"version": "2.0.0"})
    monkeypatch.setattr(uptime_kuma_api.socketio, "Client", MagicMock(return_value=sio))
    module = MagicMock()
    module.params = {"api_url": "http://kuma/", "api_timeout": 1, "validate_certs": True,
                     "api_username": "u", "api_password": "p", "api_token": None, **(params or {})}
    module.fail_json.side_effect = SystemExit
    return module, sio


# ── connect / authenticate ──────────────────────────────────────────────

def test_missing_socketio_fails_cleanly(monkeypatch):
    monkeypatch.setattr(uptime_kuma_api, "HAS_SOCKETIO", False)
    module = MagicMock()
    module.fail_json.side_effect = SystemExit
    with pytest.raises(SystemExit):
        uptime_kuma_api.UptimeKumaClient(module)
    assert "python-socketio" in module.fail_json.call_args.kwargs["msg"]


def test_connect_failure_names_the_url(monkeypatch):
    module, sio = _connecting(monkeypatch)
    sio.connect.side_effect = socketio.exceptions.ConnectionError("refused")
    with pytest.raises(SystemExit):
        uptime_kuma_api.UptimeKumaClient(module)
    assert "http://kuma" in module.fail_json.call_args.kwargs["msg"]


def test_no_info_event_fails_and_disconnects(monkeypatch):
    module, sio = _connecting(monkeypatch, push_info=False)
    with pytest.raises(SystemExit):
        uptime_kuma_api.UptimeKumaClient(module)
    assert "'info'" in module.fail_json.call_args.kwargs["msg"]
    sio.disconnect.assert_called_once()


def test_password_login_waits_for_info_then_keeps_the_token(monkeypatch):
    module, sio = _connecting(monkeypatch)
    sio.call.return_value = {"ok": True, "token": "jwt"}
    client = uptime_kuma_api.UptimeKumaClient(module)
    assert client.token == "jwt"
    assert sio.call.call_args.args[0] == "login"


def test_token_login_uses_loginByToken(monkeypatch):
    module, sio = _connecting(monkeypatch, {"api_token": "jwt"})
    sio.call.return_value = {"ok": True}
    client = uptime_kuma_api.UptimeKumaClient(module)
    assert client.token == "jwt"
    assert sio.call.call_args.args[:2] == ("loginByToken", "jwt")


def test_login_without_token_in_reply_fails_and_disconnects(monkeypatch):
    module, sio = _connecting(monkeypatch)
    sio.call.return_value = {"ok": True, "tokenRequired": True}
    with pytest.raises(SystemExit):
        uptime_kuma_api.UptimeKumaClient(module)
    assert "2FA" in module.fail_json.call_args.kwargs["msg"]
    sio.disconnect.assert_called_once()


def test_login_ok_false_surfaces_the_server_message(monkeypatch):
    module, sio = _connecting(monkeypatch)
    sio.call.return_value = {"ok": False, "msg": "Incorrect username or password."}
    with pytest.raises(SystemExit):
        uptime_kuma_api.UptimeKumaClient(module)
    assert "Incorrect username" in module.fail_json.call_args.kwargs["msg"]


def test_login_false_skips_authentication(monkeypatch):
    module, sio = _connecting(monkeypatch)
    uptime_kuma_api.UptimeKumaClient(module, login=False)
    sio.call.assert_not_called()


# ── _call ───────────────────────────────────────────────────────────────

def test_retried_call_resends_once_with_the_module_timeout():
    sio = MagicMock()
    sio.call.side_effect = [socketio.exceptions.TimeoutError(), {"ok": True, "token": "jwt"}]

    reply = _client(sio)._call("login", {"username": "u", "password": "p"}, retry=True)

    assert reply == {"token": "jwt"}
    assert sio.call.call_count == 2
    assert all(c.kwargs["timeout"] == 30 for c in sio.call.call_args_list)


def test_retried_call_gives_up_after_two_attempts():
    sio = MagicMock()
    sio.call.side_effect = socketio.exceptions.TimeoutError()

    with pytest.raises(uptime_kuma_api.UptimeKumaTimeout, match="login"):
        _client(sio)._call("login", {}, retry=True)

    assert sio.call.call_count == 2


def test_unretried_call_tries_once():
    sio = MagicMock()
    sio.call.side_effect = socketio.exceptions.TimeoutError()
    with pytest.raises(uptime_kuma_api.UptimeKumaTimeout):
        _client(sio)._call("add", {"name": "x"})
    assert sio.call.call_count == 1


def test_call_strips_ok_and_raises_on_ok_false():
    sio = MagicMock()
    sio.call.return_value = {"ok": True, "id": 3}
    assert _client(sio)._call("x") == {"id": 3}

    sio.call.return_value = {"ok": False, "msg": "boom"}
    with pytest.raises(uptime_kuma_api.UptimeKumaError, match="boom"):
        _client(sio)._call("x")

    sio.call.return_value = {"ok": False}
    with pytest.raises(uptime_kuma_api.UptimeKumaError, match="'x' failed"):
        _client(sio)._call("x")


def test_call_translates_transport_errors():
    sio = MagicMock()
    sio.call.side_effect = socketio.exceptions.BadNamespaceError("/ is not a connected namespace")
    with pytest.raises(uptime_kuma_api.UptimeKumaError, match="Transport error during 'add'"):
        _client(sio)._call("add", {})


def test_call_marshals_arguments():
    sio = MagicMock()
    sio.call.return_value = {"ok": True}
    client = _client(sio)
    client._call("needSetup")
    client._call("setup", "u", "p")
    client._call("add", {"name": "x"})
    assert [c.args[1] for c in sio.call.call_args_list] == [None, ("u", "p"), {"name": "x"}]


def test_setup_is_not_retried():
    sio = MagicMock()
    sio.call.side_effect = socketio.exceptions.TimeoutError()
    with pytest.raises(uptime_kuma_api.UptimeKumaTimeout):
        _client(sio).setup("u", "p")
    assert sio.call.call_count == 1


# ── pushed lists ────────────────────────────────────────────────────────

def test_list_times_out_when_the_server_never_pushes():
    client = _client(MagicMock(), timeout=0.01)
    client._sio.call.return_value = None
    with pytest.raises(uptime_kuma_api.UptimeKumaTimeout, match="monitorList"):
        client._list("monitorList")


def test_list_returns_the_pushed_data():
    client = _client(MagicMock())
    client._store("notificationList")([{"id": 1, "config": None}])
    assert client.get_notifications() == [{"id": 1}]


def test_expect_raises_when_the_repush_never_arrives():
    client = _client(MagicMock(), timeout=0.01)
    client._sio.call.return_value = {"ok": True, "id": 1}
    with pytest.raises(uptime_kuma_api.UptimeKumaTimeout, match="notificationList"):
        client.add_notification(name="n")


# ── monitors ────────────────────────────────────────────────────────────

def test_monitor_normalisation_round_trips():
    out = uptime_kuma_api.UptimeKumaClient._monitor_out({"notificationIDList": {"3": True, "1": True}, "active": 1})
    assert out == {"notificationIDList": [1, 3], "active": True}
    data = uptime_kuma_api.UptimeKumaClient._monitor_in({"notificationIDList": [1, 3], "accepted_statuscodes": []})
    assert data == {"notificationIDList": {"1": True, "3": True}, "accepted_statuscodes": ["200-299"]}


def test_edit_monitor_strips_readonly_keys():
    sio = MagicMock()
    sio.call.side_effect = [
        {"ok": True, "monitor": {"id": 7, "name": "m", "tags": [], "childrenIDs": [], "includeSensitiveData": True}},
        {"ok": True},
    ]
    _client(sio).edit_monitor(7, interval=30)
    sent = sio.call.call_args.args[1]
    assert sent == {"id": 7, "name": "m", "interval": 30, "accepted_statuscodes": ["200-299"]}


EVENTS = [
    ("need_setup", (), "needSetup", None),
    ("get_monitor", (7,), "getMonitor", 7),
    ("add_monitor", (), "add", None),
    ("delete_monitor", (7,), "deleteMonitor", 7),
    ("pause_monitor", (7,), "pauseMonitor", 7),
    ("resume_monitor", (7,), "resumeMonitor", 7),
    ("get_tags", (), "getTags", None),
    ("add_tag", ("t", "#fff"), "addTag", {"name": "t", "color": "#fff"}),
    ("edit_tag", (4, "t", "#000"), "editTag", {"id": 4, "name": "t", "color": "#000"}),
    ("delete_tag", (4,), "deleteTag", 4),
    ("add_monitor_tag", (4, 7, "v"), "addMonitorTag", (4, 7, "v")),
    ("delete_monitor_tag", (4, 7, "v"), "deleteMonitorTag", (4, 7, "v")),
    ("add_status_page", ("s", "T"), "addStatusPage", ("T", "s")),
    ("delete_status_page", ("s",), "deleteStatusPage", "s"),
    ("get_maintenance", (3,), "getMaintenance", 3),
    ("add_maintenance", (), "addMaintenance", None),
    ("delete_maintenance", (3,), "deleteMaintenance", 3),
    ("get_settings", (), "getSettings", None),
    ("delete_notification", (1,), "deleteNotification", 1),
    ("enable_api_key", (2,), "enableAPIKey", 2),
    ("disable_api_key", (2,), "disableAPIKey", 2),
    ("delete_api_key", (2,), "deleteAPIKey", 2),
    ("setup", ("u", "p"), "setup", ("u", "p")),
    ("edit_monitor", (7,), "editMonitor", None),
    ("add_notification", (), "addNotification", ({}, None)),
    ("get_status_page_config", ("s",), "getStatusPage", "s"),
    ("edit_maintenance", (3,), "editMaintenance", None),
    ("add_api_key", ("k", None, True), "addAPIKey", {"name": "k", "expires": None, "active": 1}),
    ("set_settings", (), "setSettings", None),
]


@pytest.mark.parametrize("method, args, event, payload", EVENTS, ids=[e[0] for e in EVENTS])
def test_wrappers_emit_the_pinned_event(method, args, event, payload):
    sio = MagicMock()
    client = _client(sio)

    def reply_and_repush(*call_args, **kwargs):
        for event_ in client._events.values():
            event_.set()
        return {"ok": True, "monitor": {}, "tags": [], "tag": {}, "maintenance": {}, "data": {}, "config": {}}
    sio.call.side_effect = reply_and_repush
    getattr(client, method)(*args)
    assert sio.call.call_args.args[0] == event
    if payload is not None:
        assert sio.call.call_args.args[1] == payload


def test_list_wrappers_read_the_pushed_lists():
    client = _client(MagicMock())
    pushed = (("monitorList", {"1": {"id": 1, "name": "m", "active": 1, "notificationIDList": {"2": True}}}),
              ("maintenanceList", {"3": {"id": 3, "title": "w"}}),
              ("apiKeyList", [{"id": 2, "name": "k", "active": 0}]))

    def repush(*call_args, **kwargs):
        for name, data in pushed:
            client._store(name)(data)
    client._sio.call.side_effect = repush
    repush()
    assert client.get_monitor_by_name("m") == {"id": 1, "name": "m", "active": True, "notificationIDList": [2]}
    assert client.get_monitor_by_name("nope") is None
    assert client.get_maintenance_by_title("w") == {"id": 3, "title": "w"}
    assert client.get_api_key_by_name("k") == {"id": 2, "name": "k", "active": False}
    assert client.get_api_key(2)["name"] == "k"
    with pytest.raises(uptime_kuma_api.UptimeKumaError, match="API key 9 not found"):
        client.get_api_key(9)


def test_set_settings_merges_and_sends_password():
    sio = MagicMock()
    sio.call.side_effect = [{"ok": True, "data": {"a": 1, "b": 2}}, {"ok": True}]
    _client(sio).set_settings(password="pw", b=3)
    assert sio.call.call_args.args[1] == ({"a": 1, "b": 3}, "pw")


def test_save_status_page_sends_config_icon_and_groups(monkeypatch):
    sio = MagicMock()
    sio.call.side_effect = [{"ok": True, "config": {"id": 1, "slug": "s", "title": "T", "icon": "data:x"}},
                            {"ok": True}]
    resp = MagicMock()
    resp.read.return_value = b'{"config": {"description": "d"}, "publicGroupList": [{"name": "g"}], "incident": null}'
    resp.__enter__.return_value = resp
    monkeypatch.setattr(uptime_kuma_api, "open_url", lambda url, **kw: resp)
    _client(sio).save_status_page("s", title="New")
    args = sio.call.call_args.args
    assert args[0] == "saveStatusPage" and args[1][0] == "s"
    assert args[1][1]["title"] == "New" and args[1][1]["description"] == "d" and "incident" not in args[1][1]
    assert args[1][2] == "data:x" and args[1][3] == [{"name": "g"}]


# ── status pages ────────────────────────────────────────────────────────

def test_status_page_config_none_only_for_not_found():
    sio = MagicMock()
    sio.call.return_value = {"ok": False, "msg": "No slug?"}
    assert _client(sio).get_status_page_config("x") is None

    sio.call.side_effect = socketio.exceptions.TimeoutError()
    with pytest.raises(uptime_kuma_api.UptimeKumaTimeout):
        _client(sio).get_status_page_config("x")

    sio.call.side_effect = socketio.exceptions.BadNamespaceError("/ is not a connected namespace")
    with pytest.raises(uptime_kuma_api.UptimeKumaError, match="Transport error"):
        _client(sio).get_status_page_config("x")


def test_status_page_http_errors_are_translated_and_slug_is_quoted(monkeypatch):
    sio = MagicMock()
    sio.call.return_value = {"ok": True, "config": {"slug": "a b"}}
    seen = {}

    def open_url(url, **kwargs):
        seen["url"] = url
        raise ProxyError("proxy says no")
    monkeypatch.setattr(uptime_kuma_api, "open_url", open_url)
    with pytest.raises(uptime_kuma_api.UptimeKumaError, match="proxy says no"):
        _client(sio).get_status_page("a b")
    assert seen["url"] == "http://kuma/api/status-page/a%20b"


# ── comparison helpers ──────────────────────────────────────────────────

def test_comparable_only_converts_numeric_id_maps():
    assert uptime_kuma_api._comparable({"3": True, "1": True}) == [1, 3]
    assert uptime_kuma_api._comparable({"slack": True}) == {"slack": True}
    assert uptime_kuma_api._comparable({"\u00b2": True}) == {"\u00b2": True}


def test_add_api_key_returns_the_ack_without_waiting_for_a_push():
    sio = MagicMock()
    sio.call.return_value = {"ok": True, "key": "uk1_x", "keyID": 4}
    client = _client(sio, timeout=0.01)
    assert client.add_api_key("k", None, True) == {"key": "uk1_x", "keyID": 4}


# ── serialize_value ─────────────────────────────────────────────────────

class FakeEnum(str, Enum):
    FOO = "foo"
    BAR = "bar"


def test_serialize_value_enum():
    assert serialize_value(FakeEnum.FOO) == "foo"


def test_serialize_value_plain():
    assert serialize_value("hello") == "hello"
    assert serialize_value(42) == 42
    assert serialize_value(None) is None


# ── normalize_result ────────────────────────────────────────────────────

def test_normalize_result_flat_dict():
    data = {"type": FakeEnum.FOO, "name": "test"}
    result = normalize_result(data)
    assert result == {"type": "foo", "name": "test"}


def test_normalize_result_nested():
    data = {"outer": {"inner": FakeEnum.BAR}, "list": [FakeEnum.FOO, "plain"]}
    result = normalize_result(data)
    assert result == {"outer": {"inner": "bar"}, "list": ["foo", "plain"]}


def test_normalize_result_list():
    data = [{"type": FakeEnum.FOO}, {"type": FakeEnum.BAR}]
    result = normalize_result(data)
    assert result == [{"type": "foo"}, {"type": "bar"}]


def test_normalize_result_none():
    assert normalize_result(None) is None


def test_normalize_result_scalar():
    assert normalize_result(42) == 42
    assert normalize_result("hello") == "hello"


# ── compute_diff ────────────────────────────────────────────────────────

def test_compute_diff_basic():
    before = {"name": "old", "color": "#ff0000"}
    after = {"name": "new", "color": "#00ff00"}
    diff = compute_diff(before, after)
    assert diff["before"]["name"] == "old"
    assert diff["after"]["name"] == "new"


def test_compute_diff_none_before():
    diff = compute_diff(None, {"name": "new"})
    assert diff["before"] == {}
    assert diff["after"]["name"] == "new"


def test_compute_diff_none_after():
    diff = compute_diff({"name": "old"}, None)
    assert diff["before"]["name"] == "old"
    assert diff["after"] == {}


def test_compute_diff_exclude_keys():
    before = {"name": "old", "id": 1, "secret": "hidden"}
    after = {"name": "new", "id": 2, "secret": "visible"}
    diff = compute_diff(before, after, exclude_keys={"id", "secret"})
    assert "id" not in diff["before"]
    assert "id" not in diff["after"]
    assert "secret" not in diff["before"]
    assert "secret" not in diff["after"]


def test_compute_diff_with_enums():
    before = {"type": FakeEnum.FOO}
    after = {"type": FakeEnum.BAR}
    diff = compute_diff(before, after)
    assert diff["before"]["type"] == "foo"
    assert diff["after"]["type"] == "bar"


# ── needs_update ────────────────────────────────────────────────────────

def test_needs_update_no_change():
    current = {"name": "test", "color": "#ff0000", "id": 1}
    desired = {"name": "test", "color": "#ff0000"}
    assert needs_update(current, desired) is False


def test_needs_update_change():
    current = {"name": "test", "color": "#ff0000", "id": 1}
    desired = {"name": "test", "color": "#00ff00"}
    assert needs_update(current, desired) is True


def test_needs_update_none_desired_ignored():
    current = {"name": "test", "color": "#ff0000"}
    desired = {"name": "test", "color": None}
    assert needs_update(current, desired) is False


def test_needs_update_exclude_keys():
    current = {"name": "test", "password": "old"}
    desired = {"name": "test", "password": "new"}
    assert needs_update(current, desired, exclude_keys={"password"}) is False


def test_needs_update_enum_comparison():
    current = {"type": FakeEnum.FOO}
    desired = {"type": "foo"}
    assert needs_update(current, desired) is False


def test_needs_update_enum_mismatch():
    current = {"type": FakeEnum.FOO}
    desired = {"type": "bar"}
    assert needs_update(current, desired) is True


def test_needs_update_new_key():
    current = {"name": "test"}
    desired = {"name": "test", "color": "#ff0000"}
    assert needs_update(current, desired) is True


def test_needs_update_empty_desired():
    current = {"name": "test", "color": "#ff0000"}
    desired = {}
    assert needs_update(current, desired) is False


# ── uptime_kuma_argument_spec ───────────────────────────────────────────

def test_argument_spec_has_required_keys():
    spec = uptime_kuma_argument_spec()
    assert "api_url" in spec
    assert "api_username" in spec
    assert "api_password" in spec
    assert "api_token" in spec
    assert "validate_certs" in spec
    assert "api_timeout" in spec


def test_argument_spec_api_url_required():
    spec = uptime_kuma_argument_spec()
    assert spec["api_url"]["required"] is True


def test_argument_spec_password_no_log():
    spec = uptime_kuma_argument_spec()
    assert spec["api_password"]["no_log"] is True
    assert spec["api_token"]["no_log"] is True


def test_argument_spec_defaults():
    spec = uptime_kuma_argument_spec()
    assert spec["validate_certs"]["default"] is True
    assert spec["api_timeout"]["default"] == 30


def test_needs_update_notification_id_list_dict_vs_list():
    current = {"notificationIDList": {"1": True, "3": True}}
    assert needs_update(current, {"notificationIDList": [3, 1]}) is False
    assert needs_update(current, {"notificationIDList": [1]}) is True


# ── scrub ───────────────────────────────────────────────────────────────

def test_scrub_drops_keys_and_passes_empty_through():
    assert uptime_kuma_api.scrub({"a": 1, "secret": 2}, {"secret"}) == {"a": 1}
    assert uptime_kuma_api.scrub(None, {"secret"}) is None
    assert uptime_kuma_api.scrub({}, {"secret"}) == {}
