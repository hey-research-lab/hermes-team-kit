#!/usr/bin/env python3
"""Append-only completion and acceptance events; no credentials or task bodies."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import time
from kit_config import load


def events(path):
    try:
        with open(path, encoding='utf-8') as stream:
            fcntl.flock(stream, fcntl.LOCK_SH)
            for line in stream:
                yield json.loads(line)  # Corruption must not silently undercount spend.
    except FileNotFoundError:
        return


def append(path, event):
    record = dict(event)
    record.setdefault('ts', time.time())
    if record.get('type') not in ('finished', 'accepted') or not record.get('event_id'):
        raise ValueError('event needs type and event_id')
    if (isinstance(record['ts'], bool) or not isinstance(record['ts'], (float, int))
            or not math.isfinite(record['ts'])):
        raise ValueError('invalid timestamp')
    if not isinstance(record.get('task_id'), str) or not record['task_id']:
        raise ValueError('missing task_id')
    if record['type'] == 'finished':
        for field in ('profile', 'model', 'provider', 'card_id', 'task_id'):
            if not isinstance(record.get(field), str) or not record[field]:
                raise ValueError('missing ' + field)
        for field in ('dollars', 'duration'):
            value = record.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (float, int))
                                      or not math.isfinite(value) or value < 0):
                raise ValueError('invalid ' + field)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a+', encoding='utf-8') as stream:
        os.chmod(path, 0o600)
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        if any(json.loads(line).get('event_id') == record['event_id'] for line in stream):
            return False
        stream.seek(0, os.SEEK_END)
        stream.write(json.dumps(record, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    return True


def finished(path, task_id, card_id, shown, group=None):
    task = shown.get('task', {})
    runs = shown.get('runs', [])
    for index, run in enumerate(runs or [{}]):
        if runs and run.get('ended_at') is None:
            continue
        run = {**(run.get('metadata') or {}), **run}
        profile = run.get('profile') or task.get('assignee') or 'unknown'
        duration = run.get('duration')
        if duration is None and isinstance(run.get('started_at'), (float, int)) and isinstance(run.get('ended_at'), (float, int)):
            duration = max(0, run['ended_at'] - run['started_at'])
        append(path, {'type': 'finished', 'event_id': f"finished:{card_id}:{run.get('id', index)}",
                      'task_id': task_id, 'card_id': card_id, 'profile': profile,
                      'model': run.get('model') or 'unknown', 'provider': run.get('provider') or 'unknown',
                      'tokens': run.get('tokens'), 'dollars': run.get('cost_usd'), 'duration': duration,
                      'group': group.get(profile) if isinstance(group, dict) else group, 'ts': run.get('ended_at') or time.time()})


def report(path, days=7, now=None):
    now = time.time() if now is None else now
    rows = list(events(path))
    accepted = {r['task_id'] for r in rows if r['type'] == 'accepted' and now - days * 86400 <= r['ts'] <= now}
    stats = defaultdict(lambda: {'dollars': 0.0, 'tasks': set(), 'unknown': 0})
    for row in rows:
        if row['type'] != 'finished' or not now - days * 86400 <= row['ts'] <= now:
            continue
        item = stats[row['profile']]
        if row.get('dollars') is None:
            item['unknown'] += 1
        else:
            item['dollars'] += row['dollars']
        if row['task_id'] in accepted:
            item['tasks'].add(row['task_id'])
    lines = ['profile\tdollars\taccepted tasks\t$/accepted task\tunknown costs']
    for profile, item in sorted(stats.items()):
        count = len(item['tasks'])
        rate = f"{item['dollars'] / count:.4f}" if count and not item['unknown'] else 'unknown'
        lines.append(f"{profile}\t{item['dollars']:.4f}\t{count}\t{rate}\t{item['unknown']}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['report', 'append'])
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--path', default=load().get('paths', {}).get('ledger', 'var/ledger.jsonl'))
    args = parser.parse_args()
    if args.days < 1:
        parser.error('--days must be positive')
    if args.command == 'report':
        print(report(args.path, args.days))
    else:
        import sys
        append(args.path, json.load(sys.stdin))

if __name__ == '__main__':
    main()
