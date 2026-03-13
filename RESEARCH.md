# Uptime Kuma API Research Notes

> Temporary file — removed during Phase 9 cleanup.

## Library: uptime-kuma-api 1.2.1

Third-party wrapper by lucasheld. Depends on python-socketio[client] + packaging.

## Connection

```python
UptimeKumaApi(url, timeout=10, headers=None, ssl_verify=True, wait_events=0.2)
```

- Connects via Socket.IO to `{url}/socket.io/`
- Auth: `login(username, password, token="")` or `login_by_token(token)`
- Auto-login when `disableAuth` is enabled (pass `username=None, password=None`)
- Context manager supported (`with UptimeKumaApi(...) as api:`)

## Resource Summary Table

| Resource | List | Get | Add | Edit | Delete | Other |
|----------|------|-----|-----|------|--------|-------|
| Monitor | `get_monitors()` | `get_monitor(id)` | `add_monitor(**kw)` | `edit_monitor(id, **kw)` | `delete_monitor(id)` | `pause_monitor(id)`, `resume_monitor(id)` |
| Monitor Tag | — | — | `add_monitor_tag(tag_id, monitor_id, value="")` | — | `delete_monitor_tag(tag_id, monitor_id, value="")` | — |
| Notification | `get_notifications()` | `get_notification(id)` | `add_notification(**kw)` | `edit_notification(id, **kw)` | `delete_notification(id)` | `test_notification(**kw)` |
| Status Page | `get_status_pages()` | `get_status_page(slug)` | `add_status_page(slug, title)` | `save_status_page(slug, **kw)` | `delete_status_page(slug)` | `post_incident(slug, ...)`, `unpin_incident(slug)` |
| Tag | `get_tags()` | `get_tag(id)` | `add_tag(**kw)` | `edit_tag(id, **kw)` | `delete_tag(id)` | — |
| Maintenance | `get_maintenances()` | `get_maintenance(id)` | `add_maintenance(**kw)` | `edit_maintenance(id, **kw)` | `delete_maintenance(id)` | `pause_maintenance(id)`, `resume_maintenance(id)` |
| API Key | `get_api_keys()` | `get_api_key(id)` | `add_api_key(name, expires, active)` | — | `delete_api_key(id)` | `enable_api_key(id)`, `disable_api_key(id)` |
| Settings | `get_settings()` | — | — | `set_settings(**kw)` | — | — |

## Enums

### MonitorType
group, http, port, ping, keyword, json-query, grpc-keyword, dns, docker,
real-browser, push, steam, gamedig, mqtt, kafka-producer, sqlserver, postgres,
mysql, mongodb, radius, redis, tailscale-ping

### AuthMethod
(empty string = none), basic, ntlm, mtls, oauth2-cc

### MaintenanceStrategy
manual, single, recurring-interval, recurring-weekday, recurring-day-of-month, cron

### NotificationType
56 providers including: alerta, discord, email (smtp), gotify, mattermost,
ntfy, opsgenie, pagerduty, pushover, slack, teams, telegram, twilio, webhook

### IncidentStyle
info, warning, danger, primary, light, dark

### ProxyProtocol
https, http, socks, socks5, socks5h, socks4

### DockerType
socket, tcp

### MonitorStatus (int enum)
0=DOWN, 1=UP, 2=PENDING, 3=MAINTENANCE

## Monitor Parameters (add_monitor / edit_monitor)

### Common (all types)
- type (MonitorType, required)
- name (str, required)
- interval (int, default=60)
- retryInterval (int, default=60)
- resendInterval (int, default=0)
- maxretries (int, default=1)
- upsideDown (bool, default=False)
- notificationIDList (list)
- httpBodyEncoding (str, default="json")
- parent (int, group parent)
- description (str)

### HTTP/KEYWORD/JSON_QUERY/REAL_BROWSER
- url (str)

### HTTP/KEYWORD/GRPC_KEYWORD
- maxredirects (int, default=10)
- accepted_statuscodes (list[str], default=["200-299"])

### HTTP/KEYWORD/JSON_QUERY
- expiryNotification (bool)
- ignoreTls (bool)
- proxyId (int)
- method (str, default="GET")
- body (str)
- headers (str)
- authMethod (AuthMethod)
- timeout (int, default=48)
- basic_auth_user, basic_auth_pass (when authMethod=basic/ntlm)
- authDomain, authWorkstation (when authMethod=ntlm)
- tlsCert, tlsKey, tlsCa (when authMethod=mtls)
- oauth_* fields (when authMethod=oauth2-cc)

