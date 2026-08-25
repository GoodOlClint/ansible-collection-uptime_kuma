#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2024, Clint Branham <goodolclint@gmail.com>
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: uptime_kuma_monitor
short_description: Manage monitors in Uptime Kuma
version_added: "0.1.0"
description:
  - Create, update, and delete monitors in Uptime Kuma.
  - Supports all monitor types including HTTP, TCP port, ping, DNS, Docker, and more.
  - Monitors are identified by O(name) for idempotency.
options:
  name:
    description:
      - Name of the monitor.
      - Used as the unique identifier for idempotency.
    type: str
    required: true
  monitor_type:
    description:
      - Type of the monitor.
      - Required when O(state=present).
    type: str
    choices:
      - group
      - http
      - port
      - ping
      - keyword
      - json-query
      - grpc-keyword
      - dns
      - docker
      - real-browser
      - push
      - steam
      - gamedig
      - mqtt
      - kafka-producer
      - sqlserver
      - postgres
      - mysql
      - mongodb
      - radius
      - redis
      - tailscale-ping
  url:
    description:
      - URL to monitor.
      - Required for HTTP, keyword, JSON query, and real-browser monitor types.
    type: str
  hostname:
    description:
      - Hostname or IP address.
      - Required for port, ping, DNS, STEAM, MQTT, Radius, and Tailscale Ping types.
    type: str
  port:
    description:
      - Port number.
      - Required for port, DNS, STEAM, MQTT, and Radius types.
    type: int
  interval:
    description:
      - Check interval in seconds.
    type: int
    default: 60
  retry_interval:
    description:
      - Retry interval in seconds.
    type: int
    default: 60
  max_retries:
    description:
      - Maximum number of retries before the service is marked as down.
    type: int
    default: 1
  upside_down:
    description:
      - Flip the status upside down. If enabled, a successful response is considered as down.
    type: bool
    default: false
  description:
    description:
      - Description of the monitor.
    type: str
  keyword:
    description:
      - Keyword to search for in the response body.
      - Required for keyword and gRPC keyword monitor types.
    type: str
  ignore_tls:
    description:
      - Ignore TLS/SSL certificate errors.
    type: bool
    default: false
  max_redirects:
    description:
      - Maximum number of HTTP redirects to follow.
    type: int
    default: 10
  accepted_statuscodes:
    description:
      - List of accepted HTTP status codes.
    type: list
    elements: str
    default: ["200-299"]
  method:
    description:
      - HTTP method to use.
    type: str
    default: GET
    choices: [GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS]
  body:
    description:
      - HTTP body for POST/PUT/PATCH requests.
    type: str
  headers:
    description:
      - HTTP headers as a JSON string.
    type: str
  dns_resolve_server:
    description:
      - DNS server to use for DNS monitor type.
    type: str
  dns_resolve_type:
    description:
      - DNS record type to query.
    type: str
    choices: [A, AAAA, CAA, CNAME, MX, NS, PTR, SOA, SRV, TXT]
  mqtt_username:
    description:
      - Username for MQTT monitor.
    type: str
  mqtt_password:
    description:
      - Password for MQTT monitor.
    type: str
  mqtt_topic:
    description:
      - MQTT topic to subscribe to.
    type: str
  mqtt_success_message:
    description:
      - Expected success message for MQTT monitor.
    type: str
  database_connection_string:
    description:
      - Connection string for database monitors (SQL Server, PostgreSQL, MySQL, MongoDB, Redis).
    type: str
  database_query:
    description:
      - SQL query for SQL Server, PostgreSQL, and MySQL monitors.
    type: str
  docker_container:
    description:
      - Docker container name or ID.
    type: str
  docker_host:
    description:
      - Docker host ID.
    type: int
  timeout:
    description:
      - Per-check timeout in seconds.
    type: int
    default: 48
  resend_interval:
    description:
      - Resend the down notification every N checks while still down. V(0) disables.
    type: int
    default: 0
  json_path:
    description:
      - JSON path (jsonata) evaluated against the response body for C(json-query) monitors.
    type: str
  json_path_operator:
    description:
      - Comparison applied between the json_path result and O(expected_value).
    type: str
    choices: ["==", "!=", "<", "<=", ">", ">=", "contains", "not_contains", "starts_with", "ends_with"]
  expected_value:
    description:
      - Expected value for C(json-query) monitors.
    type: str
  invert_keyword:
    description:
      - Invert the keyword match for C(keyword) and C(grpc-keyword) monitors.
    type: bool
    default: false
  parent:
    description:
      - Name of the C(group) monitor this monitor belongs to.
    type: str
  notification_ids:
    description:
      - List of notification provider IDs to associate with this monitor.
      - Mutually exclusive with O(notification_names).
    type: list
    elements: int
  notification_names:
    description:
      - List of notification provider names to associate with this monitor.
      - Resolved to IDs at run time; fails if a name does not exist.
    type: list
    elements: str
  proxy_id:
    description:
      - Proxy ID to use for this monitor.
    type: int
  active:
    description:
      - Whether the monitor should be active (not paused).
    type: bool
    default: true
  state:
    description:
      - Whether the monitor should exist or not.
    type: str
    choices: [present, absent]
    default: present
  api_url:
    description:
      - URL of the Uptime Kuma instance.
    type: str
    required: true
  api_username:
    description:
      - Username for authentication.
    type: str
  api_password:
    description:
      - Password for authentication.
    type: str
  api_token:
    description:
      - Login token for authentication.
    type: str
  validate_certs:
    description:
      - Whether to validate SSL certificates.
    type: bool
    default: true
  api_timeout:
    description:
      - Timeout in seconds for API requests.
    type: int
    default: 30
