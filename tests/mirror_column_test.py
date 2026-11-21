"""Fixture-driven DOM test for the mirror column.

Usage: python3 -I tests/mirror_column_test.py docs <path-to-chrome-headless-shell>

chrome-headless-shell is the Playwright build, e.g.
~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux-*/chrome-headless-shell.
It needs glib/nss/X11/fontconfig libraries; without root they can be unpacked
from .debs (apt-get download + dpkg -x) and passed via LD_LIBRARY_PATH and
FONTCONFIG_FILE.

For each scenario: copy docs/ to a temp site, add a fake mirror/mirrors.json
(or none / broken JSON), inject a probe script into index.html, serve the site
with http.server, load it in chrome-headless-shell --dump-dom, then parse the
probe's JSON output and assert on it.
"""
import functools, http.server, json, re, shutil, socketserver, subprocess, sys, tempfile, threading
from pathlib import Path

DOCS, CHROME = Path(sys.argv[1]), sys.argv[2]
FEEDS = json.loads((DOCS / "feeds.json").read_text())
URLS = [f["url"] for f in FEEDS]
U_OK, U_STALE, U_STALE_OLD, U_ERR, U_PEND_KI, U_MISSING, U_OK_KI, U_NOT_LISTED = (
    "https://thecyberwire.com/index.rss",
    "https://blog.google/security/rss/",
    "https://www.levelblue.com/blogs/levelblue-blog/rss.xml",
    "https://kb.cert.org/vuls/atomfeed/",
    "https://www.cyber.gov.au/rss/alerts",
    "https://www.cyber.gov.au/rss/threats",
    "https://www.bleepingcomputer.com/feed/",
    "https://krebsonsecurity.com/feed/",
)
U_NOT_LISTED_JS = "https://www.cyber.gov.au/rss/advisories"
assert all(u in URLS for u in [U_NOT_LISTED_JS, U_OK, U_STALE, U_STALE_OLD, U_ERR, U_PEND_KI, U_MISSING, U_OK_KI, U_NOT_LISTED])

FULL = {
    "mirror_base": "https://securityfeeds.org/mirror",
    "fetchers": [
        {"id": "worker", "updated_at": "2026-11-21T04:00:00Z", "stale": False, "ok": 3, "total": 9},
        {"id": "droplet", "updated_at": "2026-11-21T03:55:00Z", "stale": False, "ok": 4, "total": 9},
    ],
    "feeds": [
        {"source": U_OK, "mirror": "/mirror/cyberwire-ok", "status": "ok", "served_by": "droplet",
         "fetchers": {"worker": {"status": "error"}, "droplet": {"status": "ok"}}},
        {"source": U_STALE, "mirror": "/mirror/google-stale", "status": "stale", "last_ok": "2026-11-20T10:00:00Z",
         "error": "HTTP 500"},
        # old worker shape: status error + last_ok => stale
        {"source": U_STALE_OLD, "mirror": "/mirror/levelblue-old", "status": "error", "last_ok": "2026-11-19T00:00:00Z",
         "error": "timeout"},
        # error without a previous good copy => unavailable, tooltip = error
        {"source": U_ERR, "mirror": "/mirror/cert-err", "status": "error", "error": "HTTP 403 from upstream"},
        # pending + known_issue => unavailable, tooltip = known_issue
        {"source": U_PEND_KI, "mirror": "/mirror/acsc", "status": "pending", "known_issue": "Akamai edge stalls"},
        # explicit missing, nothing else => unavailable, default tooltip
        {"source": U_MISSING, "mirror": "/mirror/acsc-threats", "status": "missing"},
        # ok but has a known issue (another fetcher works) => link + tooltip
        {"source": U_OK_KI, "mirror": "/mirror/bleeping", "status": "ok", "served_by": "droplet",
         "known_issue": "Upstream blocks Cloudflare Worker IPs"},
        # ok but a non-http(s) mirror URL => never linked
        {"source": U_NOT_LISTED_JS, "mirror": "javascript:alert(1)", "status": "ok"},
        # mirror entry for a feed not in feeds.json: ignored
        {"source": "https://example.invalid/feed", "mirror": "/mirror/x", "status": "ok"},
        {"mirror": "/mirror/no-source", "status": "ok"},
    ],
}

PROBE = r"""
<script>
(function () {
  function rows() {
    var t = document.getElementById("app-table"); if (!t) return null;
    var hdr = [].map.call(t.rows[0].cells, function (c) { return c.textContent; });
    return { header: hdr, rows: [].slice.call(t.rows, 1).map(function (r) {
      var m = r.cells[1];
      return { url: r.cells[0].textContent, cells: r.cells.length, mirror_text: m.textContent,
               mirror_href: m.querySelector("a") ? m.querySelector("a").getAttribute("href") : null,
               mirror_title: m.title, mirror_class: m.className };
    }) };
  }
  function search(term) {
    var box = document.getElementById("search-box"); box.value = term;
    box.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true }));
    return rows().rows.map(function (r) { return r.url; });
  }
  var errors = [];
  window.addEventListener("error", function (e) { errors.push(String(e.message)); });
  window.addEventListener("unhandledrejection", function (e) { errors.push("unhandled: " + e.reason); });
  function wait(n) {
    var t = document.getElementById("app-table");
    if (!t && n > 0) return setTimeout(function () { wait(n - 1); }, 50);
    var out = { initial: rows(), errors: errors };
    if (t) {
      out.search = { cyberwire: search("cyberwire"), mirror_only_text: search("Akamai edge"),
                     mirror_path: search("/mirror/"), cleared: search("").length };
      out.after_search = rows();
    }
    var pre = document.createElement("pre"); pre.id = "probe"; pre.textContent = JSON.stringify(out);
    document.body.appendChild(pre);
  }
  document.addEventListener("DOMContentLoaded", function () { setTimeout(function () { wait(100); }, 0); });
})();
</script>
"""


