# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module_utils wrapper for the uptime-kuma-api library.

Provides :class:`UptimeKumaClient`, the single entry-point for all Ansible
modules in the ``goodolclint.uptime_kuma`` collection.  It handles connection
lifecycle, authentication, and normalises every API call into
``(result, changed, diff)`` tuples suitable for ``AnsibleModule.exit_json``.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

try:
    from uptime_kuma_api import UptimeKumaApi, UptimeKumaException
    HAS_UPTIME_KUMA_API = True
except ImportError:
    HAS_UPTIME_KUMA_API = False

UPTIME_KUMA_API_IMPORT_ERROR = (
    "The 'uptime-kuma-api' Python package is required by this module. "
    "Install it with: pip install 'uptime-kuma-api>=1.2.0'"
)


# ── shared argument spec fragments ──────────────────────────────────────

def uptime_kuma_argument_spec():
    """Return the base argument spec shared by every module."""
    return dict(
        api_url=dict(
            type="str",
            required=True,
            fallback=(None, []),
        ),
        api_username=dict(
            type="str",
            required=False,
            default=None,
        ),
        api_password=dict(
            type="str",
            required=False,
            default=None,
            no_log=True,
        ),
        api_token=dict(
            type="str",
            required=False,
            default=None,
            no_log=True,
        ),
        validate_certs=dict(
            type="bool",
            default=True,
        ),
        api_timeout=dict(
            type="int",
            default=10,
        ),
    )


# ── client wrapper ──────────────────────────────────────────────────────

class UptimeKumaClient:
    """Thin wrapper around :class:`uptime_kuma_api.UptimeKumaApi`.

    Manages connection lifecycle and authentication so that individual
    Ansible modules do not need to repeat boilerplate.

    Parameters
    ----------
    module : AnsibleModule
        The calling module instance; used to read connection parameters
        and to call ``fail_json`` on unrecoverable errors.
    """

    def __init__(self, module):
        self.module = module
        self._api = None

        if not HAS_UPTIME_KUMA_API:
            module.fail_json(msg=UPTIME_KUMA_API_IMPORT_ERROR)

        params = module.params
        url = params["api_url"].rstrip("/")
        ssl_verify = params.get("validate_certs", True)
        timeout = params.get("api_timeout", 10)

        try:
            self._api = UptimeKumaApi(
                url,
                timeout=timeout,
                ssl_verify=ssl_verify,
            )
        except UptimeKumaException as exc:
            module.fail_json(
                msg=f"Failed to connect to Uptime Kuma at {url}: {exc}"
            )

        self._authenticate(params)

    def _authenticate(self, params):
        """Authenticate using token, username/password, or auto-login."""
        try:
            if params.get("api_token"):
                self._api.login_by_token(params["api_token"])
            elif params.get("api_username") and params.get("api_password"):
                self._api.login(params["api_username"], params["api_password"])
            else:
                # Attempt auto-login (disableAuth mode)
                self._api.login()
        except UptimeKumaException as exc:
            self.disconnect()
            self.module.fail_json(msg=f"Authentication failed: {exc}")

    def disconnect(self):
        """Disconnect from the Uptime Kuma server."""
        if self._api is not None:
            try:
                self._api.disconnect()
            except Exception:  # noqa: BLE001
                pass

    @property
    def api(self):
        """Return the underlying :class:`UptimeKumaApi` instance."""
        return self._api

    # ── monitors ────────────────────────────────────────────────────────

    def get_monitors(self):
        """Return all monitors as a list of dicts."""
        return self._api.get_monitors()

    def get_monitor(self, monitor_id):
        """Return a single monitor by ID."""
        return self._api.get_monitor(monitor_id)

    def get_monitor_by_name(self, name):
        """Return the first monitor matching *name*, or ``None``."""
        for mon in self.get_monitors():
            if mon.get("name") == name:
                return mon
        return None

    def add_monitor(self, **kwargs):
        """Create a monitor and return the result dict."""
        return self._api.add_monitor(**kwargs)

    def edit_monitor(self, monitor_id, **kwargs):
        """Edit an existing monitor."""
        return self._api.edit_monitor(monitor_id, **kwargs)

    def delete_monitor(self, monitor_id):
        """Delete a monitor by ID."""
        return self._api.delete_monitor(monitor_id)

    def pause_monitor(self, monitor_id):
        """Pause a monitor."""
        return self._api.pause_monitor(monitor_id)

    def resume_monitor(self, monitor_id):
        """Resume a monitor."""
        return self._api.resume_monitor(monitor_id)

    # ── notifications ───────────────────────────────────────────────────

    def get_notifications(self):
        """Return all notification providers."""
        return self._api.get_notifications()

    def get_notification(self, notification_id):
        """Return a single notification by ID."""
        return self._api.get_notification(notification_id)

    def get_notification_by_name(self, name):
        """Return the first notification matching *name*, or ``None``."""
        for notif in self.get_notifications():
            if notif.get("name") == name:
                return notif
        return None

    def add_notification(self, **kwargs):
        """Create a notification provider."""
        return self._api.add_notification(**kwargs)

    def edit_notification(self, notification_id, **kwargs):
        """Edit an existing notification provider."""
        return self._api.edit_notification(notification_id, **kwargs)

    def delete_notification(self, notification_id):
        """Delete a notification provider."""
        return self._api.delete_notification(notification_id)

    # ── tags ────────────────────────────────────────────────────────────

    def get_tags(self):
        """Return all tags."""
        return self._api.get_tags()

    def get_tag(self, tag_id):
        """Return a single tag by ID."""
        return self._api.get_tag(tag_id)

    def get_tag_by_name(self, name):
        """Return the first tag matching *name*, or ``None``."""
        for tag in self.get_tags():
            if tag.get("name") == name:
                return tag
        return None

    def add_tag(self, **kwargs):
        """Create a tag."""
        return self._api.add_tag(**kwargs)

    def edit_tag(self, tag_id, **kwargs):
        """Edit an existing tag."""
        return self._api.edit_tag(tag_id, **kwargs)

    def delete_tag(self, tag_id):
        """Delete a tag."""
        return self._api.delete_tag(tag_id)

    # ── monitor tags ────────────────────────────────────────────────────

    def add_monitor_tag(self, tag_id, monitor_id, value=""):
        """Assign a tag to a monitor."""
        return self._api.add_monitor_tag(tag_id, monitor_id, value)

    def delete_monitor_tag(self, tag_id, monitor_id, value=""):
        """Remove a tag from a monitor."""
        return self._api.delete_monitor_tag(tag_id, monitor_id, value)

    # ── status pages ────────────────────────────────────────────────────

    def get_status_pages(self):
        """Return all status pages."""
        return self._api.get_status_pages()

    def get_status_page(self, slug):
        """Return a single status page by slug."""
        return self._api.get_status_page(slug)

    def add_status_page(self, slug, title):
        """Create a status page."""
        return self._api.add_status_page(slug, title)

    def save_status_page(self, slug, **kwargs):
        """Save (update) a status page."""
        return self._api.save_status_page(slug, **kwargs)

    def delete_status_page(self, slug):
        """Delete a status page by slug."""
        return self._api.delete_status_page(slug)

    # ── maintenance ─────────────────────────────────────────────────────

    def get_maintenances(self):
        """Return all maintenance windows."""
        return self._api.get_maintenances()

    def get_maintenance(self, maintenance_id):
        """Return a single maintenance window by ID."""
        return self._api.get_maintenance(maintenance_id)

    def get_maintenance_by_title(self, title):
        """Return the first maintenance matching *title*, or ``None``."""
        for maint in self.get_maintenances():
            if maint.get("title") == title:
                return maint
        return None

    def add_maintenance(self, **kwargs):
        """Create a maintenance window."""
        return self._api.add_maintenance(**kwargs)

    def edit_maintenance(self, maintenance_id, **kwargs):
        """Edit an existing maintenance window."""
        return self._api.edit_maintenance(maintenance_id, **kwargs)

    def delete_maintenance(self, maintenance_id):
        """Delete a maintenance window."""
        return self._api.delete_maintenance(maintenance_id)

    def pause_maintenance(self, maintenance_id):
        """Pause a maintenance window."""
        return self._api.pause_maintenance(maintenance_id)

    def resume_maintenance(self, maintenance_id):
        """Resume a maintenance window."""
        return self._api.resume_maintenance(maintenance_id)

    # ── api keys ────────────────────────────────────────────────────────

    def get_api_keys(self):
        """Return all API keys."""
        return self._api.get_api_keys()

    def get_api_key(self, key_id):
        """Return a single API key by ID."""
        return self._api.get_api_key(key_id)

    def get_api_key_by_name(self, name):
        """Return the first API key matching *name*, or ``None``."""
        for key in self.get_api_keys():
            if key.get("name") == name:
                return key
        return None

    def add_api_key(self, name, expires, active):
        """Create an API key."""
        return self._api.add_api_key(name, expires, active)

    def enable_api_key(self, key_id):
        """Enable an API key."""
        return self._api.enable_api_key(key_id)

    def disable_api_key(self, key_id):
        """Disable an API key."""
        return self._api.disable_api_key(key_id)

    def delete_api_key(self, key_id):
        """Delete an API key."""
        return self._api.delete_api_key(key_id)

    # ── settings ────────────────────────────────────────────────────────

    def get_settings(self):
        """Return current instance settings."""
        return self._api.get_settings()

    def set_settings(self, **kwargs):
        """Update instance settings."""
        return self._api.set_settings(**kwargs)


