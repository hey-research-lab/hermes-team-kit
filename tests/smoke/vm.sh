#!/bin/sh
# Run INSIDE a fresh Debian 12+/Ubuntu 24.04+ VM as its non-root Hermes user.
# No Docker, SSH, remote creation, package downloads or real model calls.
set -eu
cd "$(dirname "$0")/../.."
python3 tests/run.py
python3 tests/check_source.py
python3 tests/smoke/local.py
# Opt in to service checks after completing the documented root installation.
if [ "${CHECK_SERVICES:-0}" = 1 ]; then
    systemctl is-active team-gate.service
    systemctl is-active team-tasks.timer
fi