author:
  - Clint Branham (@goodolclint)
"""

EXAMPLES = r"""
- name: Create an HTTP monitor
  goodolclint.uptime_kuma.uptime_kuma_monitor:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: My Website
    monitor_type: http
    url: https://example.com
    interval: 60
    state: present

- name: Create a ping monitor
  goodolclint.uptime_kuma.uptime_kuma_monitor:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: My Server
    monitor_type: ping
    hostname: 192.168.1.1
    state: present

- name: Create a DNS monitor
  goodolclint.uptime_kuma.uptime_kuma_monitor:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: DNS Check
    monitor_type: dns
    hostname: example.com
    dns_resolve_server: "8.8.8.8"
    dns_resolve_type: A
    state: present

- name: Create a JSON query monitor linked to a notification by name
  goodolclint.uptime_kuma.uptime_kuma_monitor:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: Valheim — PlayFab lobby
    monitor_type: json-query
    url: http://docker.example.internal:8080/status.json
    json_path: platform
    json_path_operator: "=="
    expected_value: playfab
    timeout: 16
    max_retries: 2
    notification_names:
      - ntfy alerts
    state: present

- name: Delete a monitor
  goodolclint.uptime_kuma.uptime_kuma_monitor:
    api_url: http://localhost:3001
    api_username: admin
    api_password: secret123
    name: My Website
    state: absent
"""

RETURN = r"""
monitor:
  description: The monitor object after the operation.
  returned: success
  type: dict
  sample:
    id: 1
    name: My Website
    type: http
    url: https://example.com
    interval: 60
    active: true
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.goodolclint.uptime_kuma.plugins.module_utils.uptime_kuma_api import (
    UptimeKumaClient,
    UptimeKumaError,
    compute_diff,
    needs_update,
    normalize_result,
    uptime_kuma_argument_spec,
)

# Fields that are write-only (cannot be read back for comparison)
WRITE_ONLY_FIELDS = {
    "basic_auth_pass", "oauth_client_secret", "radiusPassword",
    "radiusSecret", "mqttPassword", "databaseConnectionString",
}


