# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/module_utils/uptime_kuma_api.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock

import pytest
import socketio

from plugins.module_utils import uptime_kuma_api


def _client(sio):
    client = object.__new__(uptime_kuma_api.UptimeKumaClient)
    client.module = MagicMock()
    client.timeout = 30
    client._sio = sio
    return client


def test_retried_call_waits_long_enough_for_a_password_login():
    """Uptime Kuma 2.5 takes ~3.5 s to answer ``login``; a 3 s per-attempt
    timeout failed every attempt while the server logged a success each time."""
    sio = MagicMock()
    sio.call.side_effect = [socketio.exceptions.TimeoutError(), {"ok": True, "token": "jwt"}]

    reply = _client(sio)._call("login", {"username": "u", "password": "p"}, retry=True)

    assert reply == {"token": "jwt"}
    assert sio.call.call_count == 2
    assert all(c.kwargs["timeout"] == uptime_kuma_api._RETRY_TIMEOUT for c in sio.call.call_args_list)
    assert uptime_kuma_api._RETRY_TIMEOUT >= 10


def test_retried_call_gives_up_after_five_attempts():
    sio = MagicMock()
    sio.call.side_effect = socketio.exceptions.TimeoutError()

    with pytest.raises(uptime_kuma_api.UptimeKumaError, match="login"):
        _client(sio)._call("login", {}, retry=True)

    assert sio.call.call_count == 5


def test_unretried_call_uses_the_module_timeout():
    sio = MagicMock()
    sio.call.return_value = {"ok": True, "id": 1}

    _client(sio)._call("add", {"name": "x"})

    assert sio.call.call_args.kwargs["timeout"] == 30
