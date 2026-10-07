#!/usr/bin/env python3
"""Daily budget breaker: usage adapter or completion ledger; UTC reset."""
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import time
import urllib.request
from kit_config import load
from ledger import events


def numeric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('invalid usage value')
    return float(value)


def window(now, hour=0):
    start = datetime.fromtimestamp(now, timezone.utc).replace(hour=hour, minute=0, second=0, microsecond=0)
    if start.timestamp() > now:
        start -= timedelta(days=1)
    return start.timestamp(), (start + timedelta(days=1)).timestamp()


def remote_usage(url, key):
    if not url.startswith('https://'):
        raise ValueError('usage endpoint must use HTTPS')
    request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + key})
    # Do not forward a credential to a redirect destination.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as reply:
        data = json.loads(reply.read(65537))
    return data


def evaluate(config, now=None, fetch=remote_usage):
    now = time.time() if now is None else now
    limits = config.get('limits', {})
    threshold = numeric(limits.get('breaker_threshold', .8))
    if not 0 < threshold <= 1:
        raise ValueError('breaker_threshold must be in (0, 1]')
    start, reset = window(now, limits.get('reset_hour_utc', 0))
    rows = list(events(config['paths']['ledger']))
    groups = {}
    for name, seat in config.get('seats', {}).items():
        provider = {**config.get('provider', {}), **seat}
        cap = seat.get('daily_cap_usd')
        spend = sum(numeric(r['dollars']) for r in rows if r.get('type') == 'finished'
                    and start <= r['ts'] <= now and r.get('group') == name and r.get('dollars') is not None)
        unknown = any(r.get('type') == 'finished' and start <= r['ts'] <= now
                      and r.get('group') == name and r.get('dollars') is None for r in rows)
        source = 'ledger'
        group_reset = reset
        if provider.get('usage_url'):
            try:
                usage = fetch(provider['usage_url'], os.environ.get(provider.get('api_key_env', ''), ''))
                cap, spend = numeric(usage['daily_cap_usd']), numeric(usage['spent_usd'])
                reset_time = datetime.fromisoformat(usage['reset_at'].replace('Z', '+00:00'))
                if reset_time.tzinfo is None:
                    raise ValueError('usage reset needs a timezone')
                group_reset = reset_time.timestamp()
                if group_reset <= now:
                    raise ValueError('stale usage reply')
                source, unknown = 'endpoint', False
            except (OSError, ValueError, KeyError, TypeError):
                source = 'ledger-fallback'
        cap = numeric(cap) if cap is not None else None
        paused = cap is not None and (unknown or spend >= threshold * cap)
        groups[name] = {'profiles': seat['profiles'], 'daily_cap_usd': cap, 'spent_usd': spend,
                        'remaining_usd': None if cap is None else max(0, cap * threshold - spend),
                        'paused': paused, 'unknown_cost': unknown, 'reset_at': group_reset, 'source': source}
    return {'ts': now, 'groups': groups}


def enforce(snapshot, command, state_path):
    """Park ready cards on paused groups; release only cards this breaker parked."""
    state_path = Path(state_path)
    held = json.loads(state_path.read_text()) if state_path.exists() else {}
    paused = {p for v in snapshot["groups"].values() if v["paused"] for p in v["profiles"]}
    cards = json.loads(command("list", "--json"))
    for card in cards:
        cid, profile = card["id"], card.get("assignee")
        if profile in paused and card["status"] == "ready":
            held[cid] = profile
            state_path.write_text(json.dumps(held))  # Intent survives a crash after scheduling.
            command("schedule", cid, "daily key budget breaker")
        elif cid in held and profile not in paused:
            if card["status"] == "scheduled":
                command("unblock", cid)
            del held[cid]
            state_path.write_text(json.dumps(held))
    return held


def update(config, now=None, fetch=remote_usage):
    snapshot = evaluate(config, now, fetch)
    out = Path(config['paths']['out'])
    out.mkdir(parents=True, exist_ok=True)
    temporary = out / 'breaker.json.tmp'
    temporary.write_text(json.dumps(snapshot, allow_nan=False))
    temporary.chmod(0o600)
    temporary.replace(out / 'breaker.json')
    return snapshot


def main():
    print(json.dumps(update(load()), indent=2))

if __name__ == '__main__':
    main()