### KEYWORD
- keyword (str)
- invertKeyword (bool)

### GRPC_KEYWORD
- grpcUrl, grpcEnableTls, grpcServiceName, grpcMethod, grpcProtobuf, grpcBody, grpcMetadata

### PORT/PING/DNS/STEAM/MQTT/RADIUS/TAILSCALE_PING
- hostname (str)

### PORT/DNS/STEAM/MQTT/RADIUS
- port (int)

### DNS
- dns_resolve_server (str, default="1.1.1.1")
- dns_resolve_type (str, default="A")

### MQTT
- mqttUsername, mqttPassword, mqttTopic, mqttSuccessMessage

### Database types (SQLSERVER/POSTGRES/MYSQL/MONGODB/REDIS)
- databaseConnectionString (str)
- databaseQuery (str, for SQL types only)

### DOCKER
- docker_container (str)
- docker_host (int)

### RADIUS
- radiusUsername, radiusPassword, radiusSecret, radiusCalledStationId, radiusCallingStationId

### GAMEDIG
- game (str)
- gamedigGivenPortOnly (bool)

### JSON_QUERY
- jsonPath (str)
- expectedValue (str)

### KAFKA_PRODUCER
- kafkaProducerBrokers (list[str])
- kafkaProducerTopic, kafkaProducerMessage (str)
- kafkaProducerSsl (bool)
- kafkaProducerAllowAutoTopicCreation (bool)
- kafkaProducerSaslOptions (dict)

### PING
- packetSize (int, default=56)

## Tag Parameters
- name (str, required)
- color (str, required, hex color e.g. "#ffffff")

## Notification Parameters
- name (str, required)
- type (NotificationType, required)
- isDefault (bool, default=False)
- applyExisting (bool, default=False)
- Plus provider-specific options (see notification_provider_options dict)

## Maintenance Parameters
- title (str, required)
- strategy (MaintenanceStrategy, required)
- active (bool, default=True)
- description (str)
- dateRange (list)
- intervalDay (int, default=1)
- weekdays (list)
- daysOfMonth (list)
- timeRange (list of {hours, minutes} dicts)
- cron (str, default="30 3 * * *")
- durationMinutes (int, default=60)
- timezoneOption (str)

## Status Page Parameters
- slug (str, required, URL-safe identifier)
- title (str, required)
- description (str)
- theme (str: "auto"/"light"/"dark")
- published (bool, default=True)
- showTags (bool)
- domainNameList (list)
- googleAnalyticsId (str)
- customCSS (str)
- footerText (str)
- showPoweredBy (bool, default=True)
- showCertificateExpiry (bool)
- icon (str, default="/icon.svg")
- publicGroupList (list of group dicts with monitorList)

## Settings Parameters
- checkUpdate (bool)
- checkBeta (bool)
- keepDataPeriodDays (int, default=180)
- serverTimezone (str)
- entryPage (str, default="dashboard")
- searchEngineIndex (bool)
- primaryBaseURL (str)
- steamAPIKey (str)
- nscd (bool)
- dnsCache (bool)
- chromeExecutable (str)
- tlsExpiryNotifyDays (list[int])
- disableAuth (bool)
- trustProxy (bool)
- password (str, required when disableAuth=True)

## API Key Parameters
- name (str, required)
- expires (str or None, datetime string)
- active (bool)

## Write-Only Fields
- Monitor: basic_auth_pass, oauth_client_secret, radiusPassword, radiusSecret,
  mqttPassword, databaseConnectionString (partially masked)
- Notification: provider-specific credential fields (API keys, tokens, passwords)
- Settings: steamAPIKey, password
- API Key: the key value itself (returned only on creation)

## Key Quirks
1. Status pages use `slug` (str) as identifier, not integer ID
2. `get_status_page(slug)` makes both a Socket.IO call AND an HTTP GET to `/api/status-page/{slug}`
3. Monitor `notificationIDList` is stored as dict `{id: True}` but returned as list `[id]`
4. `add_monitor_tag` / `delete_monitor_tag` require both `tag_id` and `monitor_id`
5. API keys cannot be edited — only created, enabled/disabled, and deleted
6. Tags use a direct RPC call (`getTags`) rather than event-based data
7. Maintenance supports monitor and status page associations via separate methods
