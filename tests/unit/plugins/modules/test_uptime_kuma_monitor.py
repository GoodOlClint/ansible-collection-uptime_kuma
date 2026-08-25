# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/modules/uptime_kuma_monitor.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock

import pytest


def _make_module_and_client(params_override=None, check_mode=False):
    """Create a mock module and client for testing."""
    mock_module = MagicMock()
    mock_module.params = {
        "api_url": "http://localhost:3001",
        "api_username": "admin",
        "api_password": "secret",
        "api_token": None,
        "validate_certs": True,
        "api_timeout": 10,
        "state": "present",
        "name": "test-monitor",
        "monitor_type": "http",
        "url": "https://example.com",
        "hostname": None,
        "port": None,
        "interval": 60,
        "retry_interval": 60,
        "max_retries": 1,
        "upside_down": False,
        "timeout": 48,
        "resend_interval": 0,
        "invert_keyword": False,
        "json_path": None,
        "json_path_operator": "==",
        "expected_value": None,
        "parent": None,
        "notification_names": None,
        "description": None,
        "keyword": None,
        "ignore_tls": False,
        "expiry_notification": None,
        "max_redirects": 10,
        "accepted_statuscodes": ["200-299"],
        "method": "GET",
        "body": None,
        "headers": None,
        "dns_resolve_server": "1.1.1.1",
        "dns_resolve_type": "A",
        "mqtt_username": None,
        "mqtt_password": None,
        "mqtt_topic": None,
        "mqtt_success_message": None,
        "database_connection_string": None,
        "database_query": None,
        "docker_container": None,
        "docker_host": None,
        "notification_ids": None,
        "proxy_id": None,
        "active": True,
    }
    if params_override:
        mock_module.params.update(params_override)
    mock_module.check_mode = check_mode

    exit_result = {}
    mock_module.exit_json = lambda **kw: exit_result.update(kw)
    mock_module.fail_json = lambda **kw: exit_result.update(kw, failed=True)

    client = MagicMock()
    return mock_module, client, exit_result


class TestMonitorPresent:
    def test_create_http_monitor(self):
        """Create an HTTP monitor when it does not exist."""
        from plugins.modules import uptime_kuma_monitor

        module, client, result = _make_module_and_client()
        client.get_monitor_by_name.return_value = None
        client.add_monitor.return_value = {"monitorID": 1}
        client.get_monitor.return_value = {
            "id": 1, "name": "test-monitor", "type": "http",
            "url": "https://example.com", "active": True,
        }

        uptime_kuma_monitor._run(module, client)
        assert result.get("changed") is True
        client.add_monitor.assert_called_once()

    def test_no_change_when_identical(self):
        """No change when monitor matches desired state."""
        from plugins.modules import uptime_kuma_monitor

        module, client, result = _make_module_and_client()
        client.get_monitor_by_name.return_value = {
            "id": 1, "name": "test-monitor", "type": "http",
            "url": "https://example.com", "interval": 60,
            "retryInterval": 60, "maxretries": 1,
            "upsideDown": False, "active": True,
            "ignoreTls": False, "maxredirects": 10,
            "accepted_statuscodes": ["200-299"],
            "method": "GET",
            "dns_resolve_server": "1.1.1.1",
            "dns_resolve_type": "A",
            "timeout": 48, "resendInterval": 0, "invertKeyword": False,
            "jsonPathOperator": "==",
        }

        uptime_kuma_monitor._run(module, client)
        assert result.get("changed") is False
        client.add_monitor.assert_not_called()
        client.edit_monitor.assert_not_called()


class TestMonitorAbsent:
    def test_delete_existing_monitor(self):
        """Delete a monitor that exists."""
        from plugins.modules import uptime_kuma_monitor

        module, client, result = _make_module_and_client({"state": "absent"})
        client.get_monitor_by_name.return_value = {
            "id": 1, "name": "test-monitor", "type": "http",
        }

        uptime_kuma_monitor._run(module, client)
        assert result.get("changed") is True
        client.delete_monitor.assert_called_once_with(1)

    def test_no_change_when_absent(self):
        """No change when monitor does not exist."""
        from plugins.modules import uptime_kuma_monitor

        module, client, result = _make_module_and_client({"state": "absent"})
        client.get_monitor_by_name.return_value = None

        uptime_kuma_monitor._run(module, client)
        assert result.get("changed") is False


