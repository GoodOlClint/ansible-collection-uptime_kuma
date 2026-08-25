# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/modules/uptime_kuma_monitor_tag.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock

from plugins.modules import uptime_kuma_monitor_tag as mod


def _params(**over):
    return dict({"state": "present", "tag_name": "t", "monitor_name": "m", "value": "v"}, **over)


def _client(tags):
    client = MagicMock()
    client.get_tag_by_name.return_value = {"id": 4}
    client.get_monitor_by_name.return_value = {"id": 7, "tags": tags}
    return client


def test_unknown_tag_or_monitor_fails_before_any_write(run_module):
    client = _client([])
    client.get_tag_by_name.return_value = None
    result, unused = run_module(mod, _params(), client)
    assert result["failed"] and "Tag 't' not found" in result["msg"]

    client = _client([])
    client.get_monitor_by_name.return_value = None
    result, unused = run_module(mod, _params(), client)
    assert result["failed"] and "Monitor 'm' not found" in result["msg"]
    client.add_monitor_tag.assert_not_called()


def test_assign_idempotent_and_check_mode(run_module):
    client = _client([])
    result, unused = run_module(mod, _params(), client)
    assert result["changed"] is True and result["monitor_tag"] == {"tag_id": 4, "monitor_id": 7, "value": "v"}
    client.add_monitor_tag.assert_called_once_with(4, 7, "v")

    client = _client([{"tag_id": 4, "value": "v"}])
    result, unused = run_module(mod, _params(), client)
    assert result["changed"] is False

    client = _client([{"tag_id": 4, "value": "other"}])
    result, unused = run_module(mod, _params(), client, check_mode=True)
    assert result["changed"] is True
    client.add_monitor_tag.assert_not_called()


def test_remove(run_module):
    client = _client([{"tag_id": 4, "value": "v"}])
    result, unused = run_module(mod, _params(state="absent"), client, check_mode=True)
    assert result["changed"] is True
    client.delete_monitor_tag.assert_not_called()

    result, unused = run_module(mod, _params(state="absent"), client)
    assert result["changed"] is True
    client.delete_monitor_tag.assert_called_once_with(4, 7, "v")

    client = _client([])
    result, unused = run_module(mod, _params(state="absent"), client)
    assert result["changed"] is False
