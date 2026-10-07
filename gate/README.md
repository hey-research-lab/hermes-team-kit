# Telegram gate

A deterministic, Python standard-library gate. It reads proposals from the
configured output directory and records owner decisions with single-use nonces.
It makes no model calls. Guests can submit public links for a generic review;
guest reports are delivered only to their requester and filtered for secrets.

See the root README for installation and configuration, and
[the threat model](../docs/THREAT-MODEL.md) for the trust boundaries.