class TestMonitorCheckMode:
    def test_check_mode_create(self):
        """Check mode reports change without creating."""
        from plugins.modules import uptime_kuma_monitor

        module, client, result = _make_module_and_client(check_mode=True)
        client.get_monitor_by_name.return_value = None

        uptime_kuma_monitor._run(module, client)
        assert result.get("changed") is True
        client.add_monitor.assert_not_called()

    def test_check_mode_delete(self):
        """Check mode reports change without deleting."""
        from plugins.modules import uptime_kuma_monitor

        module, client, result = _make_module_and_client(
            {"state": "absent"}, check_mode=True
        )
        client.get_monitor_by_name.return_value = {
            "id": 1, "name": "test-monitor", "type": "http",
        }

        uptime_kuma_monitor._run(module, client)
        assert result.get("changed") is True
        client.delete_monitor.assert_not_called()


class TestBuildMonitorParams:
    def test_basic_params(self):
        """Build params includes required fields."""
        from plugins.modules.uptime_kuma_monitor import build_monitor_params

        module = MagicMock()
        module.params = {
            "name": "test",
            "monitor_type": "http",
            "url": "https://example.com",
            "hostname": None,
            "port": None,
            "interval": 60,
            "retry_interval": 60,
            "max_retries": 1,
            "upside_down": False,
            "description": None,
            "keyword": None,
            "ignore_tls": None,
            "max_redirects": None,
            "accepted_statuscodes": None,
            "method": "GET",
            "body": None,
            "headers": None,
            "dns_resolve_server": None,
            "dns_resolve_type": None,
            "mqtt_username": None,
            "mqtt_password": None,
            "mqtt_topic": None,
            "mqtt_success_message": None,
            "database_connection_string": None,
            "database_query": None,
            "docker_container": None,
            "docker_host": None,
            "notification_ids": None,
            "proxy_id": None,
            "timeout": 48,
            "resend_interval": 0,
            "invert_keyword": False,
            "json_path": None,
            "json_path_operator": "==",
            "expected_value": None,
        }

        params = build_monitor_params(module)
        assert params["type"] == "http"
        assert params["name"] == "test"
        assert params["url"] == "https://example.com"
        assert params["interval"] == 60


def test_json_query_params_and_name_resolution():
    from plugins.modules.uptime_kuma_monitor import build_monitor_params, resolve_references

    module = MagicMock()
    module.params = {
        "name": "valheim", "monitor_type": "json-query", "url": "http://h/status.json",
        "interval": 60, "retry_interval": 60, "max_retries": 2, "upside_down": False,
        "timeout": 16, "resend_interval": 0, "invert_keyword": False,
        "json_path": "platform", "json_path_operator": "==", "expected_value": "playfab",
        "notification_names": ["ntfy"], "parent": "grp",
    }
    client = MagicMock()
    client.get_notification_by_name.return_value = {"id": 7}
    client.get_monitor_by_name.return_value = {"id": 3, "type": "group"}

    params = resolve_references(module, client, build_monitor_params(module))
    assert params["jsonPath"] == "platform"
    assert params["jsonPathOperator"] == "=="
    assert params["expectedValue"] == "playfab"
    assert params["timeout"] == 16
    assert params["notificationIDList"] == [7]
    assert params["parent"] == 3
    module.fail_json.assert_not_called()

    client.get_notification_by_name.return_value = None
    module.fail_json.side_effect = SystemExit
    try:
        resolve_references(module, client, build_monitor_params(module))
    except SystemExit:
        pass
    module.fail_json.assert_called_once()


def test_unset_optional_params_are_not_sent_or_compared():
    """dns_resolve_* and json_path_operator have no module default: an http monitor
    whose live row carries null for them must not report a change."""
    from plugins.modules import uptime_kuma_monitor
    from plugins.modules.uptime_kuma_monitor import build_monitor_params

    module, client, result = _make_module_and_client()
    module.params.update({"dns_resolve_server": None, "dns_resolve_type": None, "json_path_operator": None})
    params = build_monitor_params(module)
    assert "dns_resolve_server" not in params
    assert "dns_resolve_type" not in params
    assert "jsonPathOperator" not in params
    client.get_monitor_by_name.return_value = {
        "id": 1, "name": "test-monitor", "type": "http",
        "url": "https://example.com", "interval": 60,
        "retryInterval": 60, "maxretries": 1,
        "upsideDown": False, "active": True,
        "ignoreTls": False, "maxredirects": 10,
        "accepted_statuscodes": ["200-299"],
        "method": "GET",
        "dns_resolve_server": None,
        "dns_resolve_type": None,
        "timeout": 48, "resendInterval": 0, "invertKeyword": False,
        "jsonPathOperator": None,
    }
    uptime_kuma_monitor._run(module, client)
    assert result.get("changed") is False


