# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/modules/uptime_kuma_settings.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock

from plugins.modules import uptime_kuma_settings

SERVER = {"checkUpdate": True, "keepDataPeriodDays": 180, "steamAPIKey": "STEAM-SECRET"}


def _module(**params):
    module = MagicMock()
    module.params = {"state": "present", "check_update": None, "check_beta": None, "keep_data_period_days": None,
                     "server_timezone": None, "entry_page": None, "search_engine_index": None,
                     "primary_base_url": None, "steam_api_key": None, "dns_cache": None,
                     "tls_expiry_notify_days": None, "disable_auth": None, "trust_proxy": None, "password": None}
    module.params.update(params)
    module.check_mode = False
    result = {}
    module.exit_json = lambda **kw: result.update(kw)
    module.fail_json = lambda **kw: result.update(kw, failed=True)
    return module, result


def test_query_omits_steam_api_key():
    module, result = _module(state="query")
    client = MagicMock()
    client.get_settings.return_value = SERVER
    uptime_kuma_settings._run(module, client)
    assert result["settings"]["keepDataPeriodDays"] == 180
    assert "steamAPIKey" not in result["settings"]


def test_update_omits_steam_api_key_from_result_and_diff():
    module, result = _module(check_update=False)
    client = MagicMock()
    client.get_settings.side_effect = [SERVER, dict(SERVER, checkUpdate=False)]
    uptime_kuma_settings._run(module, client)
    assert result["changed"] is True
    assert "steamAPIKey" not in result["settings"]
    assert "steamAPIKey" not in result["diff"]["before"]
    assert "steamAPIKey" not in result["diff"]["after"]


def test_steam_api_key_alone_is_written():
    module, result = _module(steam_api_key="NEW")
    client = MagicMock()
    client.get_settings.side_effect = [SERVER, dict(SERVER, steamAPIKey="NEW")]
    uptime_kuma_settings._run(module, client)
    assert result["changed"] is True
    assert client.set_settings.call_args.kwargs["steamAPIKey"] == "NEW"


def test_disable_auth_change_requires_password():
    module, result = _module(disable_auth=True)
    client = MagicMock()
    client.get_settings.return_value = dict(SERVER, disableAuth=False)
    uptime_kuma_settings._run(module, client)
    assert result.get("failed") is True
    client.set_settings.assert_not_called()

    module, result = _module(disable_auth=False)
    client.get_settings.side_effect = [dict(SERVER, disableAuth=True), dict(SERVER, disableAuth=False)]
    uptime_kuma_settings._run(module, client)
    assert result["changed"] is True and client.set_settings.called
    client.get_settings.side_effect = None

    module, result = _module(disable_auth=True, password="pw")
    client.get_settings.side_effect = [dict(SERVER, disableAuth=False), dict(SERVER, disableAuth=True)]
    uptime_kuma_settings._run(module, client)
    assert result["changed"] is True
    assert client.set_settings.call_args.kwargs["password"] == "pw"
