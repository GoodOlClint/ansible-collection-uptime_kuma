# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Uptime Kuma 2.x Socket.IO client for the goodolclint.uptime_kuma collection.

:class:`UptimeKumaClient` is the single protocol layer; modules never emit
Socket.IO events themselves. Event names and payload shapes are pinned by the
integration tests against ``louislam/uptime-kuma:2`` (see ADR 0001).
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import threading

from ansible.module_utils.urls import open_url

try:
    import socketio
    HAS_SOCKETIO = True
except ImportError:
    HAS_SOCKETIO = False

SOCKETIO_IMPORT_ERROR = (
    "The 'python-socketio' package is required by this module. "
    "Install it with: pip install 'python-socketio[client]>=5.0'"
)

# Lists the server pushes as events; the getter (if any) forces a re-push.
# Monitor mutations push incremental updateMonitorIntoList/deleteMonitorFromList
# events instead, so monitor code re-reads by id rather than waiting on the list.
_PUSHED_LISTS = {
    "monitorList": "getMonitorList",
    "notificationList": None,
    "maintenanceList": "getMaintenanceList",
    "statusPageList": None,
    "apiKeyList": "getAPIKeyList",
}

MONITOR_DEFAULTS = {
    "interval": 60,
    "retryInterval": 60,
    "resendInterval": 0,
    "maxretries": 0,
    "timeout": 48,
    "upsideDown": False,
    "ignoreTls": False,
    "expiryNotification": False,
    "maxredirects": 10,
    "method": "GET",
    "accepted_statuscodes": ["200-299"],
    "packetSize": 56,
    "dns_resolve_type": "A",
    "dns_resolve_server": "1.1.1.1",
    "jsonPathOperator": "==",
    "invertKeyword": False,
    "notificationIDList": {},
    "conditions": [],
}

# jsonToBean indexes these lists unconditionally, so they must always be present.
MAINTENANCE_DEFAULTS = {
    "active": True,
    "description": "",
    "strategy": "manual",
    "intervalDay": 1,
    "dateRange": [],
    "timeRange": [{"hours": 2, "minutes": 0}, {"hours": 3, "minutes": 0}],
    "weekdays": [],
    "daysOfMonth": [],
    "cron": "30 3 * * *",
    "durationMinutes": 60,
    "timezoneOption": None,
}

# Read-only keys in getMonitor's reply that editMonitor must not receive back.
_MONITOR_READONLY = {"tags", "childrenIDs", "path", "pathName", "maintenance",
                     "screenshot", "dns_last_result", "includeSensitiveData"}


# Per-attempt ack timeout for retried requests; must exceed the server's password
# login latency (~3.5 s on Uptime Kuma 2.5), see _call.
_RETRY_TIMEOUT = 10


class UptimeKumaError(Exception):
    """Raised when the server answers ``ok: false`` or does not answer."""


def uptime_kuma_argument_spec():
    """Return the base argument spec shared by every module."""
    return dict(
        api_url=dict(type="str", required=True),
        api_username=dict(type="str", required=False, default=None),
        api_password=dict(type="str", required=False, default=None, no_log=True),
        api_token=dict(type="str", required=False, default=None, no_log=True),
        validate_certs=dict(type="bool", default=True),
        api_timeout=dict(type="int", default=30),
    )


