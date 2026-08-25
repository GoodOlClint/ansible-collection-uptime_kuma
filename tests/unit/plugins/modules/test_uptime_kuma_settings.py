# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/modules/uptime_kuma_settings.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock

from plugins.modules import uptime_kuma_settings as mod

SERVER = {"checkUpdate": True, "keepDataPeriodDays": 180, "steamAPIKey": "STEAM-SECRET"}


def _params(**over):
    params = {"state": "present", "check_update": None, "check_beta": None, "keep_data_period_days": None,
              "server_timezone": None, "entry_page": None, "search_engine_index": None,
              "primary_base_url": None, "steam_api_key": None, "dns_cache": None,
              "tls_expiry_notify_days": None, "disable_auth": None, "trust_proxy": None, "password": None}
    params.update(over)
    return params


def test_query_omits_steam_api_key(run_module):
    client = MagicMock()
    client.get_settings.return_value = SERVER
    result, unused = run_module(mod, _params(state="query"), client)
    assert result["settings"]["keepDataPeriodDays"] == 180
    assert "steamAPIKey" not in result["settings"]


def test_update_omits_steam_api_key_from_result_and_diff(run_module):
    client = MagicMock()
    client.get_settings.side_effect = [SERVER, dict(SERVER, checkUpdate=False)]
    result, unused = run_module(mod, _params(check_update=False), client)
    assert result["changed"] is True
    assert "steamAPIKey" not in result["settings"]
    assert "steamAPIKey" not in result["diff"]["before"]
    assert "steamAPIKey" not in result["diff"]["after"]


def test_steam_api_key_alone_is_written(run_module):
    client = MagicMock()
    client.get_settings.side_effect = [SERVER, dict(SERVER, steamAPIKey="NEW")]
    result, unused = run_module(mod, _params(steam_api_key="NEW"), client)
    assert result["changed"] is True
    assert client.set_settings.call_args.kwargs["steamAPIKey"] == "NEW"


def test_disable_auth_change_requires_password(run_module):
    client = MagicMock()
    client.get_settings.return_value = dict(SERVER, disableAuth=False)
    result, unused = run_module(mod, _params(disable_auth=True), client)
    assert result.get("failed") is True
    client.set_settings.assert_not_called()

    client.get_settings.side_effect = [dict(SERVER, disableAuth=True), dict(SERVER, disableAuth=False)]
    result, unused = run_module(mod, _params(disable_auth=False), client)
    assert result["changed"] is True and client.set_settings.called

    client.get_settings.side_effect = [dict(SERVER, disableAuth=False), dict(SERVER, disableAuth=True)]
    result, unused = run_module(mod, _params(disable_auth=True, password="pw"), client)
    assert result["changed"] is True
    assert client.set_settings.call_args.kwargs["password"] == "pw"
