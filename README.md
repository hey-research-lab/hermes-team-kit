Authorship: Hermes team kit contributors.

# Hermes team gate and ledger

One Telegram bot gives an owner a queue of proposals and agent reports, with
**ok / no / hold** decisions protected by single-use nonces. The gate makes no
model calls. A local ledger records completed work and reports the dollars spent
per accepted task per profile. A dispatcher turns owner messages into Hermes
kanban cards, routes them by role, and respects a daily budget breaker.

Python 3.11+ and the standard library are sufficient for the kit. Use an existing
Hermes installation with profiles and the kanban `create`, `show`, `list`,
`reassign`, `schedule`, `unblock` and `dispatch` commands. Install Hermes separately
from a source you trust; this installer downloads nothing.

| Key option | Configuration |
| --- | --- |
| Any OpenAI-compatible key | Set `provider.base_url`, `model`, and `api_key_env`; remove the seat sections if uncapped. |
| A key with a daily dollar cap | Put every profile sharing that key in one seat group and set `daily_cap_usd`. |
| A capped seat key | The same seat-group configuration; no special provider required. |
| A second compatible provider | Fill the optional `fallback` section; profile configs use Hermes' fallback model support. |

## Quickstart

On Debian 12+ or Ubuntu 24.04+, as the non-root user that owns your Hermes install:

1. Obtain a trusted local checkout and run `sh install/install.sh`. It verifies
   SHA-256 hashes, creates `config.toml`, runtime directories and all ten profile
   templates, and preserves existing files on subsequent runs.
2. Edit `config.toml`: replace the placeholder Telegram IDs, provider endpoint
   and model. Set `hermes.command` to the **absolute** path of your Hermes CLI
   (systemd does not inherit your interactive PATH). Use a dedicated board name
   and ensure no other gateway or dispatcher runs that board.
3. Put `TELEGRAM_BOT_TOKEN` and your configured model environment variables into
   `service.env`, with `chmod 600 service.env`. For the sample capped layout,
   each group has its own key variable. A shared key belongs in one group,
   so its spending is counted once. Remove unused seat groups for a smaller team.
4. Run the installer again after editing configuration. It refreshes generated
   profile configs that you have not modified; manual profile edits are preserved.
   Profiles live under `${HERMES_HOME:-$HOME/.hermes}/profiles/`.
   Exported model credentials at install time seed each profile's `.env`;
   otherwise set those files yourself. Never put the bot token in a profile.
5. Start locally to verify configuration:

   ```sh
   set -a
   . ./service.env
   set +a
   export TEAM_CONFIG="$PWD/config.toml"
   python3 gate/gate.py
   ```

   In a second terminal with the same environment, run
   `python3 take-tasks/take-tasks.py` and `python3 install/dispatch.py` after
   sending the bot `/start`, then `task write code to parse a public dataset`.
   The task appears under `var/gate/tasks/`; a card ID appears under
   `var/out/tasks/`. The profile writes `handoff.md` with `## owner (en)` and
   `## details (en)`. The report returns to the gate for review.
6. The single documented root step installs and enables systemd services:

   ```sh
   sudo sh install/install-systemd.sh YOUR_USER /absolute/path/to/kit
   ```

   Keep the default `var/` layout when using the units. If you relocate runtime
   paths, adjust `ReadWritePaths` in the gate unit before starting it. Inspect
   `journalctl -u team-gate -u team-tasks` if a task stays queued.

The services run as your non-root account. The default single-user mode trusts
that account and its agents with the bot credentials and decision state; this
is a convenience deployment, not OS isolation. See the
[threat model](docs/THREAT-MODEL.md) before allowing untrusted agents or guests.
No model, publication, release or remote action happens during installation.

## Operation and accounting

Use `/pending`, `/tasks`, `/status`, `/task`, `/pause`, `/resume` and `/help`, or the
persistent keyboard. Reports being deepened leave review until a child report
arrives. A report's **ok** marks the task accepted for accounting; it does not
publish anything. `/pause` stops dispatch; already running cards finish.

```sh
python3 ledger.py report --days 7
python3 breaker.py
```

The append-only JSONL ledger stores task/card identifiers, profile, model,
provider, tokens, dollars and duration. Unknown values remain `null` or `unknown`.
Accepted tasks are distinct task IDs, counted per profile over the same period
as spend; the numerator includes all finished work in that period, including
rejected work. A profile with missing cost information has an unknown rate.

Hermes run `metadata` may supply `cost_usd`, `tokens`, `model`, `provider` and
`duration`; these fields can also be top-level run fields. The kit records all
ended runs on a completed task. If your Hermes version omits usage, supply
completion events through `ledger.py append` from your accounting integration.
Use stable event IDs to avoid duplicates. No model call is made to estimate cost.

The breaker uses a configured HTTPS usage URL when available. Its adapter expects
`daily_cap_usd`, `spent_usd` and an ISO timestamp `reset_at`; map a provider's own
schema to this contract if necessary. Otherwise it sums local ledger spending
since `reset_hour_utc`. At 80% it defers new tasks and parks ready cards for that
group, releasing only cards it parked after reset. It never interrupts a running
card. Unknown local costs pause a capped group until accurate accounting is
available or the daily window resets. Uncapped keys need no usage endpoint.
The optional status **key balance** is the total remaining dispatch allowance
up to the breaker threshold, from a snapshot no older than ten minutes.

Do not run another dispatcher on the same board: it can bypass the timer's
breaker enforcement. This is a cooperative scheduling guard; a provider-side
cap is needed for a hard spending limit. Native fallback is configured in
Hermes profiles; budget exhaustion normally routes to an available group's
profile, while provider failures can use the profile's secondary provider.

Guests have a generic `ref https://example.com/article [note]` command, their
own report history and an optional deeper pass. Private/local URLs are refused;
retrieved content remains untrusted. Guest reports contain only handoff sections,
not raw run summaries or artifact paths. UI and handoff language default to
English; set `telegram.locale = "ru"` to use the preserved Russian UI.

## Verification

```sh
python3 tests/run.py
python3 tests/check_source.py
python3 tests/smoke/local.py
```

The smoke test copies a fresh tree into a temporary directory, installs twice,
sends an English owner update through the real gate, creates a card through
the real dispatcher and an isolated fake Hermes CLI, files its English report,
accepts it through the gate, and checks the ledger and tampered-hash rejection. It uses no credentials or
network. Run `sh tests/smoke/vm.sh` inside a fresh VM as its non-root user; set
`CHECK_SERVICES=1` after completing the real service setup to check the units.
Live Telegram/model execution and VM service setup require your own environment.
CI runs the suites and local smoke test on each push and pull request.

`gate/` holds the single-file gate, `take-tasks/` the dispatcher, `profiles/`
the role templates, `install/` the installer and units, `docs/` the operational
notes, and `tests/` the checks. Nothing is published by this repository.