class UptimeKumaClient:
    """Connection, authentication and one method per server event.

    Parameters
    ----------
    module : AnsibleModule
        Used for connection parameters and ``fail_json`` on unrecoverable errors.
    login : bool
        Skip authentication (only ``need_setup`` / ``setup`` are usable then).
    """

    def __init__(self, module, login=True):
        self.module = module
        if not HAS_SOCKETIO:
            module.fail_json(msg=SOCKETIO_IMPORT_ERROR)

        params = module.params
        self.url = params["api_url"].rstrip("/")
        self.timeout = params.get("api_timeout", 30)
        self._lists = {}
        self._events = {name: threading.Event() for name in _PUSHED_LISTS}
        self._events["info"] = threading.Event()

        self._sio = socketio.Client(
            ssl_verify=params.get("validate_certs", True),
            request_timeout=self.timeout,
        )
        for name in list(_PUSHED_LISTS) + ["info"]:
            self._sio.on(name, self._store(name))
        try:
            self._sio.connect(self.url, wait_timeout=self.timeout)
        except socketio.exceptions.SocketIOError as exc:
            module.fail_json(msg=f"Failed to connect to Uptime Kuma at {self.url}: {exc}")

        if login:
            self._authenticate(params)

    def _store(self, name):
        def handler(data):
            self._lists[name] = data
            self._events[name].set()
        return handler

    def _authenticate(self, params):
        """Log in; ``self.token`` holds the JWT afterwards.

        Password logins are rate-limited server-side (20/min); token logins are
        not, so callers that run many tasks should log in once and reuse the token.
        """
        self.token = params.get("api_token")
        try:
            if self.token:
                self._call("loginByToken", self.token, retry=True)
            else:
                reply = self._call("login", {
                    "username": params.get("api_username") or "",
                    "password": params.get("api_password") or "",
                    "token": "",
                }, retry=True)
                self.token = reply.get("token")
        except UptimeKumaError as exc:
            self.disconnect()
            self.module.fail_json(msg=f"Authentication failed: {exc}")

    def disconnect(self):
        try:
            self._sio.disconnect()
        except Exception:  # noqa: BLE001
            pass

    # ── protocol primitives ─────────────────────────────────────────────

    def _call(self, event, *args, retry=False):
        """Emit *event* and return its ack; raise on ``ok: false``.

        The server registers its handlers only after an awaited ``info`` push,
        so the first requests after connect can be dropped; ``retry`` re-sends
        idempotent ones (login, loginByToken, needSetup, setup). Each attempt
        waits ``_RETRY_TIMEOUT``, not ``api_timeout``: it must be long enough
        for a real reply (a password login takes ~3.5 s on 2.5, and a timed-out
        login still succeeds server-side and consumes the 20/min budget) but
        short enough that a genuinely dropped request is re-sent promptly.
        """
        data = args[0] if len(args) == 1 else (args or None)
        attempts = 5 if retry else 1
        for attempt in range(attempts):
            try:
                reply = self._sio.call(event, data, timeout=(_RETRY_TIMEOUT if retry else self.timeout))
                break
            except socketio.exceptions.TimeoutError as exc:
                if attempt == attempts - 1:
                    raise UptimeKumaError(f"Timed out waiting for '{event}' reply") from exc
        if isinstance(reply, dict) and "ok" in reply:
            if not reply["ok"]:
                raise UptimeKumaError(reply.get("msg") or f"'{event}' failed")
            reply = dict(reply)
            reply.pop("ok")
        return reply

    def _list(self, name, refresh=True):
        """Return the server-pushed list *name*, forcing a re-push when possible."""
        getter = _PUSHED_LISTS[name]
        if refresh and getter:
            self._events[name].clear()
            self._call(getter)
        if not self._events[name].wait(self.timeout):
            raise UptimeKumaError(f"Timed out waiting for '{name}' event")
        return self._lists.get(name)

    def _expect(self, name, func):
        """Run *func* and wait for the server to re-push list *name*."""
        self._events[name].clear()
        result = func()
        self._events[name].wait(self.timeout)
        return result

    @property
    def version(self):
        self._events["info"].wait(self.timeout)
        return (self._lists.get("info") or {}).get("version")

    # ── setup ───────────────────────────────────────────────────────────

    def need_setup(self):
        return bool(self._call("needSetup", retry=True))

    def setup(self, username, password):
        return self._call("setup", username, password, retry=True)

    # ── monitors ────────────────────────────────────────────────────────

    @staticmethod
    def _monitor_out(monitor):
        monitor = dict(monitor)
        ids = monitor.get("notificationIDList") or {}
        if isinstance(ids, dict):
            monitor["notificationIDList"] = sorted(int(i) for i in ids)
        monitor["active"] = bool(monitor.get("active"))
        return monitor

    @staticmethod
    def _monitor_in(data):
        ids = data.get("notificationIDList") or {}
        if isinstance(ids, list):
            data["notificationIDList"] = {str(i): True for i in ids}
        if not data.get("accepted_statuscodes"):
            data["accepted_statuscodes"] = ["200-299"]
        return data

    def get_monitors(self):
        return [self._monitor_out(m) for m in (self._list("monitorList") or {}).values()]

    def get_monitor(self, monitor_id):
        return self._monitor_out(self._call("getMonitor", monitor_id)["monitor"])

    def get_monitor_by_name(self, name):
        for mon in self.get_monitors():
            if mon.get("name") == name:
                return mon
        return None

    def add_monitor(self, **kwargs):
        data = dict(MONITOR_DEFAULTS)
        data.update(kwargs)
        return self._call("add", self._monitor_in(data))

    def edit_monitor(self, monitor_id, **kwargs):
        data = {k: v for k, v in self._call("getMonitor", monitor_id)["monitor"].items()
                if k not in _MONITOR_READONLY}
        data.update(kwargs)
        return self._call("editMonitor", self._monitor_in(data))

    def delete_monitor(self, monitor_id):
        return self._call("deleteMonitor", monitor_id)

    def pause_monitor(self, monitor_id):
        return self._call("pauseMonitor", monitor_id)

    def resume_monitor(self, monitor_id):
        return self._call("resumeMonitor", monitor_id)

    # ── notifications ───────────────────────────────────────────────────

    def get_notifications(self):
        result = []
        for raw in self._list("notificationList", refresh=False) or []:
            notif = dict(raw)
            config = json.loads(notif.pop("config", None) or "{}")
            notif.update(config)
            result.append(notif)
        return result

    def get_notification(self, notification_id):
        for notif in self.get_notifications():
            if notif.get("id") == notification_id:
                return notif
        raise UptimeKumaError(f"notification {notification_id} not found")

    def get_notification_by_name(self, name):
        for notif in self.get_notifications():
            if notif.get("name") == name:
                return notif
        return None

    def add_notification(self, **kwargs):
        return self._expect("notificationList", lambda: self._call("addNotification", kwargs, None))

    def edit_notification(self, notification_id, **kwargs):
        data = self.get_notification(notification_id)
        data.update(kwargs)
        return self._expect("notificationList",
                            lambda: self._call("addNotification", data, notification_id))

    def delete_notification(self, notification_id):
        return self._expect("notificationList", lambda: self._call("deleteNotification", notification_id))

    # ── tags ────────────────────────────────────────────────────────────

    def get_tags(self):
        return self._call("getTags")["tags"]

    def get_tag(self, tag_id):
        for tag in self.get_tags():
            if tag.get("id") == tag_id:
                return tag
        raise UptimeKumaError(f"tag {tag_id} not found")

    def get_tag_by_name(self, name):
        for tag in self.get_tags():
            if tag.get("name") == name:
                return tag
        return None

    def add_tag(self, name, color):
        return self._call("addTag", {"name": name, "color": color})["tag"]

    def edit_tag(self, tag_id, name, color):
        return self._call("editTag", {"id": tag_id, "name": name, "color": color})

    def delete_tag(self, tag_id):
        return self._call("deleteTag", tag_id)

    # ── monitor tags ────────────────────────────────────────────────────

    def add_monitor_tag(self, tag_id, monitor_id, value=""):
        return self._call("addMonitorTag", tag_id, monitor_id, value)

    def delete_monitor_tag(self, tag_id, monitor_id, value=""):
        return self._call("deleteMonitorTag", tag_id, monitor_id, value)

    # ── status pages ────────────────────────────────────────────────────

    def get_status_pages(self):
        """Status pages as pushed at login; the server never re-pushes this list."""
        return list((self._list("statusPageList", refresh=False) or {}).values())

    def get_status_page_config(self, slug):
        """Return the page config for *slug*, or None if no such page."""
        try:
            return self._call("getStatusPage", slug)["config"]
        except UptimeKumaError:
            return None

    def get_status_page(self, slug):
        config = self._call("getStatusPage", slug)["config"]
        resp = open_url(f"{self.url}/api/status-page/{slug}", timeout=self.timeout,
                        validate_certs=self.module.params.get("validate_certs", True))
        public = json.loads(resp.read())
        config.update(public.get("config") or {})
        return {
            **config,
            "incident": public.get("incident"),
            "publicGroupList": public.get("publicGroupList") or [],
            "maintenanceList": public.get("maintenanceList") or [],
        }

    def add_status_page(self, slug, title):
        return self._call("addStatusPage", title, slug)

    def save_status_page(self, slug, **kwargs):
        page = self.get_status_page(slug)
        page.pop("incident", None)
        page.pop("maintenanceList", None)
        page.update(kwargs)
        public_group_list = page.pop("publicGroupList", [])
        img_data_url = page.pop("icon", "/icon.svg")
        page.setdefault("theme", "auto")
        page.setdefault("published", True)
        page.setdefault("showTags", False)
        page.setdefault("domainNameList", [])
        page.setdefault("customCSS", "")
        page.setdefault("showPoweredBy", True)
        page.setdefault("showCertificateExpiry", False)
        return self._call("saveStatusPage", slug, page, img_data_url, public_group_list)

    def delete_status_page(self, slug):
        return self._call("deleteStatusPage", slug)

    # ── maintenance ─────────────────────────────────────────────────────

    def get_maintenances(self):
        return list((self._list("maintenanceList") or {}).values())

    def get_maintenance(self, maintenance_id):
        return self._call("getMaintenance", maintenance_id)["maintenance"]

    def get_maintenance_by_title(self, title):
        for maint in self.get_maintenances():
            if maint.get("title") == title:
                return maint
        return None

    def add_maintenance(self, **kwargs):
        data = dict(MAINTENANCE_DEFAULTS)
        data.update(kwargs)
        return self._call("addMaintenance", data)

    def edit_maintenance(self, maintenance_id, **kwargs):
        data = self.get_maintenance(maintenance_id)
        data.update(kwargs)
        return self._call("editMaintenance", data)

    def delete_maintenance(self, maintenance_id):
        return self._call("deleteMaintenance", maintenance_id)

    def pause_maintenance(self, maintenance_id):
        return self._call("pauseMaintenance", maintenance_id)

    def resume_maintenance(self, maintenance_id):
        return self._call("resumeMaintenance", maintenance_id)

    # ── api keys ────────────────────────────────────────────────────────

    def get_api_keys(self):
        keys = []
        for key in self._list("apiKeyList") or []:
            key = dict(key)
            key["active"] = bool(key.get("active"))
            keys.append(key)
        return keys

    def get_api_key(self, key_id):
        for key in self.get_api_keys():
            if key.get("id") == key_id:
                return key
        raise UptimeKumaError(f"API key {key_id} not found")

    def get_api_key_by_name(self, name):
        for key in self.get_api_keys():
            if key.get("name") == name:
                return key
        return None

    def add_api_key(self, name, expires, active):
        data = {"name": name, "expires": expires, "active": 1 if active else 0}
        return self._expect("apiKeyList", lambda: self._call("addAPIKey", data))

    def enable_api_key(self, key_id):
        return self._expect("apiKeyList", lambda: self._call("enableAPIKey", key_id))

    def disable_api_key(self, key_id):
        return self._expect("apiKeyList", lambda: self._call("disableAPIKey", key_id))

    def delete_api_key(self, key_id):
        return self._expect("apiKeyList", lambda: self._call("deleteAPIKey", key_id))

    # ── settings ────────────────────────────────────────────────────────

    def get_settings(self):
        return self._call("getSettings")["data"]

    def set_settings(self, password=None, **kwargs):
        data = self.get_settings()
        data.update(kwargs)
        return self._call("setSettings", data, password)


