/* KoBALT-700 report rendering. Vanilla JS, DOM APIs only, no innerHTML with data. */
(function () {
  "use strict";

  var SVG_NS = "http://www.w3.org/2000/svg";
  var ACCENT = "#1e5b4c";
  var TRACK = "#e7e1d3";
  var GRID = "#d8d1c0";
  var INK = "#201d18";
  var MUTED = "#575046";

  function $(id) { return document.getElementById(id); }

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    if (attrs) {
      for (var k in attrs) {
        if (Object.prototype.hasOwnProperty.call(attrs, k)) {
          node.setAttribute(k, attrs[k]);
        }
      }
    }
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function svgEl(tag, attrs, text) {
    var node = document.createElementNS(SVG_NS, tag);
    if (attrs) {
      for (var k in attrs) {
        if (Object.prototype.hasOwnProperty.call(attrs, k)) {
          node.setAttribute(k, attrs[k]);
        }
      }
    }
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function isNum(x) {
    return typeof x === "number" && isFinite(x);
  }

  function pct(x, digits) {
    if (!isNum(x)) return "not reported";
    return (x * 100).toFixed(digits === undefined ? 1 : digits) + "%";
  }

  function fmtMs(ms) {
    if (!isNum(ms)) return "not recorded";
    if (ms >= 1000) return (ms / 1000).toFixed(1) + " s";
    return Math.round(ms) + " ms";
  }

  function fmtDate(iso) {
    if (typeof iso !== "string") return null;
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
    if (!m) return null;
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var idx = parseInt(m[2], 10) - 1;
    if (idx < 0 || idx > 11) return null;
    return parseInt(m[3], 10) + " " + months[idx] + " " + m[1];
  }

  function evidenceHref(path) {
    if (typeof path !== "string" || !path) return null;
    var p = path.replace(/^\.\//, "");
    if (p.indexOf("site/") === 0) p = p.slice("site/".length);
    return p;
  }

  function reasoningLabel(run) {
    if (run.reasoning_mode === "provider-default") return "Provider default";
    if (typeof run.reasoning_mode === "string" && run.reasoning_mode) {
      return "Reasoning effort: " + run.reasoning_mode;
    }
    return "Not recorded";
  }

  function shortName(run) {
    if (typeof run.label === "string" && run.label) return run.label;
    if (typeof run.model === "string" && run.model) {
      var parts = run.model.split("/");
      return parts[parts.length - 1];
    }
    return "Unnamed run";
  }

  function chartLabel(run) {
    // Compact label for SVG rows: model basename plus non-default reasoning mode.
    var base = "Unnamed run";
    if (typeof run.model === "string" && run.model) {
      var parts = run.model.split("/");
      base = parts[parts.length - 1];
    } else if (typeof run.label === "string" && run.label) {
      base = run.label;
    }
    if (typeof run.reasoning_mode === "string" && run.reasoning_mode &&
        run.reasoning_mode !== "provider-default") {
      base += " (" + run.reasoning_mode + ")";
    }
    return base;
  }

  function setStatus(text, isError) {
    var s = $("status");
    s.textContent = text;
    s.className = isError ? "status error" : "status";
  }

  function chartError(containerId, message) {
    var c = $(containerId);
    while (c.firstChild) c.removeChild(c.firstChild);
    var p = el("p", { "class": "chart-error" }, message);
    c.appendChild(p);
    c.removeAttribute("role");
  }

  /* ---------------- overall dot-and-interval chart ---------------- */

  function renderOverallChart(runs) {
    var box = $("overall-chart");
    while (box.firstChild) box.removeChild(box.firstChild);
    if (!runs.length) {
      chartError("overall-chart", "No primary runs to chart.");
      return;
    }
    var W = 680, labelW = 205, valueW = 150, padR = 8, padT = 30, rowH = 46;
    var plotX = labelW, plotW = W - labelW - valueW - padR;
    var H = padT + runs.length * rowH + 26;

    var svg = svgEl("svg", {
      viewBox: "0 0 " + W + " " + H,
      role: "presentation",
      "aria-hidden": "true",
      "font-family": "inherit"
    });
    var desc = svgEl("desc", null,
      "Dot-and-interval chart. " + runs.map(function (r) {
        var w = r.wilson_95 || {};
        return shortName(r) + ": " + pct(r.accuracy) +
          (isNum(w.lo) && isNum(w.hi)
            ? " (95% interval " + pct(w.lo) + " to " + pct(w.hi) + ")"
            : " (interval unavailable)");
      }).join(". "));
    svg.appendChild(desc);

    // gridlines + axis labels at 0/25/50/75/100
    [0, 0.25, 0.5, 0.75, 1].forEach(function (t) {
      var x = plotX + t * plotW;
      svg.appendChild(svgEl("line", {
        x1: x, y1: padT - 8, x2: x, y2: H - 24,
        stroke: GRID, "stroke-width": 1
      }));
      svg.appendChild(svgEl("text", {
        x: x, y: H - 8, "text-anchor": "middle",
        "font-size": 11, fill: MUTED
      }, Math.round(t * 100) + "%"));
    });

    runs.forEach(function (r, i) {
      var cy = padT + i * rowH + rowH / 2;
      // run label (truncated for space; full name is in the cards)
      var name = chartLabel(r);
      var shown = name.length > 30 ? name.slice(0, 29) + "…" : name;
      svg.appendChild(svgEl("text", {
        x: 12, y: cy + 4, "font-size": 12.5, fill: INK
      }, shown));

      var acc = isNum(r.accuracy) ? r.accuracy : null;
      var w = r.wilson_95 || {};
      if (acc !== null && isNum(w.lo) && isNum(w.hi)) {
        var x1 = plotX + Math.max(0, Math.min(1, w.lo)) * plotW;
        var x2 = plotX + Math.max(0, Math.min(1, w.hi)) * plotW;
        svg.appendChild(svgEl("line", {
          x1: x1, y1: cy, x2: x2, y2: cy,
          stroke: INK, "stroke-width": 2, "stroke-linecap": "round"
        }));
        [x1, x2].forEach(function (x) {
          svg.appendChild(svgEl("line", {
            x1: x, y1: cy - 5, x2: x, y2: cy + 5,
            stroke: INK, "stroke-width": 2, "stroke-linecap": "round"
          }));
        });
      }
      if (acc !== null) {
        var cx = plotX + Math.max(0, Math.min(1, acc)) * plotW;
        svg.appendChild(svgEl("circle", {
          cx: cx, cy: cy, r: 6, fill: ACCENT,
          stroke: "#ffffff", "stroke-width": 1.5
        }));
      }
      var val = acc !== null ? pct(acc) : "not reported";
      var ci = (acc !== null && isNum(w.lo) && isNum(w.hi))
        ? " (" + pct(w.lo, 1) + "–" + pct(w.hi, 1) + ")"
        : (acc !== null ? " (interval unavailable)" : "");
      svg.appendChild(svgEl("text", {
        x: W - padR, y: cy + 4, "text-anchor": "end",
        "font-size": 12, fill: INK
      }, val + ci));
    });

    box.appendChild(svg);
  }

  /* ---------------- run cards ---------------- */

  function renderCards(runs) {
    var wrap = $("run-cards");
    while (wrap.firstChild) wrap.removeChild(wrap.firstChild);
    var list = el("ul", { "class": "cards" });
    runs.forEach(function (r, i) {
      var item = el("li", null);
      var card = el("article", {
        "class": "card" + (i === 0 ? " lead" : ""),
        "aria-label": shortName(r)
      });
      card.appendChild(el("h3", null, shortName(r)));
      if (typeof r.model === "string" && r.model && r.model !== shortName(r)) {
        card.appendChild(el("p", { "class": "model-id" }, "Model id: " + r.model));
      }
      var dl = el("dl", null);
      function row(term, value, cls) {
        dl.appendChild(el("dt", null, term));
        var dd = el("dd", cls ? { "class": cls } : null, value);
        dl.appendChild(dd);
      }
      var w = r.wilson_95 || {};
      var score = pct(r.accuracy) +
        ((isNum(w.lo) && isNum(w.hi))
          ? "  (95% CI " + pct(w.lo) + "–" + pct(w.hi) + ")"
          : "  (interval unavailable)");
      row("Accuracy", score, "score");
      row("Correct", isNum(r.correct) && isNum(r.total)
        ? r.correct + " / " + r.total : "not reported");
      var inv = r.invalid || {};
      row("Invalid outputs", isNum(inv.count) && isNum(r.total)
        ? inv.count + " (" + pct(inv.rate !== undefined ? inv.rate : inv.count / r.total) + ")"
        : "not reported");
      var lat = r.latency_ms || {};
      row("Median latency", fmtMs(lat.median));
      row("Reasoning", reasoningLabel(r));
      if (typeof r.timestamp === "string" && r.timestamp) {
        var d = fmtDate(r.timestamp);
        row("Run date", d ? d + " (UTC)" : r.timestamp);
      }
      card.appendChild(dl);

      var ev = r.evidence || {};
      var evP = el("p", { "class": "evidence" });
      var snap = evidenceHref(ev.snapshot);
      var res = evidenceHref(ev.results);
      if (snap) {
        var a1 = el("a", { href: snap }, "Config snapshot");
        evP.appendChild(a1);
      }
      if (res) {
        var a2 = el("a", { href: res }, "Results JSON");
        evP.appendChild(a2);
      }
      if (!snap && !res) {
        evP.appendChild(el("span", { "class": "small" }, "Evidence files unavailable."));
      }
      card.appendChild(evP);
      item.appendChild(card);
      list.appendChild(item);
    });
    wrap.appendChild(list);
  }

  /* ---------------- grouped breakdown charts (run-major blocks) ---------------- */

  function breakdownGroups(runs, key) {
    // union of group names across runs, in first-seen order
    var names = [];
    runs.forEach(function (r) {
      var rows = Array.isArray(r[key]) ? r[key] : [];
      rows.forEach(function (g) {
        if (g && typeof g.name === "string" && names.indexOf(g.name) === -1) {
          names.push(g.name);
        }
      });
    });
    return names;
  }

  function renderBreakdownChart(containerId, runs, key, groupLabel) {
    var box = $(containerId);
    while (box.firstChild) box.removeChild(box.firstChild);
    var names = breakdownGroups(runs, key);
    if (!runs.length || !names.length) {
      chartError(containerId, "Breakdown data unavailable.");
      return false;
    }
    var W = 680, labelW = 205, valueW = 64, padR = 10;
    var plotX = labelW, plotW = W - labelW - valueW - padR;
    var rowH = 26, blockTitleH = 30, blockGap = 14, padT = 8, padB = 10;
    var H = padT + runs.length * (blockTitleH + names.length * rowH + blockGap) + padB;

    var svg = svgEl("svg", {
      viewBox: "0 0 " + W + " " + H,
      role: "presentation",
      "aria-hidden": "true",
      "font-family": "inherit"
    });
    svg.appendChild(svgEl("desc", null,
      "Bar chart of " + groupLabel + " accuracy by run, on a zero to one-hundred percent scale."));

    var y = padT;
    runs.forEach(function (r) {
      var title = chartLabel(r);
      if (title.length > 52) title = title.slice(0, 51) + "…";
      svg.appendChild(svgEl("text", {
        x: 12, y: y + 16, "font-size": 13, "font-weight": "bold", fill: INK
      }, title));
      y += blockTitleH;
      var byName = {};
      (Array.isArray(r[key]) ? r[key] : []).forEach(function (g) {
        if (g && typeof g.name === "string") byName[g.name] = g;
      });
      names.forEach(function (n) {
        var g = byName[n] || {};
        var label = n + (isNum(g.n) ? " (n=" + g.n + ")" : "");
        if (label.length > 30) label = label.slice(0, 29) + "…";
        svg.appendChild(svgEl("text", {
          x: 12, y: y + 16, "font-size": 12, fill: MUTED
        }, label));
        var acc = isNum(g.accuracy) ? Math.max(0, Math.min(1, g.accuracy)) : null;
        svg.appendChild(svgEl("rect", {
          x: plotX, y: y + 4, width: plotW, height: 14,
          fill: TRACK, rx: 2
        }));
        if (acc !== null) {
          svg.appendChild(svgEl("rect", {
            x: plotX, y: y + 4, width: Math.max(acc * plotW, 2), height: 14,
            fill: ACCENT, rx: 2
          }));
          svg.appendChild(svgEl("text", {
            x: plotX + plotW + 6, y: y + 16, "font-size": 12, fill: INK
          }, pct(g.accuracy)));
        } else {
          svg.appendChild(svgEl("text", {
            x: plotX + plotW + 6, y: y + 16, "font-size": 12, fill: MUTED
          }, "n/a"));
        }
        y += rowH;
      });
      y += blockGap;
    });

    box.appendChild(svg);
    return true;
  }

  function renderBreakdownTable(wrapId, runs, key, firstColLabel) {
    var wrap = $(wrapId);
    while (wrap.firstChild) wrap.removeChild(wrap.firstChild);
    var names = breakdownGroups(runs, key);
    if (!runs.length || !names.length) {
      wrap.appendChild(el("p", { "class": "small" }, "Breakdown data unavailable."));
      return;
    }
    var table = el("table", null);
    var cap = el("caption", null,
      "Exact " + firstColLabel.toLowerCase() + " accuracy: correct / total (percent).");
    table.appendChild(cap);
    var thead = el("thead", null);
    var hr = el("tr", null);
    hr.appendChild(el("th", { scope: "col" }, firstColLabel));
    runs.forEach(function (r) {
      hr.appendChild(el("th", { scope: "col" }, shortName(r)));
    });
    thead.appendChild(hr);
    table.appendChild(thead);
    var tbody = el("tbody", null);
    names.forEach(function (n) {
      var tr = el("tr", null);
      // row header includes n when consistent reporters exist
      var n0 = null;
      runs.forEach(function (r) {
        var g = (Array.isArray(r[key]) ? r[key] : []).filter(function (x) {
          return x && x.name === n;
        })[0];
        if (g && isNum(g.n) && n0 === null) n0 = g.n;
      });
      tr.appendChild(el("th", { scope: "row" }, n + (n0 !== null ? " (n=" + n0 + ")" : "")));
      runs.forEach(function (r) {
        var g = (Array.isArray(r[key]) ? r[key] : []).filter(function (x) {
          return x && x.name === n;
        })[0];
        var cell = (!g || !isNum(g.correct) || !isNum(g.n))
          ? "n/a"
          : g.correct + " / " + g.n + " (" + pct(g.accuracy) + ")";
        tr.appendChild(el("td", { "class": "num" }, cell));
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
  }

  /* ---------------- ablations ---------------- */

  function renderAblations(primary, ablations) {
    var body = $("ablation-body");
    while (body.firstChild) body.removeChild(body.firstChild);
    if (!ablations.length) {
      body.appendChild(el("p", null, "No reasoning ablations are present in the current data."));
      return;
    }
    ablations.forEach(function (ab) {
      var base = null;
      if (typeof ab.model === "string") {
        for (var i = 0; i < primary.length; i++) {
          if (primary[i].model === ab.model) { base = primary[i]; break; }
        }
      }
      var panel = el("div", { "class": "ablation-pair" });
      panel.appendChild(el("h3", null, shortName(ab)));
      if (base && isNum(base.accuracy) && isNum(ab.accuracy)) {
        var delta = (ab.accuracy - base.accuracy) * 100;
        var sign = delta > 0 ? "+" : "";
        var p = el("p", { "class": "delta" },
          pct(base.accuracy) + " → " + pct(ab.accuracy) +
          "  (" + sign + delta.toFixed(1) + " points)");
        panel.appendChild(p);
        panel.appendChild(el("p", null,
          "Compared with the provider-default run of the same model (" +
          shortName(base) + ", " + pct(base.accuracy) + "), disabling reasoning " +
          (delta <= 0 ? "lowered" : "raised") + " accuracy by " +
          Math.abs(delta).toFixed(1) + " points on the same 700 items. " +
          "This is a configuration experiment, not a model rank."));
        var latB = (base.latency_ms || {}).median;
        var latA = (ab.latency_ms || {}).median;
        var invB = (base.invalid || {}).count;
        var invA = (ab.invalid || {}).count;
        var bits = [];
        if (isNum(latB) && isNum(latA)) {
          bits.push("median latency " + fmtMs(latB) + " → " + fmtMs(latA));
        }
        if (isNum(invB) && isNum(invA) && isNum(base.total)) {
          bits.push("invalid outputs " + invB + " → " + invA + " of " + base.total);
        }
        if (bits.length) {
          panel.appendChild(el("p", { "class": "ablation-note" },
            "Side effects of the setting change: " + bits.join("; ") + "."));
        }
      } else {
        panel.appendChild(el("p", null,
          "Accuracy: " + pct(ab.accuracy) + ". No matching provider-default run " +
          "for this model is present, so no paired comparison is shown."));
      }
      var ev = ab.evidence || {};
      var evP = el("p", { "class": "evidence small" });
      var snap = evidenceHref(ev.snapshot);
      var res = evidenceHref(ev.results);
      if (snap) evP.appendChild(el("a", { href: snap }, "Config snapshot"));
      if (res) evP.appendChild(el("a", { href: res }, "Results JSON"));
      if (snap || res) panel.appendChild(evP);
      body.appendChild(panel);
    });
  }

  /* ---------------- reliability ---------------- */

  function renderReliability(allRuns) {
    var wrap = $("reliability-table-wrap");
    while (wrap.firstChild) wrap.removeChild(wrap.firstChild);
    if (!allRuns.length) {
      wrap.appendChild(el("p", { "class": "small" }, "Reliability data unavailable."));
      return;
    }
    var table = el("table", null);
    table.appendChild(el("caption", null,
      "Invalid outputs and latency per run. Latency reflects the endpoint used, not the model itself."));
    var thead = el("thead", null);
    var hr = el("tr", null);
    ["Run", "Invalid", "Empty outputs", "Median latency", "p95 latency"].forEach(function (h, i) {
      hr.appendChild(el("th", i === 0 ? { scope: "col" } : { scope: "col", "class": "num" }, h));
    });
    thead.appendChild(hr);
    table.appendChild(thead);
    var tbody = el("tbody", null);
    allRuns.forEach(function (r) {
      var tr = el("tr", null);
      var label = shortName(r) + (r.category === "ablation" ? " (ablation)" : "");
      tr.appendChild(el("th", { scope: "row" }, label));
      var inv = r.invalid || {};
      tr.appendChild(el("td", { "class": "num" },
        isNum(inv.count) && isNum(r.total)
          ? inv.count + " / " + r.total + " (" + pct(isNum(inv.rate) ? inv.rate : inv.count / r.total) + ")"
          : "not reported"));
      var empty = r.empty_raw_output;
      tr.appendChild(el("td", { "class": "num" },
        (typeof empty === "number" && isNum(r.total))
          ? empty + " / " + r.total : "not reported"));
      var lat = r.latency_ms || {};
      tr.appendChild(el("td", { "class": "num" }, fmtMs(lat.median)));
      tr.appendChild(el("td", { "class": "num" }, fmtMs(lat.p95)));
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
  }

  /* ---------------- skipped ---------------- */

  function renderSkipped(skipped) {
    var body = $("skipped-body");
    while (body.firstChild) body.removeChild(body.firstChild);
    var summary = $("skipped-summary");
    if (!skipped || !skipped.length) {
      summary.textContent = "Skipped or incomplete runs (0)";
      body.appendChild(el("p", { "class": "small" }, "No runs were skipped."));
      return;
    }
    summary.textContent = "Skipped or incomplete runs (" + skipped.length + ")";
    var ul = el("ul", null);
    skipped.forEach(function (s) {
      var slug = (s && typeof s.slug === "string") ? s.slug : "unknown run";
      var reason = (s && typeof s.reason === "string") ? s.reason : "reason not recorded";
      ul.appendChild(el("li", null,
        slug + " — " + reason + ". Excluded from all results and charts."));
    });
    body.appendChild(ul);
  }

  /* ---------------- header / footer meta ---------------- */

  function renderMeta(payload) {
    var runs = Array.isArray(payload.runs) ? payload.runs : [];
    var stamps = runs
      .map(function (r) { return typeof r.timestamp === "string" ? r.timestamp : null; })
      .filter(Boolean)
      .sort();
    var meta = $("report-meta");
    while (meta.firstChild) meta.removeChild(meta.firstChild);
    var nPrimary = runs.filter(function (r) { return r.category !== "ablation"; }).length;
    var nAbl = runs.length - nPrimary;
    var itemCount = payload.item_count;
    var parts = [];
    if (stamps.length) {
      var first = fmtDate(stamps[0]);
      var last = fmtDate(stamps[stamps.length - 1]);
      parts.push(first === last || !last ? first : first + " – " + last);
    }
    parts.push(isNum(itemCount) ? itemCount + " items per run" : "item count not reported");
    parts.push(runs.length + " complete runs (" + nPrimary + " primary, " + nAbl + " ablation" + (nAbl === 1 ? "" : "s") + ")");
    meta.textContent = "Evaluation scope: " + parts.join(" · ") + ".";
    var foot = $("footer-line");
    var gen = typeof payload.generated_at === "string" ? fmtDate(payload.generated_at) : null;
    foot.textContent = "KoBALT-700 research report." +
      (gen ? " Data generated " + gen + " (UTC)" : "") +
      " from run directories; see evidence links per run.";
  }

  /* ---------------- main ---------------- */

  function fail(message) {
    setStatus(message, true);
    chartError("overall-chart", "Overall chart unavailable: " + message);
    chartError("domain-chart", "Domain chart unavailable: " + message);
    chartError("level-chart", "Difficulty chart unavailable: " + message);
    var cards = $("run-cards");
    while (cards.firstChild) cards.removeChild(cards.firstChild);
    cards.appendChild(el("p", { "class": "small" }, "Results could not be loaded. " + message));
    renderSkipped([]);
  }

  function init() {
    fetch("results.json", { cache: "no-store" })
      .then(function (resp) {
        if (!resp.ok) throw new Error("results.json returned HTTP " + resp.status);
        return resp.json();
      })
      .then(function (payload) {
        if (!payload || typeof payload !== "object" || !Array.isArray(payload.runs)) {
          fail("results file is missing the runs list.");
          return;
        }
        var runs = payload.runs;
        if (!runs.length) {
          fail("no completed runs found in the results file.");
          return;
        }
        var primary = runs.filter(function (r) { return r && r.category !== "ablation"; });
        var ablations = runs.filter(function (r) { return r && r.category === "ablation"; });

        renderMeta(payload);
        renderOverallChart(primary);
        renderCards(primary);
        var okD = renderBreakdownChart("domain-chart", primary, "by_domain", "domain");
        renderBreakdownTable("domain-table-wrap", primary, "by_domain", "Domain");
        var okL = renderBreakdownChart("level-chart", primary, "by_level", "difficulty level");
        var levelNames = breakdownGroups(primary, "by_level");
        renderBreakdownTable("level-table-wrap", primary, "by_level", "Level");
        renderAblations(primary, ablations);
        renderReliability(primary.concat(ablations));
        renderSkipped(payload.skipped);

        var notes = [];
        if (!okD) notes.push("domain chart unavailable");
        if (!okL) notes.push("difficulty chart unavailable");
        if (!levelNames.length) notes.push("difficulty data missing");
        setStatus("Loaded " + primary.length + " primary run" +
          (primary.length === 1 ? "" : "s") + " and " + ablations.length +
          " ablation" + (ablations.length === 1 ? "" : "s") + "." +
          (notes.length ? " Note: " + notes.join("; ") + "." : ""));
      })
      .catch(function (err) {
        fail(err && err.message ? err.message : "could not load results.json.");
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