def build_monitor_params(module):
    """Build the kwargs dict for add_monitor / edit_monitor."""
    params = module.params
    kwargs = {
        "type": params["monitor_type"],
        "name": params["name"],
        "interval": params["interval"],
        "retryInterval": params["retry_interval"],
        "maxretries": params["max_retries"],
        "upsideDown": params["upside_down"],
        "timeout": params["timeout"],
        "resendInterval": params["resend_interval"],
        "invertKeyword": params["invert_keyword"],
    }

    # Optional string/int params with direct mapping
    mappings = {
        "url": "url",
        "hostname": "hostname",
        "port": "port",
        "description": "description",
        "keyword": "keyword",
        "method": "method",
        "body": "body",
        "headers": "headers",
        "dns_resolve_server": "dns_resolve_server",
        "dns_resolve_type": "dns_resolve_type",
        "docker_container": "docker_container",
        "docker_host": "docker_host",
        "database_query": "databaseQuery",
        "proxy_id": "proxyId",
        "json_path": "jsonPath",
        "json_path_operator": "jsonPathOperator",
        "expected_value": "expectedValue",
    }

    for param_name, api_name in mappings.items():
        value = params.get(param_name)
        if value is not None:
            kwargs[api_name] = value

    # Boolean params
    if params.get("ignore_tls") is not None:
        kwargs["ignoreTls"] = params["ignore_tls"]

    # List params
    if params.get("accepted_statuscodes") is not None:
        kwargs["accepted_statuscodes"] = params["accepted_statuscodes"]

    if params.get("max_redirects") is not None:
        kwargs["maxredirects"] = params["max_redirects"]

    # Credential params (write-only)
    if params.get("mqtt_username") is not None:
        kwargs["mqttUsername"] = params["mqtt_username"]
    if params.get("mqtt_password") is not None:
        kwargs["mqttPassword"] = params["mqtt_password"]
    if params.get("mqtt_topic") is not None:
        kwargs["mqttTopic"] = params["mqtt_topic"]
    if params.get("mqtt_success_message") is not None:
        kwargs["mqttSuccessMessage"] = params["mqtt_success_message"]
    if params.get("database_connection_string") is not None:
        kwargs["databaseConnectionString"] = params["database_connection_string"]

    if params.get("notification_ids") is not None:
        kwargs["notificationIDList"] = params["notification_ids"]

    return kwargs


def resolve_references(module, client, kwargs):
    """Turn notification_names / parent names into IDs, failing on unknown names."""
    params = module.params
    if params.get("notification_names") is not None:
        ids = []
        for name in params["notification_names"]:
            notif = client.get_notification_by_name(name)
            if notif is None:
                module.fail_json(msg=f"Notification '{name}' does not exist")
            ids.append(notif["id"])
        kwargs["notificationIDList"] = ids
    if params.get("parent") is not None:
        group = client.get_monitor_by_name(params["parent"])
        if group is None or group.get("type") != "group":
            module.fail_json(msg=f"Group monitor '{params['parent']}' does not exist")
        kwargs["parent"] = group["id"]
    return kwargs


def run_module(module):
    """Execute the monitor module logic."""
    client = UptimeKumaClient(module)
    try:
        _run(module, client)
    except UptimeKumaError as exc:
        module.fail_json(msg=f"Uptime Kuma API error: {exc}")
    finally:
        client.disconnect()


