# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/modules/uptime_kuma_api_key.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock, patch

from plugins.module_utils.uptime_kuma_api import UptimeKumaError
from plugins.modules import uptime_kuma_api_key as mod

KEY = {"id": 2, "name": "ci", "active": True, "expires": None}


def _params(**over):
    return dict({"state": "present", "name": "ci", "active": True, "expires": None}, **over)


def test_create_returns_the_one_time_key(run_module):
    client = MagicMock()
    client.get_api_key_by_name.return_value = None
    client.add_api_key.return_value = {"key": "uk1_secret", "keyID": 2}
    client.get_api_key.return_value = KEY
    result, client = run_module(mod, _params(), client)
    assert result["changed"] is True and result["key"] == "uk1_secret" and result["api_key"] == KEY
    client.add_api_key.assert_called_once_with(name="ci", expires=None, active=True)


def test_check_mode_create_does_not_call_the_server(run_module):
    client = MagicMock()
    client.get_api_key_by_name.return_value = None
    result, client = run_module(mod, _params(), client, check_mode=True)
    assert result["changed"] is True and "key" not in result
    client.add_api_key.assert_not_called()


def test_enable_and_disable(run_module):
    client = MagicMock()
    client.get_api_key_by_name.return_value = dict(KEY, active=False)
    client.get_api_key.return_value = KEY
    result, unused = run_module(mod, _params(), client)
    assert result["changed"] is True
    client.enable_api_key.assert_called_once_with(2)

    client.get_api_key_by_name.return_value = KEY
    client.get_api_key.return_value = dict(KEY, active=False)
    result, unused = run_module(mod, _params(active=False), client)
    assert result["changed"] is True
    client.disable_api_key.assert_called_once_with(2)


def test_check_mode_active_change_predicts_the_diff(run_module):
    client = MagicMock()
    client.get_api_key_by_name.return_value = KEY
    result, unused = run_module(mod, _params(active=False), client, check_mode=True)
    assert result["changed"] is True
    assert result["diff"]["before"]["active"] is True and result["diff"]["after"]["active"] is False
    client.disable_api_key.assert_not_called()


def test_absent(run_module):
    client = MagicMock()
    client.get_api_key_by_name.return_value = KEY
    result, unused = run_module(mod, _params(state="absent"), client, check_mode=True)
    assert result["changed"] is True
    client.delete_api_key.assert_not_called()

    result, unused = run_module(mod, _params(state="absent"), client)
    assert result["changed"] is True and result["api_key"] == {}
    client.delete_api_key.assert_called_once_with(2)

    client.get_api_key_by_name.return_value = None
    result, unused = run_module(mod, _params(state="absent"), client)
    assert result["changed"] is False


def test_api_error_is_reported_and_client_disconnected():
    module = MagicMock()
    module.params = _params()
    module.check_mode = False
    client = MagicMock()
    client.get_api_key_by_name.side_effect = UptimeKumaError("boom")
    with patch.object(mod, "UptimeKumaClient", return_value=client):
        mod.run_module(module)
    assert "boom" in module.fail_json.call_args.kwargs["msg"]
    client.disconnect.assert_called_once()


def test_expiry_strings_the_server_stores_verbatim_compare_as_strings():
    assert mod._instant("never") == "never"
    assert mod._instant("2027-01-01 00:00:00") == mod._instant("2027-01-01T00:00:00.000Z")
    assert mod._instant("2027-01-01T02:00:00+02:00") == mod._instant("2027-01-01 00:00:00")
