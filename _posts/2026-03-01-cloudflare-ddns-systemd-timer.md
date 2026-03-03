---
title: "Cloudflare Dynamic DNS with systemd Timer"
date: 2026-03-01 12:30:00 -0800
description: "A practical Cloudflare DDNS setup using a Bash script, systemd service, and daily timer with env-based secrets."
categories: [homelab]
tags: [cloudflare, dns, ddns, systemd, linux, automation, security]
---

At home, I often need to reach things by using my public internet address (IP), which is basically a string of numbers. That's annoying to remember, and honestly not how I want to think about my own setup.

So the obvious move is to give those numbers a name, like `myhomecomputer.com`. Easy enough, right? Well, not quite. My home IP doesn't change all the time, but it does change eventually. So I can't just point `myhomecomputer.com` at one address and expect it to work forever.

This is where Dynamic DNS comes in. It's a common fix for this exact problem. There are services that do it for you, but many either cost money or force you onto a provider-branded name like `yourcomputer.superddns.com`.

I wanted my own domain name, not someone else's subdomain. Since I already manage my domains in Cloudflare, I decided to use that: have my home server check my current home internet address on a schedule, compare it to what Cloudflare has on file, and update it only if it changed.

This post shows exactly how I set that up, including how I made it run automatically on a schedule.

## What we're talking about

- **IP address**: The number-based address your home connection is using right now.
- **Domain name**: A readable name like `myhomecomputer.com`.
- **DNS**: The internet system that maps names to number-based addresses.
- **Dynamic DNS (DDNS)**: A way to keep your domain name pointed at the right home address over time.
- **Cloudflare**: The service where I manage domain records in this setup.
- **systemd** timer: A built-in Linux scheduler that runs a task on a set schedule.

## Why this setup

- Cloudflare already hosts my DNS.
- A shell script is easy to audit and debug.
- **systemd** timer is native, reliable, and easy to inspect.
- Secrets stay in a local **.env** file, not in published code.

## Files

- Script: `/var/www/dnsupdater.sh`
- Service: `/etc/systemd/system/cloudflare-ddns.service`
- Timer: `/etc/systemd/system/cloudflare-ddns.timer`
- Env file: `/etc/cloudflare-ddns/cloudflare-ddns.env`
- Log file: `/var/log/cloudflare-ddns.log`

## 1) Keep Cloudflare credentials in **.env**

I use an env file that is readable only by root:

```bash
CF_API_TOKEN="REDACTED"
CF_ZONE_NAME="mydomain.com"
CF_RECORD_NAME="mydomain.com" # You can also use a subdomain like "vpn.mydomain.com"
CF_RECORD_TYPE="A"
```

You can point this at either the zone root (`mydomain.com`) or any host/subdomain record in that zone.

Permissions:

```bash
sudo mkdir -p /etc/cloudflare-ddns
sudo chown root:root /etc/cloudflare-ddns
sudo chmod 700 /etc/cloudflare-ddns
sudo chmod 600 /etc/cloudflare-ddns/cloudflare-ddns.env
```

## 2) DDNS update script

The script loads the env file, detects public IP with fallbacks, checks the current DNS record, and only updates Cloudflare when the IP has changed.

