# Feed cleanup, 2026-11-21

Not served: GitHub Pages publishes `docs/` only.

## Where the list comes from

`docs/feeds.json` is the source of truth, edited by hand. Evidence:

- The site loads only `./feeds.json` (`docs/app.js`). `docs/index.html` switched its
  `<noscript>` pointer from `/app.json` to `/feeds.json` in 9aca7f2 (2025-05-26).
- `docs/app.json` (`{banner, feeds}`, 25 feeds, one with a ~180 KB description) is
  the old format from before that change. Nothing reads it, and its feed list is
  not a superset of `feeds.json` (21 shared, 4 only there, 134 only in `feeds.json`).
- `~/Code/security-feeds` (`python -m secfeeds`) reads `urls.txt` and writes
  `{id, text, title, subtitle, description, type, xmlUrl, htmlUrl, ...}`, with `type` set to
  the XML root tag (e.g. `{http://www.w3.org/2005/Atom}feed`). That is not the
  `{url, title, description, type: "rss"|"atom"}` shape in `feeds.json`, and `urls.txt` has never
  been committed in either repo. The 2026 additions (a038bed, 394a837) are
  hand-written 6-line blocks in `feeds.json`.
- Downstream: the mirror Worker's `worker/scripts/build-allowlist.mjs` reads
  `docs/feeds.json` from `main` (by default). Its slugs are hashes of the feed URL, so a
  **changed URL gets a new mirror slug and path**.

So the fix is an edit to `docs/feeds.json` only, and `app.json` stays as it is.

## Method

`curl -4 -L --retry 2 --retry-all-errors --connect-timeout 10 -m 30` with a
browser User-Agent and an `Accept` header for RSS/Atom. Each body's root element was
checked, and every replacement was parsed with Python `xml.etree` to read its
title and newest item. Replacement URLs came from the publisher's own pages: their
`<link rel="alternate">` or the redirect target of the old page. Run from the agent
container on 2026-11-21.

## Results (155 → 143 feeds)