def test_optional_type_params_carry_no_argument_spec_default():
    from unittest.mock import patch
    from plugins.modules import uptime_kuma_monitor

    captured = {}

    def fake_module(**kwargs):
        captured.update(kwargs["argument_spec"])
        raise SystemExit

    with patch.object(uptime_kuma_monitor, "AnsibleModule", side_effect=fake_module):
        try:
            uptime_kuma_monitor.main()
        except SystemExit:
            pass
    for key in ("dns_resolve_server", "dns_resolve_type", "json_path_operator"):
        assert "default" not in captured[key], key


class TestMonitorSecrets:
    SERVER = {"id": 7, "name": "test-monitor", "type": "http", "url": "https://example.com", "active": True,
              "basic_auth_pass": "hunter2", "tlsKey": "-----BEGIN", "pushToken": "tok",
              "headers": '{"Authorization": "Bearer x"}', "grpcMetadata": "k=v", "bearer_token": "b"}

    @staticmethod
    def _assert_scrubbed(result):
        for key in ("basic_auth_pass", "tlsKey", "pushToken", "headers", "grpcMetadata", "bearer_token"):
            assert key not in result["monitor"]
            for side in result.get("diff", {}).values():
                assert key not in side

    def test_create_result_omits_server_side_credentials(self):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client()
        client.get_monitor_by_name.return_value = None
        client.add_monitor.return_value = {"monitorID": 7}
        client.get_monitor.return_value = self.SERVER
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is True
        assert result["monitor"]["url"] == "https://example.com"
        self._assert_scrubbed(result)

    def test_delete_diff_omits_server_side_credentials(self):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client({"state": "absent"})
        client.get_monitor_by_name.return_value = self.SERVER
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is True
        self._assert_scrubbed(result)

    def test_unchanged_result_omits_server_side_credentials(self):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client({"url": "https://example.com"})
        client.get_monitor_by_name.return_value = dict(
            self.SERVER, interval=60, retryInterval=60, maxretries=1, upsideDown=False, timeout=48,
            resendInterval=0, invertKeyword=False, method="GET", ignoreTls=False, maxredirects=10,
            accepted_statuscodes=["200-299"], dns_resolve_server="1.1.1.1", dns_resolve_type="A",
            jsonPathOperator="==")
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is False
        self._assert_scrubbed(result)


class TestMonitorDrift:
    EXISTING = dict(id=7, name="test-monitor", type="http", url="https://example.com", active=True, interval=60,
                    retryInterval=60, maxretries=1, upsideDown=False, timeout=48, resendInterval=0,
                    invertKeyword=False, method="GET", ignoreTls=False, maxredirects=10,
                    accepted_statuscodes=["200-299"], dns_resolve_server="1.1.1.1", dns_resolve_type="A",
                    jsonPathOperator="==")

    def test_credential_rotation_is_detected_and_never_returned(self):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client({"mqtt_password": "rotated"})
        client.get_monitor_by_name.return_value = dict(self.EXISTING, mqttPassword="old")
        client.get_monitor.return_value = dict(self.EXISTING, mqttPassword="rotated")
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is True
        assert client.edit_monitor.call_args.kwargs["mqttPassword"] == "rotated"
        assert "mqttPassword" not in result["monitor"] and "mqttPassword" not in result["diff"]["after"]

        module, client, result = _make_module_and_client({"mqtt_password": "rotated"})
        client.get_monitor_by_name.return_value = dict(self.EXISTING, mqttPassword="rotated")
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is False

    def test_inactive_create_sends_active_false_and_never_pauses(self):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client({"active": False})
        client.get_monitor_by_name.return_value = None
        client.add_monitor.return_value = {"monitorID": 7}
        client.get_monitor.return_value = dict(self.EXISTING, active=False)
        uptime_kuma_monitor._run(module, client)
        assert client.add_monitor.call_args.kwargs["active"] is False
        client.pause_monitor.assert_not_called()
        assert result["monitor"]["active"] is False

        module, client, result = _make_module_and_client({"active": False}, check_mode=True)
        client.get_monitor_by_name.return_value = None
        uptime_kuma_monitor._run(module, client)
        assert result["monitor"]["active"] is False and result["diff"]["after"]["active"] is False
        client.add_monitor.assert_not_called()

        module, client, result = _make_module_and_client({"active": None})
        client.get_monitor_by_name.return_value = None
        client.add_monitor.return_value = {"monitorID": 7}
        client.get_monitor.return_value = dict(self.EXISTING, active=False)
        uptime_kuma_monitor._run(module, client)
        assert client.add_monitor.call_args.kwargs["active"] is False