`/var/www/dnsupdater.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Local paths for secrets and logs
ENV_FILE="/etc/cloudflare-ddns/cloudflare-ddns.env"
LOG_FILE="/var/log/cloudflare-ddns.log"

# Timestamped logger that writes to file and stdout
log() {
  printf '%s %s\n' "$(date -Is)" "$*" | tee -a "$LOG_FILE" >/dev/null
}

# Fail fast if the environment file is missing
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

: "${CF_API_TOKEN:?Missing CF_API_TOKEN}"
: "${CF_ZONE_NAME:?Missing CF_ZONE_NAME (e.g. mydomain.com)}"
: "${CF_RECORD_NAME:?Missing CF_RECORD_NAME (e.g. mydomain.com)}"
: "${CF_RECORD_TYPE:=A}"

AUTH_HEADER="Authorization: Bearer ${CF_API_TOKEN}"
JSON_HEADER="Content-Type: application/json"

# Determine public IPv4 with multiple providers for resilience
PUBLIC_IP="$(curl -fsS4 --max-time 5 https://api.ipify.org 2>/dev/null || true)"
if [[ -z "$PUBLIC_IP" ]]; then
  PUBLIC_IP="$(curl -fsS4 --max-time 5 https://checkip.amazonaws.com 2>/dev/null | tr -d ' \n\r\t' || true)"
fi
if [[ -z "$PUBLIC_IP" ]]; then
  PUBLIC_IP="$(curl -fsS4 --max-time 5 https://icanhazip.com 2>/dev/null | tr -d ' \n\r\t' || true)"
fi
if [[ -z "$PUBLIC_IP" ]]; then
  log "ERROR: Could not determine public IP"
  exit 1
fi

# Resolve zone ID from zone name
ZONE_ID="$({
  curl -fsS -H "$AUTH_HEADER" \
    "https://api.cloudflare.com/client/v4/zones?name=${CF_ZONE_NAME}&status=active"
} | jq -r '.result[0].id // empty')"
if [[ -z "$ZONE_ID" ]]; then
  log "ERROR: Zone not found or not accessible: ${CF_ZONE_NAME}"
  exit 1
fi

# Fetch the target DNS record and current content
REC_JSON="$({
  curl -fsS -H "$AUTH_HEADER" \
    "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records?type=${CF_RECORD_TYPE}&name=${CF_RECORD_NAME}"
})"

RECORD_ID="$(printf '%s' "$REC_JSON" | jq -r '.result[0].id // empty')"
CURRENT_IP="$(printf '%s' "$REC_JSON" | jq -r '.result[0].content // empty')"

if [[ -z "$RECORD_ID" ]]; then
  log "ERROR: Record not found: ${CF_RECORD_NAME} (${CF_RECORD_TYPE}) in zone ${CF_ZONE_NAME}"
  exit 1
fi

# No-op when DNS already matches current public IP
if [[ "$CURRENT_IP" == "$PUBLIC_IP" ]]; then
  log "OK: ${CF_RECORD_NAME} already ${PUBLIC_IP} (no change)"
  exit 0
fi

# Update record content to current public IP
UPDATE_JSON="$({
  curl -fsS -X PUT \
    -H "$AUTH_HEADER" \
    -H "$JSON_HEADER" \
    --data "{\"type\":\"${CF_RECORD_TYPE}\",\"name\":\"${CF_RECORD_NAME}\",\"content\":\"${PUBLIC_IP}\",\"ttl\":120,\"proxied\":false}" \
    "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records/${RECORD_ID}"
})"

if printf '%s' "$UPDATE_JSON" | jq -e '.success == true' >/dev/null; then
  log "UPDATED: ${CF_RECORD_NAME} ${CURRENT_IP:-unknown} -> ${PUBLIC_IP}"
else
  # Cloudflare returns structured errors; log them for troubleshooting
  ERR="$(printf '%s' "$UPDATE_JSON" | jq -c '.errors // empty' 2>/dev/null || true)"
  log "ERROR: Update failed: ${ERR:-unknown}"
  exit 1
fi
```

## 3) systemd service

Now that I have the script ready to go, I set up the service that the timer will use.

`/etc/systemd/system/cloudflare-ddns.service`:

```ini
[Unit]
Description=Cloudflare DDNS update for mydomain.com

[Service]
Type=oneshot
ExecStart=/var/www/dnsupdater.sh
```

## 4) systemd timer

Set up the timer to run once a day. `Persistent=true` also helps if the host was down at the scheduled time; **systemd** will run the missed job after boot.

`/etc/systemd/system/cloudflare-ddns.timer`:

```ini
[Unit]
Description=Run Cloudflare DDNS update for mydomain.com every 24 hours

[Timer]
OnBootSec=2min
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

One useful **systemd** detail: this timer runs `cloudflare-ddns.service` because the base name matches. If you ever want a timer to trigger a differently named service, set `Unit=your-service.service` in the `[Timer]` block.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflare-ddns.timer
```

For a first validation pass, I like to run the service manually once and confirm it logs either a no-change result or a successful update:

```bash
sudo systemctl start cloudflare-ddns.service
journalctl -u cloudflare-ddns.service -n 50 --no-pager
```

## 5) Useful checks

Useful for troubleshooting and quick confidence checks.

```bash
systemctl status cloudflare-ddns.timer
systemctl list-timers --all | grep cloudflare-ddns
sudo systemctl start cloudflare-ddns.service
journalctl -u cloudflare-ddns.service -f
tail -f /var/log/cloudflare-ddns.log
```

## Security notes

- Use a scoped Cloudflare API token (DNS edit only for the target zone).
- Never commit real API tokens or raw `.env` files.
- Keep env files root-only (`chmod 600`).
- Rotate credentials if there is any chance they were exposed.

This setup has been very low maintenance so far and gives me a clear, auditable DDNS path with native Linux tooling. 
