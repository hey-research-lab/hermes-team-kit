# Contributing

Describe the problem and intended behavior before submitting a substantial
change. Keep patches focused and use conventional lowercase commit messages
such as `fix: preserve report state`; omit AI trailers.

Use Python 3.11+ and the standard library. Follow the surrounding code style,
keep the gate deterministic, and preserve English defaults and the documented
Russian locale. Use plain factual documentation, sentence case headings, no
hype, emoji or em dashes. Never commit credentials or private runtime data.

Run all three checks from the repository root:

```sh
python3 tests/run.py
python3 tests/check_source.py
python3 tests/smoke/local.py
```

When changing packaged files, first refresh their integrity manifest:

```sh
python3 install/update_hashes.py
```

Add regression coverage for behavior changes. The local smoke test uses a fake
Hermes CLI and needs no credentials or network. For service changes, also run
`sh tests/smoke/vm.sh` in a fresh supported Linux VM as its non-root user; use
`CHECK_SERVICES=1` after the real service setup. Describe any unrun live or VM
checks in the pull request. Review the tree and Git history for deployment
identifiers and secrets before proposing a change. Report security problems
privately as described in [SECURITY.md](SECURITY.md).
