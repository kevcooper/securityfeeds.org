# Tests

These aren't served (GitHub Pages publishes `docs/` only).

## Mirror column DOM test

```sh
tests/run.sh
```

`mirror_column_test.py` copies `docs/` to a temp directory and adds fixture
`mirror/mirrors.json` files. It covers these cases: ok, stale, an old-style error
with `last_ok`, error, pending with a known issue, missing, ok with a known issue,
a non-http link, an unknown source, and a file that is absent, broken or the wrong
shape. Each copy is served with `http.server` and loaded in `chrome-headless-shell --dump-dom`.
A probe script injected into the page records the rendered mirror cells, tooltips,
classes and search results. The test asserts on those and exits non-zero if
anything fails.

### Setup

`tests/setup-headless.sh` does the setup, and `run.sh` calls it for you.

- **Browser:** it uses Playwright's `chrome-headless-shell`, found in
  `~/.cache/ms-playwright/` or named by `CHROME_HEADLESS_SHELL`.
- **Libraries:** it needs no system-wide installs. It downloads the shared
  libraries and fonts the browser needs as `.deb`s (`apt-get download`) and unpacks
  them with `dpkg -x` into `~/.cache/securityfeeds-test/`. Set
  `SECFEEDS_TEST_HOME` to use another location. It also writes a
  `fonts.conf` there, which matters: without fonts, Chrome aborts with a Skia
  `FATAL`.
- **Re-running:** it is idempotent and prints the `export` lines for
  `CHROME_HEADLESS_SHELL`, `LD_LIBRARY_PATH` and `FONTCONFIG_FILE`.
- **Package names:** these are Debian 13 (trixie) names, for arm64 or amd64.
- **apt lists:** if apt's package lists are empty, the script runs
  `sudo apt-get update`. That refreshes the lists only and installs nothing.

To run the test by hand:

```sh
eval "$(tests/setup-headless.sh)"
python3 -I tests/mirror_column_test.py docs "$CHROME_HEADLESS_SHELL"
```
