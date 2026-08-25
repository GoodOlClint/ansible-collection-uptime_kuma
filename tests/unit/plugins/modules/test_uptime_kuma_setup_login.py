# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for uptime_kuma_setup and uptime_kuma_login."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock, patch

import pytest

from plugins.module_utils.uptime_kuma_api import UptimeKumaError
from plugins.modules import uptime_kuma_login, uptime_kuma_setup


def _module(params, check_mode=False):
    module = MagicMock()
    module.params = params
    module.check_mode = check_mode
    module.exit_json.side_effect = SystemExit
    module.fail_json.side_effect = SystemExit
    return module


@pytest.mark.parametrize("needs_setup, check_mode, expect_call, expect", [
    (False, False, False, {"changed": False, "setup_performed": False}),
    (True, False, True, {"changed": True, "setup_performed": True}),
    (True, True, False, {"changed": True, "setup_performed": False}),
])
def test_setup(needs_setup, check_mode, expect_call, expect):
    module = _module({"username": "u", "password": "p"}, check_mode)
    client = MagicMock()
    client.need_setup.return_value = needs_setup
    with patch.object(uptime_kuma_setup, "UptimeKumaClient", return_value=client) as ctor, pytest.raises(SystemExit):
        uptime_kuma_setup.run_module(module)
    assert ctor.call_args.kwargs == {"login": False}
    assert module.exit_json.call_args.kwargs == expect
    assert client.setup.called is expect_call
    client.disconnect.assert_called_once()


def test_setup_error_is_reported():
    module = _module({"username": "u", "password": "p"})
    client = MagicMock()
    client.need_setup.side_effect = UptimeKumaError("no ack")
    with patch.object(uptime_kuma_setup, "UptimeKumaClient", return_value=client), pytest.raises(SystemExit):
        uptime_kuma_setup.run_module(module)
    assert "no ack" in module.fail_json.call_args.kwargs["msg"]
    client.disconnect.assert_called_once()


def test_login_returns_the_token_and_never_changes():
    module = _module({"api_url": "http://k", "api_username": "u", "api_password": "p"})
    client = MagicMock()
    client.token = "jwt"
    with patch.object(uptime_kuma_login, "AnsibleModule", return_value=module), \
            patch.object(uptime_kuma_login, "UptimeKumaClient", return_value=client), pytest.raises(SystemExit):
        uptime_kuma_login.main()
    assert module.exit_json.call_args.kwargs == {"changed": False, "token": "jwt"}
    client.disconnect.assert_called_once()
