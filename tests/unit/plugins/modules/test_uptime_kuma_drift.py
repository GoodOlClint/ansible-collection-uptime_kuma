# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Drift-detection tests for status_page, maintenance, api_key and monitor_tag."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock

from plugins.modules import (
    uptime_kuma_api_key,
    uptime_kuma_maintenance,
    uptime_kuma_monitor_tag,
    uptime_kuma_status_page,
)

PAGE_PARAMS = dict(state="present", slug="p", title="T", description="A", theme="auto", published=True, show_tags=False,
                   show_powered_by=True, show_certificate_expiry=False, custom_css="", footer_text=None,
                   google_analytics_id=None, domain_name_list=None, public_group_list=None)
PAGE = dict(id=1, slug="p", title="T", description="A", theme="auto", published=True, showTags=False,
            showPoweredBy=True, showCertificateExpiry=False, customCSS="", incident=None, maintenanceList=[],
            publicGroupList=[{"id": 9, "name": "Web", "weight": 1, "monitorList": [{"id": 2}, {"id": 1}]}])


def test_status_page_description_drift_is_applied(run_module):
    client = MagicMock()
    client.get_status_page_config.return_value = {"id": 1}
    client.get_status_page.side_effect = [PAGE, dict(PAGE, description="B")]
    result, unused = run_module(uptime_kuma_status_page, dict(PAGE_PARAMS, description="B"), client)
    assert result["changed"] is True
    assert client.save_status_page.call_args.kwargs["description"] == "B"
    assert "incident" not in result["diff"]["before"]


def test_status_page_groups_compare_by_name_and_monitor_ids(run_module):
    same = [{"name": "Web", "monitorList": [{"id": 2}, {"id": 1}]}]
    client = MagicMock()
    client.get_status_page_config.return_value = {"id": 1}
    client.get_status_page.return_value = PAGE
    result, unused = run_module(uptime_kuma_status_page, dict(PAGE_PARAMS, public_group_list=same), client)
    assert result["changed"] is False

    reordered = [{"name": "Web", "monitorList": [{"id": 1}, {"id": 2}]}]
    result, unused = run_module(uptime_kuma_status_page, dict(PAGE_PARAMS, public_group_list=reordered), client,
                                check_mode=True)
    assert result["changed"] is True
    assert result["diff"]["after"]["publicGroupList"] == reordered

    bad = [{"name": "Web", "monitorList": [1]}]
    result, unused = run_module(uptime_kuma_status_page, dict(PAGE_PARAMS, public_group_list=bad), client)
    assert result.get("failed") is True


def test_status_page_without_groups_does_not_fetch_the_public_page(run_module):
    client = MagicMock()
    client.get_status_page_config.return_value = {k: v for k, v in PAGE.items() if k != "publicGroupList"}
    result, unused = run_module(uptime_kuma_status_page, dict(PAGE_PARAMS), client)
    assert result["changed"] is False
    client.get_status_page.assert_not_called()


def test_status_page_check_mode_create_includes_identity(run_module):
    client = MagicMock()
    client.get_status_page_config.return_value = None
    result, unused = run_module(uptime_kuma_status_page, dict(PAGE_PARAMS), client, check_mode=True)
    assert result["status_page"]["slug"] == "p" and result["status_page"]["title"] == "T"


MAINT_PARAMS = dict(state="present", title="m", strategy="manual", active=True, description="", date_range=None,
                    interval_day=1, weekdays=None, days_of_month=None, time_range=None, cron="30 3 * * *",
                    duration_minutes=60, timezone=None)
MAINT = dict(id=3, title="m", strategy="manual", active=True, description="", intervalDay=1, timezoneOption=None)


def test_maintenance_timezone_is_compared_when_supplied(run_module):
    client = MagicMock()
    client.get_maintenance_by_title.return_value = dict(MAINT, timezoneOption="UTC")
    client.get_maintenance.return_value = MAINT
    result, unused = run_module(uptime_kuma_maintenance, dict(MAINT_PARAMS, timezone="SAME_AS_SERVER"), client)
    assert result["changed"] is False

    client.get_maintenance.side_effect = [MAINT, dict(MAINT, timezoneOption="UTC")]
    result, unused = run_module(uptime_kuma_maintenance, dict(MAINT_PARAMS, timezone="UTC"), client)
    assert result["changed"] is True
    assert client.edit_maintenance.call_args.kwargs["timezoneOption"] == "UTC"


def test_api_key_expiry_drift_fails_instead_of_ignoring(run_module):
    params = dict(state="present", name="k", active=True, expires="2027-01-01 00:00:00")
    client = MagicMock()
    client.get_api_key_by_name.return_value = {"id": 1, "name": "k", "active": True, "expires": "2027-01-01 00:00:00"}
    result, unused = run_module(uptime_kuma_api_key, dict(params, expires="2030-01-01 00:00:00"), client)
    assert result.get("failed") is True
    client.enable_api_key.assert_not_called()

    result, unused = run_module(uptime_kuma_api_key, params, client)
    assert result["changed"] is False

    client.get_api_key_by_name.return_value = {"id": 1, "name": "k", "active": True,
                                               "expires": "2027-01-01T00:00:00.000Z"}
    result, unused = run_module(uptime_kuma_api_key, params, client)
    assert result["changed"] is False


def _null_tag_client():
    client = MagicMock()
    client.get_tag_by_name.return_value = {"id": 4}
    client.get_monitor_by_name.return_value = {"id": 7, "tags": [{"tag_id": 4, "value": None}]}
    return client


def test_monitor_tag_absent_on_null_value_fails_loudly(run_module):
    client = _null_tag_client()
    result, unused = run_module(uptime_kuma_monitor_tag, dict(state="absent", tag_name="t", monitor_name="m", value=""),
                                client)
    assert result.get("failed") is True
    client.delete_monitor_tag.assert_not_called()


def test_maintenance_time_range_carries_seconds():
    module = MagicMock(params=dict(MAINT_PARAMS, strategy="recurring-weekday", weekdays=[1],
                                   time_range=[{"hours": 2, "minutes": 0}]))
    kwargs = uptime_kuma_maintenance._build_maintenance_kwargs(module)
    assert kwargs["timeRange"] == [{"hours": 2, "minutes": 0, "seconds": 0}]


def test_monitor_tag_matches_null_value_as_empty(run_module):
    client = _null_tag_client()
    params = dict(state="present", tag_name="t", monitor_name="m", value="")
    result, unused = run_module(uptime_kuma_monitor_tag, params, client)
    assert result["changed"] is False
    client.add_monitor_tag.assert_not_called()