| Old URL | Action | New URL | Evidence |
|---|---|---|---|
| https://msrc.microsoft.com/blog/feed | removed | — | 301 → www.microsoft.com/en-us/msrc/blog (HTML). The new blog has no `rel=alternate` feed; `/feed`, `/rss` and `/feed.xml` there return 404. `msrc.microsoft.com/feed` is RSS but contains only a "Content Not Found" placeholder item from 2022. |
| https://msrc.microsoft.com/blog/categories/microsoft-threat-hunting/feed | removed | — | same 301 to the HTML blog |
| https://msrc.microsoft.com/blog/categories/bug-bounty-programs/feed | removed | — | same |
| https://msrc.microsoft.com/blog/categories/bluehat/feed | removed | — | same |
| https://msrc.microsoft.com/blog/categories/security-research-defense/feed | removed | — | same |
| https://msrc.microsoft.com/blog/categories/msrc/feed | removed | — | same |
| https://msrc.microsoft.com/blog/categories/japan-security-team/feed | removed | — | same |
| https://www.ncsc.govt.nz/news/category/cyber-threat-reports/rss | removed | — | 404. The site advertises no feed (no `rel=alternate`; `/news/rss`, `/rss`, `/news/feed`, `/alerts/rss` and `/alerts/feed` all return 404). It offers email sign-up instead. |
| https://www.ncsc.govt.nz/news/category/cyber-security-alerts/rss | removed | — | same |
| https://www.ncsc.govt.nz/news/category/security-advisories/rss | removed | — | same |
| https://blog.google/threat-analysis-group/rss/ | replaced | https://blog.google/security/rss/ | old feed 404. `blog.google/threat-analysis-group/` now redirects to `blog.google/security/`, whose page links `/security/rss/`. That URL returns 200 RSS "Security" with 20 items, the newest dated 2026-11-19. (Threat research from GTIG is already listed as `cloudblog.withgoogle.com/topics/threat-intelligence/rss`.) |
| https://owasp.org/feed.xml | removed | — | 404. The rebuilt owasp.org advertises no feed. `/feed`, `/rss`, `/rss.xml` and `/index.xml` return 404, and `/blog/feed.xml` redirects to a 404 on owasp.github.io. |
| https://thecyberwire.com/feeds/rss.xml | replaced | https://thecyberwire.com/index.rss | old feed 404. The homepage's `<link rel="alternate" type="application/rss+xml">` points to the new URL, which returns 200 RSS "N2K CyberWire" with its newest item dated 2026-11-20. |
| https://www.cyber.gov.au/rss/advisories | **kept** (known issue) | — | Unreachable from here: HTTP/2 INTERNAL_ERROR, and a 60 s timeout over HTTP/1.1. Akamai edge; likely blocks this network. Not proof the feed is gone. |
| https://www.cyber.gov.au/rss/alerts | **kept** (known issue) | — | same |
| https://www.cyber.gov.au/rss/threats | **kept** (known issue) | — | same |
| https://www.oracle.com/ocom/groups/public/@otn/documents/webcontent/rss-otn-sec.xml | **kept** (known issue) | — | Returns 200 RSS today with browser, `SecFeeds/1.0` and `curl` User-Agents. The earlier 403 came from Akamai, so treat it as flaky. |
| https://www.cybereason.com/blog/rss.xml | replaced | https://www.levelblue.com/blogs/levelblue-blog/rss.xml | Not a Cloudflare challenge any more: it 301s to the www.levelblue.com homepage (HTML), so the Cybereason blog feed is gone. The LevelBlue blog page links this feed via `rel=alternate`. It returns 200 RSS "LevelBlue Blog" with its newest item dated 2026-11-18. **Decision for the owner**: keep the successor's feed or drop it. |
| https://www.theregister.com/security/headlines.atom | kept, `type` atom → rss | (same URL) | 200 over IPv4. It now redirects to `api.theregister.com/...&remapper=rss` and serves RSS 2.0 (50 items), not Atom. The earlier error was this container's IPv6 DNS. |
| https://aws.amazon.com/blogs/security/feed/ | kept | — | 200 RSS over IPv4 (the earlier error was IPv6 DNS) |
| https://kb.cert.org/vuls/atomfeed | replaced | https://kb.cert.org/vuls/atomfeed/ | 200 over IPv4 after a redirect to the trailing-slash URL. The new URL is the canonical one and returns Atom directly, with 15 entries updated 2026-11-20. |
| https://krebsonsecurity.com/feed/atom/ | removed | — | Redirect loop: the https URL 301s to the `http://` URL, which comes back to https, until curl hits 50 redirects. The homepage advertises only `/feed/` (RSS), which is already listed and returns 200 RSS. |
| https://www.bleepingcomputer.com/feed/ | kept | — | 200 RSS from here. It is blocked only for Cloudflare Worker IPs (existing known issue). |

## Proposed `known-issues.json` entries for the mirror Worker

The slugs below are computed with `build-allowlist.mjs`'s `slugify`. Re-implementing it
reproduces the existing `bleepingcomputer-com-9676af` slug.

```json
{
  "bleepingcomputer-com-9676af": "Upstream blocks Cloudflare Worker IPs (Cloudflare error 1106)",
  "oracle-com-ocom-groups-public-otn-documents-webcontent-rss-o-6d63a7": "Akamai intermittently returns 403 to automated clients",
  "cyber-gov-au-rss-advisories-fdea1d": "Akamai edge stalls or resets some networks (HTTP/2 INTERNAL_ERROR, timeouts)",
  "cyber-gov-au-rss-alerts-9c7206": "Akamai edge stalls or resets some networks (HTTP/2 INTERNAL_ERROR, timeouts)",
  "cyber-gov-au-rss-threats-c2d6fd": "Akamai edge stalls or resets some networks (HTTP/2 INTERNAL_ERROR, timeouts)"
}
```

## Also seen in a full sweep (not changed)

- `https://blog.qualys.com/feed/atom`: 403 HTML from here. The other Qualys feed in the list works.
- `https://blog.google/technology/safety-security/rss/` works, via a redirect to
  `blog.google/innovation-and-ai/technology/safety-security/rss/`.
