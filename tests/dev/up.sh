#!/usr/bin/env bash
# Bring up a throwaway Uptime Kuma 2.x and create the admin the integration tests expect.
# Usage: tests/dev/up.sh [down|fresh]
# fresh: recreate the volume and leave setup to the suite; run it with -e uptime_kuma_fresh_instance=true once.
set -euo pipefail
cd "$(dirname "$0")"
if [[ "${1:-}" == "down" ]]; then docker compose down -v; exit 0; fi
fresh=false
if [[ "${1:-}" == "fresh" ]]; then fresh=true; docker compose down -v; fi
docker compose up -d --wait
if [[ "$fresh" == false ]]; then
python3 - <<'PY'
import socketio, sys
URL, USER, PASS = "http://localhost:3001", "admin", "Ansible-Dev-Pass-1"
sio = socketio.Client(request_timeout=30)
sio.connect(URL, wait_timeout=30)
def call(ev, *args):
    for _ in range(5):
        try: return sio.call(ev, args if len(args) != 1 else args[0], timeout=3)
        except socketio.exceptions.TimeoutError: pass
    sys.exit(f"{ev}: no ack")
if call("needSetup"):
    r = call("setup", USER, PASS)
    print("setup:", r)
else:
    print("setup: already done")
print("login:", call("login", {"username": USER, "password": PASS, "token": ""}).get("ok"))
sio.disconnect()
PY
fi
cat > ../integration/integration_config.yml <<'YML'
uptime_kuma_api_url: "http://localhost:3001"
uptime_kuma_api_username: "admin"
uptime_kuma_api_password: "Ansible-Dev-Pass-1"
YML
echo "dev instance ready at http://localhost:3001 (admin / Ansible-Dev-Pass-1)"
if [[ "$fresh" == true ]]; then
  echo "fresh instance: run the suite once with -e uptime_kuma_fresh_instance=true to assert the setup create path"
fi