def _run(module, client):
    """Inner logic separated for clean disconnect handling."""
    state = module.params["state"]
    name = module.params["name"]
    active = module.params.get("active", True)

    existing = client.get_monitor_by_name(name)

    if state == "absent":
        if existing is None:
            module.exit_json(changed=False, monitor={})
            return
        if module.check_mode:
            module.exit_json(
                changed=True,
                diff=compute_diff(existing, None),
                monitor=normalize_result(existing),
            )
            return
        client.delete_monitor(existing["id"])
        module.exit_json(
            changed=True,
            diff=compute_diff(existing, None),
            monitor={},
        )
        return

    # state == present
    kwargs = resolve_references(module, client, build_monitor_params(module))

    if existing is None:
        # Create
        if module.check_mode:
            module.exit_json(changed=True, diff=compute_diff(None, kwargs), monitor=kwargs)
            return
        result = client.add_monitor(**kwargs)
        monitor_id = result.get("monitorID")
        new_monitor = client.get_monitor(monitor_id) if monitor_id else result
        # Handle active/paused state
        if not active and monitor_id:
            client.pause_monitor(monitor_id)
        module.exit_json(
            changed=True,
            diff=compute_diff(None, new_monitor),
            monitor=normalize_result(new_monitor),
        )
        return

    # Update if needed
    monitor_id = existing["id"]
    changed = False
    diff_data = {}

    # Check if monitor params need updating
    if needs_update(existing, kwargs, exclude_keys=WRITE_ONLY_FIELDS):
        if module.check_mode:
            after = dict(existing)
            after.update(kwargs)
            module.exit_json(
                changed=True,
                diff=compute_diff(existing, after),
                monitor=normalize_result(after),
            )
            return
        client.edit_monitor(monitor_id, **kwargs)
        changed = True

    # Handle active/paused state
    is_active = existing.get("active", True)
    if active and not is_active:
        if not module.check_mode:
            client.resume_monitor(monitor_id)
        changed = True
    elif not active and is_active:
        if not module.check_mode:
            client.pause_monitor(monitor_id)
        changed = True

    if changed:
        updated = client.get_monitor(monitor_id) if not module.check_mode else existing
        diff_data = compute_diff(existing, updated)
        module.exit_json(changed=True, diff=diff_data, monitor=normalize_result(updated))
    else:
        module.exit_json(changed=False, monitor=normalize_result(existing))


def main():
    """Module entry point."""
    spec = uptime_kuma_argument_spec()
    spec.update(
        name=dict(type="str", required=True),
        monitor_type=dict(
            type="str",
            choices=[
                "group", "http", "port", "ping", "keyword", "json-query",
                "grpc-keyword", "dns", "docker", "real-browser", "push",
                "steam", "gamedig", "mqtt", "kafka-producer", "sqlserver",
                "postgres", "mysql", "mongodb", "radius", "redis", "tailscale-ping",
            ],
        ),
        url=dict(type="str"),
        hostname=dict(type="str"),
        port=dict(type="int"),
        interval=dict(type="int", default=60),
        retry_interval=dict(type="int", default=60),
        max_retries=dict(type="int", default=1),
        upside_down=dict(type="bool", default=False),
        description=dict(type="str"),
        keyword=dict(type="str", no_log=False),
        ignore_tls=dict(type="bool", default=False),
        max_redirects=dict(type="int", default=10),
        accepted_statuscodes=dict(type="list", elements="str", default=["200-299"]),
        method=dict(
            type="str", default="GET",
            choices=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        ),
        body=dict(type="str"),
        headers=dict(type="str"),
        dns_resolve_server=dict(type="str"),
        dns_resolve_type=dict(
            type="str",
            choices=["A", "AAAA", "CAA", "CNAME", "MX", "NS", "PTR", "SOA", "SRV", "TXT"],
        ),
        mqtt_username=dict(type="str"),
        mqtt_password=dict(type="str", no_log=True),
        mqtt_topic=dict(type="str"),
        mqtt_success_message=dict(type="str"),
        database_connection_string=dict(type="str", no_log=True),
        database_query=dict(type="str"),
        docker_container=dict(type="str"),
        docker_host=dict(type="int"),
        timeout=dict(type="int", default=48),
        resend_interval=dict(type="int", default=0),
        json_path=dict(type="str"),
        json_path_operator=dict(
            type="str",
            choices=["==", "!=", "<", "<=", ">", ">=", "contains", "not_contains", "starts_with", "ends_with"],
        ),
        expected_value=dict(type="str"),
        invert_keyword=dict(type="bool", default=False),
        parent=dict(type="str"),
        notification_ids=dict(type="list", elements="int"),
        notification_names=dict(type="list", elements="str"),
        proxy_id=dict(type="int"),
        active=dict(type="bool", default=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ("monitor_type",)),
        ],
        mutually_exclusive=[("notification_ids", "notification_names")],
    )

    run_module(module)


if __name__ == "__main__":
    main()
