# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/module_utils/uptime_kuma_api.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
from enum import Enum

# Ensure the collection path is importable
sys.path.insert(0, ".")

from plugins.module_utils.uptime_kuma_api import (  # noqa: E402
    compute_diff,
    needs_update,
    normalize_result,
    serialize_value,
    uptime_kuma_argument_spec,
)


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
    # current doesn't have color, but desired wants it
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
