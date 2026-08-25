# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/modules/uptime_kuma_tag.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock

from plugins.modules import uptime_kuma_tag as mod

EXISTING = {"id": 1, "name": "existing-tag", "color": "#ff0000"}


def _params(**over):
    return dict({"state": "present", "name": "existing-tag", "color": "#ff0000"}, **over)


def _client(existing):
    client = MagicMock()
    client.get_tag_by_name.return_value = existing
    return client


def test_create_new_tag(run_module):
    client = _client(None)
    client.add_tag.return_value = {"id": 1, "name": "new-tag", "color": "#ff0000"}
    result, unused = run_module(mod, _params(name="new-tag"), client)
    assert result["changed"] is True
    client.add_tag.assert_called_once_with(name="new-tag", color="#ff0000")


def test_no_change_when_identical(run_module):
    client = _client(EXISTING)
    result, unused = run_module(mod, _params(), client)
    assert result["changed"] is False
    client.add_tag.assert_not_called()
    client.edit_tag.assert_not_called()


def test_update_when_color_differs(run_module):
    client = _client(EXISTING)
    client.edit_tag.return_value = {"tag": dict(EXISTING, color="#00ff00")}
    result, unused = run_module(mod, _params(color="#00ff00"), client)
    assert result["changed"] is True
    client.edit_tag.assert_called_once()


def test_delete_existing_tag(run_module):
    client = _client(EXISTING)
    result, unused = run_module(mod, _params(state="absent", color=None), client)
    assert result["changed"] is True
    client.delete_tag.assert_called_once_with(1)


def test_no_change_when_absent(run_module):
    client = _client(None)
    result, unused = run_module(mod, _params(state="absent", name="nonexistent-tag", color=None), client)
    assert result["changed"] is False
    client.delete_tag.assert_not_called()


def test_check_mode_create(run_module):
    client = _client(None)
    result, unused = run_module(mod, _params(name="new-tag"), client, check_mode=True)
    assert result["changed"] is True
    client.add_tag.assert_not_called()


def test_check_mode_delete(run_module):
    client = _client(EXISTING)
    result, unused = run_module(mod, _params(state="absent", color=None), client, check_mode=True)
    assert result["changed"] is True
    client.delete_tag.assert_not_called()