class TestMonitorActiveState:
    EXISTING = TestMonitorDrift.EXISTING

    def test_pause_and_resume_existing(self):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client({"active": False})
        client.get_monitor_by_name.return_value = self.EXISTING
        client.get_monitor.return_value = dict(self.EXISTING, active=False)
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is True
        client.pause_monitor.assert_called_once_with(7)
        client.edit_monitor.assert_not_called()

        module, client, result = _make_module_and_client()
        client.get_monitor_by_name.return_value = dict(self.EXISTING, active=False)
        client.get_monitor.return_value = self.EXISTING
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is True
        client.resume_monitor.assert_called_once_with(7)

    def test_check_mode_active_only_change_predicts_the_diff(self):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client({"active": False}, check_mode=True)
        client.get_monitor_by_name.return_value = self.EXISTING
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is True
        assert result["diff"]["before"]["active"] is True and result["diff"]["after"]["active"] is False
        client.pause_monitor.assert_not_called()

    def test_check_mode_field_and_active_change_predicts_both(self):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client({"active": False, "interval": 300}, check_mode=True)
        client.get_monitor_by_name.return_value = self.EXISTING
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is True
        assert result["diff"]["after"]["interval"] == 300 and result["diff"]["after"]["active"] is False
        client.edit_monitor.assert_not_called()

    def test_unknown_parent_group_fails(self):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client({"parent": "nope"})
        module.fail_json = MagicMock(side_effect=SystemExit)
        client.get_monitor_by_name.return_value = None
        try:
            uptime_kuma_monitor._run(module, client)
        except SystemExit:
            pass
        assert "Group monitor 'nope'" in module.fail_json.call_args.kwargs["msg"]
        client.add_monitor.assert_not_called()


class TestMonitorCreateRequirements:
    def test_create_without_type_specific_options_fails(self):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client({"url": None})
        module.fail_json = MagicMock(side_effect=SystemExit)
        client.get_monitor_by_name.return_value = None
        try:
            uptime_kuma_monitor._run(module, client)
        except SystemExit:
            pass
        assert "needs url" in module.fail_json.call_args.kwargs["msg"]
        client.add_monitor.assert_not_called()

    @pytest.mark.parametrize("monitor_type, missing", [
        ("ntp", "hostname"), ("sip-options", "hostname, port"), ("websocket-upgrade", "url"),
        ("oracledb", "database_connection_string"), ("redis", "database_connection_string"),
        ("sqlserver", "database_connection_string"), ("postgres", "database_connection_string"),
        ("mysql", "database_connection_string"), ("mongodb", "database_connection_string"),
        ("steam", "hostname, port"), ("gamedig", "hostname, port"), ("radius", "hostname"),
    ])
    def test_every_targeted_type_needs_its_target(self, monitor_type, missing):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client({"url": None, "monitor_type": monitor_type})
        module.fail_json = MagicMock(side_effect=SystemExit)
        client.get_monitor_by_name.return_value = None
        try:
            uptime_kuma_monitor._run(module, client)
        except SystemExit:
            pass
        assert f"needs {missing}" in module.fail_json.call_args.kwargs["msg"]
        client.add_monitor.assert_not_called()

    def test_manual_needs_nothing(self):
        from plugins.modules import uptime_kuma_monitor
        module, client, result = _make_module_and_client({"url": None, "monitor_type": "manual"})
        client.get_monitor_by_name.return_value = None
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is True and client.add_monitor.called

    def test_partial_update_and_delete_do_not_need_them(self):
        from plugins.modules import uptime_kuma_monitor
        existing = dict(TestMonitorDrift.EXISTING, interval=30)
        module, client, result = _make_module_and_client({"url": None})
        client.get_monitor_by_name.return_value = existing
        client.get_monitor.return_value = dict(existing, interval=60)
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is True and client.edit_monitor.called

        module, client, result = _make_module_and_client({"url": None, "state": "absent"})
        client.get_monitor_by_name.return_value = existing
        uptime_kuma_monitor._run(module, client)
        assert result["changed"] is True and client.delete_monitor.called


class TestExpiryNotification:
    @pytest.mark.parametrize("value", [True, False])
    def test_reaches_the_payload(self, value):
        from plugins.modules.uptime_kuma_monitor import build_monitor_params
        module, _, _ = _make_module_and_client({"expiry_notification": value})
        assert build_monitor_params(module)["expiryNotification"] is value

    def test_absent_when_unset(self):
        from plugins.modules.uptime_kuma_monitor import build_monitor_params
        module, _, _ = _make_module_and_client()
        assert "expiryNotification" not in build_monitor_params(module)
