"""The HTML served by GET /status.

Kept as a plain string (rather than a Jinja template file) so that PyInstaller
bundles it into run.exe automatically with no ``datas`` entry in run.spec.
It is fully self-contained: no CDN, no external fonts, no build step.
"""

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{APP_NAME}} - Status</title>
<style>
  :root {
    --bg: #f6f7f9;  --panel: #ffffff; --text: #14181f; --muted: #5c6672;
    --border: #e2e6ea; --ok: #10893e; --okbg: #e8f6ed; --bad: #c02b2b;
    --badbg: #fdecec; --warn: #b06a00; --warnbg: #fdf3e3; --accent: #2a5db0;
    --mono: ui-monospace, SFMono-Regular, Consolas, "Courier New", monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14171c; --panel: #1c2027; --text: #e8eaed; --muted: #9aa4b1;
      --border: #2b313a; --ok: #4ade80; --okbg: #14301f; --bad: #f87171;
      --badbg: #341a1a; --warn: #fbbf24; --warnbg: #332612; --accent: #7aa5f0;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 24px; background: var(--bg); color: var(--text);
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 14px; line-height: 1.5;
  }
  .wrap { max-width: 1100px; margin: 0 auto; }
  header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 12px; margin-bottom: 20px; }
  h1 { font-size: 20px; margin: 0; font-weight: 650; }
  .ver { font-family: var(--mono); font-size: 12px; color: var(--muted);
         border: 1px solid var(--border); border-radius: 999px; padding: 2px 10px; }
  .spacer { flex: 1; }
  .refresh { font-size: 12px; color: var(--muted); }

  .banner {
    border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;
    display: flex; align-items: center; gap: 16px; border: 1px solid transparent;
  }
  .banner.ok   { background: var(--okbg);   border-color: var(--ok);   }
  .banner.bad  { background: var(--badbg);  border-color: var(--bad);  }
  .banner.wait { background: var(--warnbg); border-color: var(--warn); }
  /* Serving correctly, but something in config.json still needs fixing. */
  .banner.warn { background: var(--warnbg); border-color: var(--warn); }
  .dot { width: 14px; height: 14px; border-radius: 50%; flex: none; }
  .banner.ok   .dot { background: var(--ok);   animation: pulse 2s infinite; }
  .banner.bad  .dot { background: var(--bad);  }
  .banner.wait .dot { background: var(--warn); }
  .banner.warn .dot { background: var(--warn); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
  .banner .headline { font-size: 18px; font-weight: 650; }
  .banner .sub { font-size: 13px; color: var(--muted); }

  .grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); margin-bottom: 20px; }
  .card { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
  .card .label { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
  .card .value { font-size: 22px; font-weight: 650; margin-top: 4px; font-variant-numeric: tabular-nums; }
  .card .value.small { font-size: 15px; font-weight: 550; word-break: break-word; }

  section { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 16px; overflow: hidden; }
  section > h2 { font-size: 13px; margin: 0; padding: 12px 16px; border-bottom: 1px solid var(--border);
                 text-transform: uppercase; letter-spacing: .06em; color: var(--muted); font-weight: 600; }
  .body { padding: 4px 16px 14px; }
  .scroll { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; font-weight: 600; color: var(--muted); font-size: 11px;
       text-transform: uppercase; letter-spacing: .05em; padding: 10px 8px; border-bottom: 1px solid var(--border); }
  td { padding: 8px; border-bottom: 1px solid var(--border); font-variant-numeric: tabular-nums; }
  tr:last-child td { border-bottom: none; }
  td.mono, .mono { font-family: var(--mono); font-size: 12px; }
  /* Driver errors can be several hundred characters - clamp them to one line
     and keep the full text in the title attribute. */
  td.detail { max-width: 320px; white-space: nowrap; overflow: hidden;
              text-overflow: ellipsis; color: var(--bad); cursor: help; }
  td.nowrap { white-space: nowrap; }
  .pill { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11px;
          font-weight: 600; font-family: var(--mono); }
  .pill.s2 { background: var(--okbg); color: var(--ok); }
  .pill.s4 { background: var(--warnbg); color: var(--warn); }
  .pill.s5 { background: var(--badbg); color: var(--bad); }
  .check { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--border); }
  .check:last-child { border-bottom: none; }
  .check .mark { font-weight: 700; flex: none; width: 18px; }
  .check .mark.ok { color: var(--ok); } .check .mark.bad { color: var(--bad); }
  .check .mark.warn { color: var(--warn); }
  .check .name { font-weight: 600; min-width: 90px; }
  .check .detail { color: var(--muted); font-family: var(--mono); font-size: 12px; word-break: break-all; }
  /* A check that passed but wants attention - e.g. a config.json that only
     loaded because its backslashes were repaired. */
  .check .detail.warn { color: var(--warn); }
  .empty { color: var(--muted); padding: 14px 0; font-style: italic; }
  a { color: var(--accent); }
  .links { display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 16px 16px; }
  .links a { font-family: var(--mono); font-size: 12px; text-decoration: none;
             border: 1px solid var(--border); border-radius: 6px; padding: 5px 10px; }
  .links a:hover { border-color: var(--accent); }
  footer { color: var(--muted); font-size: 12px; text-align: center; padding: 8px 0 24px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{{APP_NAME}}</h1>
    <span class="ver">v{{VERSION}}</span>
    <span class="spacer"></span>
    <span class="refresh">auto-refresh 5s &middot; last update <span id="lastUpdate">-</span></span>
  </header>

  <div class="banner wait" id="banner">
    <div class="dot"></div>
    <div>
      <div class="headline" id="headline">Connecting&hellip;</div>
      <div class="sub" id="subline">Contacting the API</div>
    </div>
  </div>

  <div class="grid">
    <div class="card"><div class="label">Uptime</div><div class="value" id="uptime">-</div></div>
    <div class="card"><div class="label">Requests served</div><div class="value" id="requests">-</div></div>
    <div class="card"><div class="label">Failed responses</div><div class="value" id="errors">-</div></div>
    <div class="card"><div class="label">DB response</div><div class="value" id="dbLatency">-</div></div>
    <div class="card"><div class="label">Host</div><div class="value small" id="host">-</div></div>
    <div class="card"><div class="label">Process ID</div><div class="value small" id="pid">-</div></div>
  </div>

  <section>
    <h2>System checks</h2>
    <div class="body" id="checks"><div class="empty">Loading&hellip;</div></div>
  </section>

  <section>
    <h2>Recent requests</h2>
    <div class="body scroll" id="recent"><div class="empty">Loading&hellip;</div></div>
  </section>

  <section>
    <h2>Recent errors</h2>
    <div class="body scroll" id="recentErrors"><div class="empty">Loading&hellip;</div></div>
  </section>

  <section>
    <h2>Busiest endpoints</h2>
    <div class="body scroll" id="top"><div class="empty">Loading&hellip;</div></div>
  </section>

  <section>
    <h2>Raw endpoints</h2>
    <div class="links">
      <a href="/health" target="_blank">/health</a>
      <a href="/version" target="_blank">/version</a>
      <a href="/metrics" target="_blank">/metrics</a>
      <a href="/routes" target="_blank">/routes</a>
      <a href="/ping" target="_blank">/ping</a>
    </div>
  </section>

  <footer>Logs are written to the <span class="mono" id="logdir">logs</span> folder.</footer>
</div>

<script>
(function () {
  var $ = function (id) { return document.getElementById(id); };

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function pillClass(status) {
    if (status >= 500) return "s5";
    if (status >= 400) return "s4";
    return "s2";
  }

  function shortTime(iso) {
    if (!iso) return "-";
    var d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleTimeString();
  }

  function setBanner(kind, headline, sub) {
    $("banner").className = "banner " + kind;
    $("headline").textContent = headline;
    $("subline").textContent = sub;
  }

  function renderChecks(checks) {
    var rows = Object.keys(checks || {}).map(function (name) {
      var c = checks[name];
      // A warning means the check passed but the operator still has something
      // to fix - show it instead of the bland "OK" that would otherwise hide it.
      var warned = c.ok && c.warning;
      var detail = c.error ? c.error
                 : (c.warning ? c.warning
                 : (c.uri ? c.uri + "  (" + c.latencyMs + " ms)"
                 : (c.path || c.file || "OK")));
      var mark = c.ok ? (warned ? "warn" : "ok") : "bad";
      var glyph = c.ok ? (warned ? "!" : "✓") : "✗";
      return '<div class="check">'
           +   '<span class="mark ' + mark + '">' + glyph + "</span>"
           +   '<span class="name">' + esc(name) + "</span>"
           +   '<span class="detail' + (warned ? " warn" : "") + '">' + esc(detail) + "</span>"
           + "</div>";
    });
    $("checks").innerHTML = rows.length ? rows.join("") : '<div class="empty">No checks reported.</div>';
  }

  function renderRequests(target, list, emptyText) {
    if (!list || !list.length) {
      $(target).innerHTML = '<div class="empty">' + emptyText + "</div>";
      return;
    }
    var rows = list.map(function (r) {
      return "<tr>"
           + '<td class="nowrap">' + esc(shortTime(r.time)) + "</td>"
           + '<td class="mono">' + esc(r.method) + "</td>"
           + '<td class="mono nowrap">' + esc(r.path) + "</td>"
           + '<td><span class="pill ' + pillClass(r.status) + '">' + esc(r.status) + "</span></td>"
           + '<td class="nowrap">' + esc(r.durationMs) + " ms</td>"
           + (r.error
                ? '<td class="mono detail" title="' + esc(r.error) + '">' + esc(r.error) + "</td>"
                : "<td></td>")
           + "</tr>";
    });
    $(target).innerHTML = "<table><thead><tr><th>Time</th><th>Method</th><th>Path</th>"
                        + "<th>Status</th><th>Duration</th><th>Detail</th></tr></thead><tbody>"
                        + rows.join("") + "</tbody></table>";
  }

  function renderTop(list) {
    if (!list || !list.length) {
      $("top").innerHTML = '<div class="empty">No traffic yet.</div>';
      return;
    }
    var max = Math.max.apply(null, list.map(function (i) { return i.count; }));
    var rows = list.map(function (i) {
      var pct = Math.round((i.count / max) * 100);
      return "<tr><td class='mono'>" + esc(i.endpoint) + "</td>"
           + "<td style='width:55%'><div style='background:var(--accent);height:8px;border-radius:4px;width:"
           + pct + "%'></div></td>"
           + "<td style='text-align:right'>" + esc(i.count) + "</td></tr>";
    });
    $("top").innerHTML = "<table><thead><tr><th>Endpoint</th><th>Share</th><th style='text-align:right'>Calls</th>"
                       + "</tr></thead><tbody>" + rows.join("") + "</tbody></table>";
  }

  function applyVitals(h) {
    $("uptime").textContent = h.uptimeHuman || "-";
    $("host").textContent = h.host || "-";
    $("pid").textContent = h.pid || "-";
    $("logdir").textContent = h.logDirectory || "logs";
    $("lastUpdate").textContent = new Date().toLocaleTimeString();
  }

  function getJSON(url) {
    return fetch(url, { cache: "no-store" }).then(function (r) { return r.json(); });
  }

  // Phase 1: the shallow check answers instantly and proves the process is
  // serving requests. Phase 2 adds the database and disk probes, which can take
  // several seconds when the database server is unreachable - we must not make
  // the operator stare at "Connecting..." while that times out.
  var firstLoad = true;

  function refresh() {
    getJSON("/health?deep=false").then(function (h) {
      applyVitals(h);
      // Only on the very first load - after that we keep the last known deep
      // result on screen instead of flashing "checking…" every 5 seconds.
      if (firstLoad) {
        setBanner("wait", "API is up and responding",
                  "Process alive since " + shortTime(h.startedAt) + " · checking database…");
      }
      return getJSON("/metrics");
    }).then(function (m) {
      $("requests").textContent = m.totalRequests;
      $("errors").textContent = m.totalErrors;
      renderRequests("recent", m.recentRequests, "No requests yet. Call an endpoint and it will show up here.");
      renderRequests("recentErrors", m.recentErrors, "No errors recorded. ✓");
      renderTop(m.topEndpoints);

      return getJSON("/health");   // deep check - may be slow
    }).then(function (h) {
      applyVitals(h);

      if (h.healthy) {
        // Healthy, but a check may still be carrying a warning - most often a
        // config.json that only loaded because its backslashes were repaired.
        var warned = Object.keys(h.checks || {}).filter(function (k) {
          return h.checks[k].ok && h.checks[k].warning;
        });
        if (warned.length) {
          setBanner("warn", "API is running, but a setting needs fixing",
                    "Warning on: " + warned.join(", ") + " - see System checks below");
        } else {
          setBanner("ok", "API is running normally",
                    "All checks passing · up since " + shortTime(h.startedAt));
        }
      } else {
        var failed = Object.keys(h.checks || {}).filter(function (k) { return !h.checks[k].ok; });
        setBanner("bad", "API is up, but a dependency is broken",
                  "Failing check: " + (failed.join(", ") || "unknown") + " - see System checks below");
      }

      var db = (h.checks || {}).database;
      $("dbLatency").textContent = db ? (db.ok ? db.latencyMs + " ms" : "unreachable") : "not checked";
      renderChecks(h.checks);
      firstLoad = false;
    }).catch(function (err) {
      setBanner("bad", "Cannot reach the API",
                "Nothing is answering on this address (" + err + "). "
                + "Check the service is started and the port is correct.");
      $("dbLatency").textContent = "-";
    });
  }

  refresh();
  setInterval(refresh, 5000);
})();
</script>
</body>
</html>
"""