def run_scenario(name, mirrors):
    site = Path(tempfile.mkdtemp(prefix=f"site-{name}-"))
    shutil.copytree(DOCS, site, dirs_exist_ok=True)
    html = (site / "index.html").read_text()
    (site / "index.html").write_text(html.replace("</head>", PROBE + "</head>"))
    if mirrors is not None:
        (site / "mirror").mkdir()
        (site / "mirror" / "mirrors.json").write_text(mirrors if isinstance(mirrors, str) else json.dumps(mirrors))
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    handler = functools.partial(Quiet, directory=str(site))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{srv.server_address[1]}/"
        dom = subprocess.run([CHROME, "--no-sandbox", "--disable-gpu", "--virtual-time-budget=10000",
                              "--dump-dom", url], capture_output=True, text=True, timeout=60).stdout
        srv.shutdown()
    shutil.rmtree(site)
    m = re.search(r'<pre id="probe">(.*?)</pre>', dom, re.S)
    assert m, f"{name}: probe output missing; DOM head: {dom[:500]}"
    import html as h
    return json.loads(h.unescape(m.group(1)))


failures = []
def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond: failures.append(msg)


def common(name, out, expect_rows):
    check(out["errors"] == [], f"{name}: no JS errors {out['errors']}")
    init = out["initial"]
    check(init is not None, f"{name}: table rendered")
    if not init: return {}
    check(init["header"] == ["url", "mirror", "title", "description", "type"], f"{name}: header {init['header']}")
    check(len(init["rows"]) == expect_rows, f"{name}: {len(init['rows'])} rows == {expect_rows}")
    check(all(r["cells"] == 5 for r in init["rows"]), f"{name}: every row has 5 cells")
    s = out["search"]
    check(s["cyberwire"] == [U_OK], f"{name}: search 'cyberwire' -> {s['cyberwire']}")
    check(s["mirror_only_text"] == [], f"{name}: text found only in mirrors.json does not match search")
    check(s["mirror_path"] == [], f"{name}: '/mirror/' does not match search")
    check(s["cleared"] == expect_rows, f"{name}: clearing search restores all rows")
    return {r["url"]: r for r in out["after_search"]["rows"]}


n = len(FEEDS)
# 1. full fixture
out = run_scenario("full", FULL)
by = common("full", out, n)
r = by[U_OK]; check(r["mirror_text"] == "mirror" and r["mirror_href"] == "/mirror/cyberwire-ok", f"ok: {r}")
check("served by droplet" in r["mirror_title"] and "mirror-ok" in r["mirror_class"], f"ok title/class: {r}")
r = by[U_STALE]; check(r["mirror_text"] == "mirror (stale)" and r["mirror_href"] == "/mirror/google-stale", f"stale: {r}")
check("HTTP 500" in r["mirror_title"] and "mirror-stale" in r["mirror_class"], f"stale title/class: {r}")
r = by[U_STALE_OLD]; check(r["mirror_text"] == "mirror (stale)" and "timeout" in r["mirror_title"], f"error+last_ok => stale: {r}")
r = by[U_ERR]; check(r["mirror_text"] == "unavailable" and r["mirror_href"] is None and r["mirror_title"] == "HTTP 403 from upstream", f"error => unavailable(error): {r}")
r = by[U_PEND_KI]; check(r["mirror_text"] == "unavailable" and r["mirror_title"] == "Akamai edge stalls" and "mirror-missing" in r["mirror_class"], f"pending+known_issue: {r}")
r = by[U_MISSING]; check(r["mirror_text"] == "unavailable" and r["mirror_title"] == "not mirrored yet", f"missing: {r}")
r = by[U_OK_KI]; check(r["mirror_text"] == "mirror" and r["mirror_href"] == "/mirror/bleeping" and "Cloudflare Worker" in r["mirror_title"], f"ok+known_issue: {r}")
r = by[U_NOT_LISTED]; check(r["mirror_text"] == "" and r["mirror_title"] == "" and r["mirror_class"] == "mirror", f"not in mirrors.json => empty cell: {r}")
check(not any("example.invalid" in u for u in by), "unknown mirror source not added as a row")
r = by[U_NOT_LISTED_JS]; check(r["mirror_href"] is None and r["mirror_text"] == "unavailable" and "mirror-missing" in r["mirror_class"], f"javascript: mirror URL not linked: {r}")

# 2-4. mirrors.json unavailable / broken / wrong shape: table unchanged, empty mirror column
for name, fixture in [("absent", None), ("broken-json", "{not json"), ("wrong-shape", {"feeds": "nope"})]:
    out = run_scenario(name, fixture)
    by = common(name, out, n)
    check(all(r["mirror_text"] == "" and r["mirror_href"] is None for r in by.values()), f"{name}: mirror column empty")

print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
