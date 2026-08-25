# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/modules/uptime_kuma_status_page.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock

from plugins.module_utils.uptime_kuma_api import UptimeKumaServerError
from plugins.modules import uptime_kuma_status_page as mod

PARAMS = dict(state="present", slug="p", title="T", description=None, theme="auto", published=True, show_tags=False,
              show_powered_by=True, show_certificate_expiry=False, custom_css="", footer_text=None,
              google_analytics_id=None, domain_name_list=None, public_group_list=None)
CONFIG = dict(id=1, slug="p", title="T", description="", theme="auto", published=True, showTags=False,
              showPoweredBy=True, showCertificateExpiry=False, customCSS="", incident={"title": "x"},
              maintenanceList=[])
PAGE = dict(CONFIG, incident=None, maintenanceList=[], publicGroupList=[])


def _params(**over):
    return dict(PARAMS, **over)


def test_create_adds_then_saves_the_config(run_module):
    client = MagicMock()
    client.get_status_page_config.side_effect = [None, CONFIG, dict(CONFIG, description="d")]
    result, unused = run_module(mod, _params(description="d"), client)
    assert result["changed"] is True and result["status_page"]["slug"] == "p"
    client.add_status_page.assert_called_once_with("p", "T")
    saved = client.save_status_page.call_args
    assert saved.args == ("p",)
    assert saved.kwargs["id"] == 1 and saved.kwargs["title"] == "T" and saved.kwargs["description"] == "d"


def test_unchanged_and_absent(run_module):
    client = MagicMock()
    client.get_status_page_config.return_value = CONFIG
    result, unused = run_module(mod, _params(), client)
    assert result["changed"] is False
    client.save_status_page.assert_not_called()
    client.get_status_page.assert_not_called()

    result, unused = run_module(mod, _params(state="absent"), client, check_mode=True)
    assert result["changed"] is True and "incident" not in result["diff"]["before"]
    client.delete_status_page.assert_not_called()

    result, unused = run_module(mod, _params(state="absent"), client)
    assert result["changed"] is True and result["status_page"] == {}
    client.delete_status_page.assert_called_once_with("p")

    client.get_status_page_config.return_value = None
    result, unused = run_module(mod, _params(state="absent"), client)
    assert result["changed"] is False


def test_check_mode_update_predicts_without_saving(run_module):
    client = MagicMock()
    client.get_status_page_config.return_value = CONFIG
    result, unused = run_module(mod, _params(title="New"), client, check_mode=True)
    assert result["changed"] is True and result["diff"]["after"]["title"] == "New"
    client.save_status_page.assert_not_called()


def test_title_is_required_to_create(run_module):
    client = MagicMock()
    client.get_status_page_config.return_value = None
    result, unused = run_module(mod, _params(title=None), client)
    assert result.get("failed") is True
    client.add_status_page.assert_not_called()


def test_analytics_and_domains_are_sent_in_2x_shape(run_module):
    client = MagicMock()
    client.get_status_page_config.side_effect = [CONFIG, dict(CONFIG, analyticsId="G-1")]
    result, unused = run_module(mod, _params(google_analytics_id="G-1", domain_name_list=["s.example.com"]), client)
    assert result["changed"] is True
    saved = client.save_status_page.call_args.kwargs
    assert saved["analyticsId"] == "G-1" and saved["analyticsType"] == "google"
    assert saved["domainNameList"] == ["s.example.com"]


def test_managed_groups_read_the_page_once(run_module):
    groups = [{"name": "g", "monitorList": [{"id": 1}]}]
    client = MagicMock()
    client.get_status_page.return_value = dict(PAGE, publicGroupList=groups)
    result, unused = run_module(mod, _params(public_group_list=groups), client)
    assert result["changed"] is False
    client.get_status_page_config.assert_not_called()
    client.get_status_page.assert_called_once_with("p")

    client = MagicMock()
    client.get_status_page.side_effect = [UptimeKumaServerError("No slug?"), dict(PAGE, publicGroupList=groups)]
    client.get_status_page_config.return_value = CONFIG
    result, unused = run_module(mod, _params(public_group_list=groups), client)
    assert result["changed"] is True and result["status_page"]["publicGroupList"] == groups
    client.add_status_page.assert_called_once_with("p", "T")
    assert client.save_status_page.call_args.kwargs["publicGroupList"] == groups
