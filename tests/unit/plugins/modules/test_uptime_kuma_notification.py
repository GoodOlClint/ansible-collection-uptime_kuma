# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/modules/uptime_kuma_notification.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock

from plugins.modules import uptime_kuma_notification

SERVER = {"id": 1, "name": "mail", "type": "smtp", "isDefault": False, "active": True,
          "smtpHost": "mail.example.com", "smtpPassword": "hunter2"}


def _module(check_mode=False, **params):
    module = MagicMock()
    module.params = {
        "state": "present", "name": "mail", "notification_type": "smtp", "is_default": False,
        "apply_existing": False,
        "notification_config": {"smtpHost": "mail.example.com", "smtpPassword": "hunter2"},
    }
    module.params.update(params)
    module.check_mode = check_mode
    result = {}
    module.exit_json = lambda **kw: result.update(kw)
    module.fail_json = lambda **kw: result.update(kw, failed=True)
    return module, result


def _no_secret(result, key="notification"):
    for obj in [result[key]] + list(result.get("diff", {}).values()):
        assert set(obj) <= uptime_kuma_notification._RETURNED_KEYS, obj


def test_unmask_benign_config_keeps_credential_looking_keys_masked():
    module = MagicMock()
    module.no_log_values = {"mail.example.com", "25", "hunter2", "https://hooks.example/abc", "True"}
    uptime_kuma_notification._unmask_benign_config(
        module, {"smtpHost": "mail.example.com", "smtpPort": 25, "smtpPassword": "hunter2",
                 "slackwebhookURL": "https://hooks.example/abc", "smtpSecure": True, "smtpFrom": "hunter2"})
    assert module.no_log_values == {"hunter2", "https://hooks.example/abc", "True"}


def test_create_returns_server_object_without_credentials():
    module, result = _module()
    client = MagicMock()
    client.get_notification_by_name.return_value = None
    client.add_notification.return_value = {"id": 1}
    client.get_notification.return_value = SERVER

    uptime_kuma_notification._run(module, client)

    assert result["changed"] is True
    assert result["notification"] == {"id": 1, "name": "mail", "type": "smtp", "isDefault": False, "active": True}
    _no_secret(result)


def test_check_mode_create_scrubs_the_requested_config():
    module, result = _module(check_mode=True)
    client = MagicMock()
    client.get_notification_by_name.return_value = None

    uptime_kuma_notification._run(module, client)

    assert result["changed"] is True
    _no_secret(result)


def test_update_and_delete_scrub_existing_object():
    module, result = _module(is_default=True)
    client = MagicMock()
    client.get_notification_by_name.return_value = SERVER
    client.get_notification.return_value = dict(SERVER, isDefault=True)
    uptime_kuma_notification._run(module, client)
    assert result["changed"] is True
    _no_secret(result)

    module, result = _module(state="absent")
    client.get_notification_by_name.return_value = SERVER
    uptime_kuma_notification._run(module, client)
    assert result["changed"] is True
    _no_secret(result)


def test_no_change_still_scrubs():
    module, result = _module()
    client = MagicMock()
    client.get_notification_by_name.return_value = SERVER
    uptime_kuma_notification._run(module, client)
    assert result["changed"] is False
    _no_secret(result)


def test_config_drift_is_applied():
    module, result = _module(notification_config={"smtpHost": "new.example.com", "smtpPassword": "hunter2"})
    client = MagicMock()
    client.get_notification_by_name.return_value = SERVER
    client.get_notification.return_value = dict(SERVER, smtpHost="new.example.com")
    uptime_kuma_notification._run(module, client)
    assert result["changed"] is True
    assert client.edit_notification.call_args.kwargs["smtpHost"] == "new.example.com"


def test_credential_rotation_is_applied_once():
    module, result = _module(notification_config={"smtpHost": "mail.example.com", "smtpPassword": "rotated"})
    client = MagicMock()
    client.get_notification_by_name.return_value = SERVER
    client.get_notification.return_value = dict(SERVER, smtpPassword="rotated")
    uptime_kuma_notification._run(module, client)
    assert result["changed"] is True
    assert client.edit_notification.call_args.kwargs["smtpPassword"] == "rotated"
    _no_secret(result)

    module, result = _module(notification_config={"smtpHost": "mail.example.com", "smtpPassword": "rotated"})
    client.get_notification_by_name.return_value = dict(SERVER, smtpPassword="rotated")
    uptime_kuma_notification._run(module, client)
    assert result["changed"] is False
