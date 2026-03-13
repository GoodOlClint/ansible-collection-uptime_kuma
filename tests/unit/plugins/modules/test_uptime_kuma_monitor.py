# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/modules/uptime_kuma_monitor.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")


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
        "description": None,
        "keyword": None,
        "ignore_tls": False,
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
        }

        params = build_monitor_params(module)
        assert params["type"] == "http"
        assert params["name"] == "test"
        assert params["url"] == "https://example.com"
        assert params["interval"] == 60