# ── helper functions ────────────────────────────────────────────────────

def serialize_value(value):
    if hasattr(value, "value"):
        return value.value
    return value


def normalize_result(data):
    """Return *data* with any enum-like values replaced by their ``.value``."""
    if isinstance(data, dict):
        return {k: normalize_result(v) for k, v in data.items()}
    if isinstance(data, list):
        return [normalize_result(item) for item in data]
    return serialize_value(data)


def compute_diff(before, after, exclude_keys=None):
    """Return ``{"before": ..., "after": ...}`` with *exclude_keys* removed."""
    if exclude_keys is None:
        exclude_keys = set()

    def _clean(d):
        if d is None:
            return {}
        return {k: v for k, v in d.items() if k not in exclude_keys}

    return {
        "before": normalize_result(_clean(before)),
        "after": normalize_result(_clean(after)),
    }


def scrub(data, keys):
    """Return *data* without *keys* (for results that must not carry credentials)."""
    if not isinstance(data, dict):
        return data
    return {k: v for k, v in data.items() if k not in keys}


def _comparable(value):
    value = serialize_value(value)
    if isinstance(value, dict) and value and all(v is True for v in value.values()):
        return sorted(int(k) for k in value)
    if isinstance(value, list) and all(isinstance(v, int) for v in value):
        return sorted(value)
    return value


def needs_update(current, desired, exclude_keys=None):
    """Return True if any non-None key in *desired* differs from *current*."""
    if exclude_keys is None:
        exclude_keys = set()

    for key, desired_val in desired.items():
        if key in exclude_keys or desired_val is None:
            continue
        if _comparable(current.get(key)) != _comparable(desired_val):
            return True
    return False
