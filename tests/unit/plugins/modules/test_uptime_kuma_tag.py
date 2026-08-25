# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/modules/uptime_kuma_tag.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock, patch


def _run_module(module_args, check_mode=False):
    """Helper to execute the tag module with mocked dependencies."""
    from plugins.modules import uptime_kuma_tag

    mock_module = MagicMock()
    mock_module.params = {
        "api_url": "http://localhost:3001",
        "api_username": "admin",
        "api_password": "secret",
        "api_token": None,
        "validate_certs": True,
        "api_timeout": 10,
        "state": "present",
        "name": "test-tag",
        "color": "#ff0000",
    }
    mock_module.params.update(module_args)
    mock_module.check_mode = check_mode

    # Capture exit_json / fail_json calls
    result = {}

    def mock_exit_json(**kwargs):
        result.update(kwargs)
        result["failed"] = False

    def mock_fail_json(**kwargs):
        result.update(kwargs)
        result["failed"] = True

    mock_module.exit_json = mock_exit_json
    mock_module.fail_json = mock_fail_json

    mock_client = MagicMock()

    with patch.object(uptime_kuma_tag, "UptimeKumaClient", return_value=mock_client):
        uptime_kuma_tag._run(mock_module, mock_client)

    return result, mock_client


class TestTagPresent:
    def test_create_new_tag(self):
        """Create a tag when it does not exist."""
        result, client = _run_module({"name": "new-tag", "color": "#ff0000"})
        client.get_tag_by_name.return_value = None
        client.add_tag.return_value = {"id": 1, "name": "new-tag", "color": "#ff0000"}

        # Re-run with properly configured mocks
        result, client = _run_module({"name": "new-tag", "color": "#ff0000"})
        client.get_tag_by_name.return_value = None
        client.add_tag.return_value = {"id": 1, "name": "new-tag", "color": "#ff0000"}
        from plugins.modules import uptime_kuma_tag

        mock_module = MagicMock()
        mock_module.params = {
            "api_url": "http://localhost:3001",
            "api_username": "admin",
            "api_password": "secret",
            "api_token": None,
            "validate_certs": True,
            "api_timeout": 10,
            "state": "present",
            "name": "new-tag",
            "color": "#ff0000",
        }
        mock_module.check_mode = False
        exit_result = {}
        mock_module.exit_json = lambda **kw: exit_result.update(kw)
        mock_module.fail_json = lambda **kw: exit_result.update(kw, failed=True)

        uptime_kuma_tag._run(mock_module, client)
        assert exit_result.get("changed") is True
        client.add_tag.assert_called_once_with(name="new-tag", color="#ff0000")

    def test_no_change_when_identical(self):
        """No change when tag already exists with same values."""
        from plugins.modules import uptime_kuma_tag

        mock_module = MagicMock()
        mock_module.params = {
            "api_url": "http://localhost:3001",
            "api_username": "admin",
            "api_password": "secret",
            "api_token": None,
            "validate_certs": True,
            "api_timeout": 10,
            "state": "present",
            "name": "existing-tag",
            "color": "#ff0000",
        }
        mock_module.check_mode = False
        exit_result = {}
        mock_module.exit_json = lambda **kw: exit_result.update(kw)

        client = MagicMock()
        client.get_tag_by_name.return_value = {
            "id": 1, "name": "existing-tag", "color": "#ff0000"
        }

        uptime_kuma_tag._run(mock_module, client)
        assert exit_result.get("changed") is False
        client.add_tag.assert_not_called()
        client.edit_tag.assert_not_called()

    def test_update_when_color_differs(self):
        """Update when tag exists but color differs."""
        from plugins.modules import uptime_kuma_tag

        mock_module = MagicMock()
        mock_module.params = {
            "api_url": "http://localhost:3001",
            "api_username": "admin",
            "api_password": "secret",
            "api_token": None,
            "validate_certs": True,
            "api_timeout": 10,
            "state": "present",
            "name": "existing-tag",
            "color": "#00ff00",
        }
        mock_module.check_mode = False
        exit_result = {}
        mock_module.exit_json = lambda **kw: exit_result.update(kw)

        client = MagicMock()
        client.get_tag_by_name.return_value = {
            "id": 1, "name": "existing-tag", "color": "#ff0000"
        }
        client.edit_tag.return_value = {
            "tag": {"id": 1, "name": "existing-tag", "color": "#00ff00"}
        }

        uptime_kuma_tag._run(mock_module, client)
        assert exit_result.get("changed") is True
        client.edit_tag.assert_called_once()


