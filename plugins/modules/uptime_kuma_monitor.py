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
    default: "1.1.1.1"
  dns_resolve_type:
    description:
      - DNS record type to query.
    type: str
    default: A
    choices: [A, AAAA, CAA, CNAME, MX, NS, PTR, SOA, SRV, TXT]
  mqtt_username:
    description:
      - Username for MQTT monitor.
    type: str
  mqtt_password:
    description:
      - Password for MQTT monitor.
    type: str
    no_log: true
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
    no_log: true
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
  notification_ids:
    description:
      - List of notification provider IDs to associate with this monitor.
    type: list
    elements: int
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
    no_log: true
  api_token:
    description:
      - Login token for authentication.
    type: str
    no_log: true
  validate_certs:
    description:
      - Whether to validate SSL certificates.
    type: bool
    default: true
  api_timeout:
    description:
      - Timeout in seconds for API requests.
    type: int
    default: 10
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

    # Notification IDs
    if params.get("notification_ids") is not None:
        kwargs["notificationIDList"] = params["notification_ids"]

    return kwargs


def run_module(module):
    """Execute the monitor module logic."""
    client = UptimeKumaClient(module)
    try:
        _run(module, client)
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
    kwargs = build_monitor_params(module)

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
        keyword=dict(type="str"),
        ignore_tls=dict(type="bool", default=False),
        max_redirects=dict(type="int", default=10),
        accepted_statuscodes=dict(type="list", elements="str", default=["200-299"]),
        method=dict(
            type="str", default="GET",
            choices=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        ),
        body=dict(type="str"),
        headers=dict(type="str"),
        dns_resolve_server=dict(type="str", default="1.1.1.1"),
        dns_resolve_type=dict(
            type="str", default="A",
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
        notification_ids=dict(type="list", elements="int"),
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
    )

    run_module(module)


if __name__ == "__main__":
    main()
