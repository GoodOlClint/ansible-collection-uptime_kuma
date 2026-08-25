# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+

"""Unit tests for plugins/modules/uptime_kuma_maintenance.py."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock

from plugins.modules import uptime_kuma_maintenance as mod

PARAMS = dict(state="present", title="w", strategy="manual", active=True, description="", date_range=None,
              interval_day=1, weekdays=None, days_of_month=None, time_range=None, cron="30 3 * * *",
              duration_minutes=60, timezone=None)
RAW = dict(id=3, title="w", strategy="manual", active=True, description="", intervalDay=1, timezoneOption=None)


def _params(**over):
    return dict(PARAMS, **over)


def test_cron_fields_are_only_sent_for_the_cron_strategy():
    module = MagicMock(params=_params(strategy="cron", cron="0 4 * * *", duration_minutes=30))
    kw = mod._build_maintenance_kwargs(module)
    assert kw["cron"] == "0 4 * * *" and kw["durationMinutes"] == 30
    kw = mod._build_maintenance_kwargs(MagicMock(params=_params(strategy="recurring-weekday", weekdays=[1, 3],
                                                                time_range=[{"hours": 1, "minutes": 0}])))
    assert "cron" not in kw and kw["weekdays"] == [1, 3]
    assert kw["timeRange"] == [{"hours": 1, "minutes": 0, "seconds": 0}]


def test_create_and_check_mode_create(run_module):
    client = MagicMock()
    client.get_maintenance_by_title.return_value = None
    client.add_maintenance.return_value = {"maintenanceID": 3}
    client.get_maintenance.return_value = RAW
    result, unused = run_module(mod, _params(), client)
    assert result["changed"] is True and result["maintenance"] == RAW
    assert client.add_maintenance.call_args.kwargs["strategy"] == "manual"

    client.reset_mock()
    result, unused = run_module(mod, _params(), client, check_mode=True)
    assert result["changed"] is True and result["maintenance"]["title"] == "w"
    client.add_maintenance.assert_not_called()


def test_unchanged_update_and_check_mode_update(run_module):
    client = MagicMock()
    client.get_maintenance_by_title.return_value = {"id": 3}
    client.get_maintenance.return_value = RAW
    result, unused = run_module(mod, _params(), client)
    assert result["changed"] is False

    client.get_maintenance.side_effect = [RAW, dict(RAW, description="d")]
    result, unused = run_module(mod, _params(description="d"), client)
    assert result["changed"] is True and result["diff"]["after"]["description"] == "d"
    assert client.edit_maintenance.call_args.args[0] == 3

    client.get_maintenance.side_effect = None
    client.edit_maintenance.reset_mock()
    result, unused = run_module(mod, _params(description="d"), client, check_mode=True)
    assert result["changed"] is True and result["diff"]["after"]["description"] == "d"
    client.edit_maintenance.assert_not_called()


def test_absent(run_module):
    client = MagicMock()
    client.get_maintenance_by_title.return_value = {"id": 3}
    client.get_maintenance.return_value = RAW
    result, unused = run_module(mod, _params(state="absent"), client)
    assert result["changed"] is True and result["diff"]["before"]["title"] == "w"
    client.delete_maintenance.assert_called_once_with(3)

    result, unused = run_module(mod, _params(state="absent"), client, check_mode=True)
    assert result["changed"] is True and client.delete_maintenance.call_count == 1

    client.get_maintenance_by_title.return_value = None
    result, unused = run_module(mod, _params(state="absent"), client)
    assert result["changed"] is False


def test_single_and_day_of_month_strategies_send_their_schedules():
    dates = ["2030-01-01 00:00:00", "2030-01-02 00:00:00"]
    kw = mod._build_maintenance_kwargs(MagicMock(params=_params(strategy="single", date_range=dates)))
    assert kw["dateRange"] == dates
    module = MagicMock(params=_params(strategy="recurring-day-of-month", days_of_month=[1, 15]))
    kw = mod._build_maintenance_kwargs(module)
    assert kw["daysOfMonth"] == [1, 15]
