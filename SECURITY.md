# Security reporting

Report vulnerabilities through the repository's Security tab using **Report a
vulnerability**. The owner must enable private vulnerability reporting before
publication. If that option is unavailable, ask a maintainer to enable a private
reporting channel without disclosing the vulnerability in a public issue.

Do not file public issues containing secrets, bot tokens, provider credentials,
private chat IDs, task content or runtime logs. Include a minimal sanitized
reproduction, affected revision, impact and any suggested fix in a private
report. If a credential is exposed, revoke it immediately and invalidate
outstanding gate proposals before restarting. Do not send live credentials
with the report.

See [the threat model](docs/THREAT-MODEL.md) for trust boundaries and deployment
modes. Maintainers should coordinate a fix and disclosure with the reporter;
no timing commitment is established yet.