class TestTagAbsent:
    def test_delete_existing_tag(self):
        """Delete a tag that exists."""
        from plugins.modules import uptime_kuma_tag

        mock_module = MagicMock()
        mock_module.params = {
            "api_url": "http://localhost:3001",
            "api_username": "admin",
            "api_password": "secret",
            "api_token": None,
            "validate_certs": True,
            "api_timeout": 10,
            "state": "absent",
            "name": "existing-tag",
            "color": None,
        }
        mock_module.check_mode = False
        exit_result = {}
        mock_module.exit_json = lambda **kw: exit_result.update(kw)

        client = MagicMock()
        client.get_tag_by_name.return_value = {
            "id": 1, "name": "existing-tag", "color": "#ff0000"
        }

        uptime_kuma_tag._run(mock_module, client)
        assert exit_result.get("changed") is True
        client.delete_tag.assert_called_once_with(1)

    def test_no_change_when_absent(self):
        """No change when tag does not exist and state=absent."""
        from plugins.modules import uptime_kuma_tag

        mock_module = MagicMock()
        mock_module.params = {
            "api_url": "http://localhost:3001",
            "api_username": "admin",
            "api_password": "secret",
            "api_token": None,
            "validate_certs": True,
            "api_timeout": 10,
            "state": "absent",
            "name": "nonexistent-tag",
            "color": None,
        }
        mock_module.check_mode = False
        exit_result = {}
        mock_module.exit_json = lambda **kw: exit_result.update(kw)

        client = MagicMock()
        client.get_tag_by_name.return_value = None

        uptime_kuma_tag._run(mock_module, client)
        assert exit_result.get("changed") is False
        client.delete_tag.assert_not_called()


class TestTagCheckMode:
    def test_check_mode_create(self):
        """Check mode reports change for new tag without creating."""
        from plugins.modules import uptime_kuma_tag

        mock_module = MagicMock()
        mock_module.params = {
            "api_url": "http://localhost:3001",
            "api_username": "admin",
            "api_password": "secret",
            "api_token": None,
            "validate_certs": True,
            "api_timeout": 10,
            "state": "present",
            "name": "new-tag",
            "color": "#ff0000",
        }
        mock_module.check_mode = True
        exit_result = {}
        mock_module.exit_json = lambda **kw: exit_result.update(kw)

        client = MagicMock()
        client.get_tag_by_name.return_value = None

        uptime_kuma_tag._run(mock_module, client)
        assert exit_result.get("changed") is True
        client.add_tag.assert_not_called()

    def test_check_mode_delete(self):
        """Check mode reports change for existing tag without deleting."""
        from plugins.modules import uptime_kuma_tag

        mock_module = MagicMock()
        mock_module.params = {
            "api_url": "http://localhost:3001",
            "api_username": "admin",
            "api_password": "secret",
            "api_token": None,
            "validate_certs": True,
            "api_timeout": 10,
            "state": "absent",
            "name": "existing-tag",
            "color": None,
        }
        mock_module.check_mode = True
        exit_result = {}
        mock_module.exit_json = lambda **kw: exit_result.update(kw)

        client = MagicMock()
        client.get_tag_by_name.return_value = {
            "id": 1, "name": "existing-tag", "color": "#ff0000"
        }

        uptime_kuma_tag._run(mock_module, client)
        assert exit_result.get("changed") is True
        client.delete_tag.assert_not_called()
