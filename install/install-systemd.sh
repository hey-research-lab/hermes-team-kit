#!/bin/sh
# The sole root step. Usage: sudo install/install-systemd.sh USER /absolute/kit/path
set -eu
[ "$(id -u)" -eq 0 ] || { echo 'This step requires root.' >&2; exit 1; }
[ "$#" -eq 2 ] || { echo 'Usage: install-systemd.sh USER /absolute/kit/path' >&2; exit 1; }
kit_user=$1
kit_path=$2
case "$kit_user" in *[!a-zA-Z0-9_-]*) echo 'Invalid username.' >&2; exit 1 ;; esac
id "$kit_user" >/dev/null
[ "$kit_user" != root ] || { echo 'The services must run as a non-root user.' >&2; exit 1; }
case "$kit_path" in /*) ;; *) echo 'Use an absolute path.' >&2; exit 1 ;; esac
case "$kit_path" in *[!a-zA-Z0-9_./-]*) echo 'Path must contain no whitespace or systemd escapes.' >&2; exit 1 ;; esac
[ -f "$kit_path/config.toml" ] && [ -f "$kit_path/service.env" ]
for unit in team-gate.service team-tasks.service team-tasks.timer; do
    sed -e "s|@USER@|$kit_user|g" -e "s|@ROOT@|$kit_path|g" "$kit_path/install/$unit" > "/etc/systemd/system/$unit"
done
systemctl daemon-reload
systemctl enable --now team-gate.service team-tasks.timer