# ── helper functions ────────────────────────────────────────────────────

def serialize_value(value):
    """Convert enum values and other non-serializable types to strings."""
    if hasattr(value, "value"):
        return value.value
    return value


def normalize_result(data):
    """Recursively convert API response dicts to plain JSON-safe dicts.

    The uptime-kuma-api library returns enum instances in many fields.
    Ansible requires all return data to be JSON-serializable.
    """
    if isinstance(data, dict):
        return {k: normalize_result(v) for k, v in data.items()}
    if isinstance(data, list):
        return [normalize_result(item) for item in data]
    return serialize_value(data)


def compute_diff(before, after, exclude_keys=None):
    """Build an Ansible-style diff dict.

    Parameters
    ----------
    before : dict or None
        The state before the change.
    after : dict or None
        The state after the change.
    exclude_keys : set, optional
        Keys to omit from both sides of the diff (e.g. write-only fields).

    Returns
    -------
    dict
        ``{"before": {...}, "after": {...}}``
    """
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


def needs_update(current, desired, exclude_keys=None):
    """Determine whether *desired* differs from *current*.

    Parameters
    ----------
    current : dict
        Current state from the API.
    desired : dict
        Desired state from module parameters.
    exclude_keys : set, optional
        Keys to ignore during comparison (write-only fields, IDs, etc.).

    Returns
    -------
    bool
        ``True`` if an update is required.
    """
    if exclude_keys is None:
        exclude_keys = set()

    for key, desired_val in desired.items():
        if key in exclude_keys:
            continue
        if desired_val is None:
            continue
        current_val = current.get(key)
        # Normalise enums for comparison
        current_cmp = serialize_value(current_val)
        desired_cmp = serialize_value(desired_val)
        if current_cmp != desired_cmp:
            return True
    return False
