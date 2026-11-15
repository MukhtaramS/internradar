(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var PAGE = 60;
  var FEED_CITIES = ["London", "Zurich", "Amsterdam", "Dublin", "Paris", "Munich", "Berlin"];
  var DOMAINS = {
    "Google": "google.com", "Meta": "meta.com", "Apple": "apple.com", "Amazon": "amazon.com",
    "Microsoft": "microsoft.com", "Netflix": "netflix.com", "NVIDIA": "nvidia.com",
    "OpenAI": "openai.com", "Anthropic": "anthropic.com", "Stripe": "stripe.com",
    "Databricks": "databricks.com", "Palantir": "palantir.com", "Uber": "uber.com",
    "Airbnb": "airbnb.com", "Snowflake": "snowflake.com", "Datadog": "datadoghq.com",
    "Cloudflare": "cloudflare.com", "Figma": "figma.com", "Coinbase": "coinbase.com",
    "Bloomberg": "bloomberg.com", "Spotify": "spotify.com", "Waymo": "waymo.com",
    "Scale AI": "scale.com", "Perplexity AI": "perplexity.ai", "TikTok": "tiktok.com",
    "Tesla": "tesla.com", "Jane Street": "janestreet.com", "Citadel": "citadel.com",
    "Citadel Securities": "citadelsecurities.com", "Hudson River Trading": "hudsonrivertrading.com",
    "Jump Trading": "jumptrading.com", "Optiver": "optiver.com", "IMC": "imc.com", "SIG": "sig.com",
    "Two Sigma": "twosigma.com", "D. E. Shaw": "deshaw.com", "DRW": "drw.com",
    "XTX Markets": "xtxmarkets.com", "G-Research": "gresearch.com",
    "Tower Research Capital": "tower-research.com", "Squarepoint Capital": "squarepoint-capital.com",
    "Millennium": "mlp.com", "Qube Research & Technologies": "qube-rt.com", "Marshall Wace": "mwam.com",
    "GSA Capital": "gsacapital.com", "Maven Securities": "mavensecurities.com",
    "Da Vinci": "davincitrading.com", "Flow Traders": "flowtraders.com", "Adyen": "adyen.com",
    "Monzo": "monzo.com", "Helsing": "helsing.ai", "N26": "n26.com", "DeepL": "deepl.com",
    "ElevenLabs": "elevenlabs.io", "Mistral AI": "mistral.ai", "Wise": "wise.com",
    "Booking.com": "booking.com", "Klarna": "klarna.com", "Revolut": "revolut.com"
  };
  var ROLE_ORDER = ["Software", "Infrastructure", "AI/ML", "Data", "Quant Research", "Quant Trading",
                    "Security", "Hardware", "Mobile", "Frontend", "QA/Test"];
  var DEGREES = [["BS", "Bachelor's"], ["MS", "Master's"], ["PhD", "PhD"]];
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var GROUPS = ["cat", "country", "city", "role", "degree", "kind", "company"];
  var PIN = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>';

  var data = null, jobs = [], shown = PAGE, updatedAt = null, todayTs = 0, seedTs = 0;
  var state = freshState();
  /* My jobs: saved[url] = { t: added, s: status, st: status changed, title, company, category, where, posted }.
     The job details are kept so an application stays listed after the posting closes.
     Older versions stored only a timestamp per url. */
  var STATUSES = [["saved", "Saved"], ["applied", "Applied"], ["oa", "Online assessment"],
                  ["interview", "Interview"], ["offer", "Offer"], ["rejected", "Rejected"]];
  var STATUS_LABEL = {};
  STATUSES.forEach(function (x) { STATUS_LABEL[x[0]] = x[1]; });
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem("saved-jobs") || "{}") || {}; } catch (e) { saved = {}; }
  Object.keys(saved).forEach(function (u) {
    if (typeof saved[u] === "number") saved[u] = { t: saved[u], s: "saved", st: saved[u] };
    if (!saved[u] || typeof saved[u] !== "object") delete saved[u];
    else if (!STATUS_LABEL[saved[u].s]) saved[u].s = "saved";
  });

  function freshState() {
    var s = { view: "jobs", q: "", age: "", savedOnly: false, hideApplied: false, newOnly: false, sort: "posted" };
    GROUPS.forEach(function (g) { s[g] = {}; });
    return s;
  }

  /* ---------------- helpers ---------------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function keys(o) { return Object.keys(o); }
  function initials(name) {
    var w = name.replace(/[^A-Za-z0-9 ]/g, "").split(/\s+/).filter(Boolean);
    return (w.length > 1 ? w[0][0] + w[1][0] : (w[0] || "?").slice(0, 2)).toUpperCase();
  }
  function logo(name) {
    var d = DOMAINS[name];
    var img = d ? '<img src="https://www.google.com/s2/favicons?domain=' + esc(d) + '&sz=64" alt="" loading="lazy" onerror="this.remove()" onload="this.parentNode.firstChild.textContent=\'\'">' : "";
    return '<span class="logo">' + esc(initials(name)) + img + "</span>";
  }
  function flag(code) { return (data.countries[code] || {}).flag || ""; }
  function cname(code) { return (data.countries[code] || {}).name || code; }
  function catLabel(c) { return data.categories[c] || c; }
  function day(iso) { return iso ? new Date(iso + "T00:00:00Z").getTime() : 0; }
  function ago(iso) {
    if (!iso) return "";
    var d = Math.floor((updatedAt - day(iso)) / 864e5);
    if (d <= 0) return "today";
    if (d === 1) return "yesterday";
    if (d < 30) return d + " days ago";
    var m = Math.round(d / 30);
    return m + (m === 1 ? " month ago" : " months ago");
  }
  function where(j) {
    var flags = j.countries.map(flag).join(" ");
    if (j.cities.length) return flags + " " + j.cities.join(", ");
    if (j.countries.length) return j.countries.map(function (c) { return flag(c) + " " + cname(c); }).join(", ");
    return "🇪🇺 Europe-wide";
  }
  function persistSaved() { try { localStorage.setItem("saved-jobs", JSON.stringify(saved)); } catch (e) {} }
  function applied(url) { return !!saved[url] && saved[url].s !== "saved"; }
  function plainWhere(j) {
    if (j.cities.length) return j.cities.join(", ") + (j.countries.length === 1 ? ", " + cname(j.countries[0]) : "");
    if (j.countries.length) return j.countries.map(cname).join(", ");
    return "Europe";
  }
  function snapshot(j) {
    return { title: j.title, company: j.company, category: j.category, where: where(j), plain: plainWhere(j), posted: j.posted, code: j.code };
  }

  /* ---------------- URL hash <-> state ---------------- */
  function readHash() {
    var s = freshState();
    var p = new URLSearchParams(location.hash.replace(/^#/, ""));
    if (p.get("view")) s.view = p.get("view");
    s.q = p.get("q") || "";
    s.age = p.get("age") || "";
    s.sort = p.get("sort") || "posted";
    s.newOnly = p.get("new") === "1";
    s.hideApplied = p.get("hide") === "1";
    GROUPS.forEach(function (g) {
      (p.get(g) || "").split("|").filter(Boolean).forEach(function (v) { s[g][v] = true; });
    });
    state = s;
  }
  function writeHash() {
    var p = new URLSearchParams();
    if (state.view !== "jobs") p.set("view", state.view);
    if (state.q) p.set("q", state.q);
    if (state.age) p.set("age", state.age);
    if (state.sort !== "posted") p.set("sort", state.sort);
    if (state.newOnly) p.set("new", "1");
    if (state.hideApplied) p.set("hide", "1");
    GROUPS.forEach(function (g) { if (keys(state[g]).length) p.set(g, keys(state[g]).join("|")); });
    var h = p.toString();
    history.replaceState(null, "", h ? "#" + h : location.pathname + location.search);
  }

  /* ---------------- filtering ---------------- */
  function values(j, g) {
    switch (g) {
      case "cat": return [j.category];
      case "country": return j.countries.length ? j.countries : ["EU"];
      case "city": return j.cities;
      case "role": return [j.role];
      case "degree": return j.degrees;
      case "kind": return [j.kind];
      case "company": return [j.company];
    }
    return [];
  }
  function passes(j, skip) {
    for (var i = 0; i < GROUPS.length; i++) {
      var g = GROUPS[i], want = keys(state[g]);
      if (g === skip || !want.length) continue;
      var have = values(j, g);
      if (g === "degree" && !have.length) continue; // no degree named = open to all
      if (!have.some(function (v) { return state[g][v]; })) return false;
    }
    if (state.q && j.search.indexOf(state.q) === -1) return false;
    if (state.age && skip !== "age" && !ageOk(j, state.age)) return false;
    if (state.savedOnly && !saved[j.url]) return false;
    if (state.hideApplied && applied(j.url)) return false;
    if (state.newOnly && !j.isNew) return false;
    return true;
  }
  /* Date posted, like LinkedIn. Sites give dates without times, so whole days are compared:
     "Past 24 hours" = posted today or yesterday. A job with no posting date uses the day we
     first found it, except jobs from the very first scrape, whose real age is unknown. */
  var AGE_LABEL = { "": "Any time", "1": "Past 24 hours", "3": "Past 3 days", "7": "Past week", "30": "Past month" };
  var AGE_ORDER = ["", "1", "3", "7", "30"]; // object key order would put "" last
  function ageOk(j, age) {
    return !age || (j.ageTs > 0 && j.ageTs >= todayTs - Number(age) * 864e5);
  }
  function renderAge() {
    var base = jobs.filter(function (j) { return passes(j, "age"); });
    AGE_ORDER.forEach(function (v) {
      var em = document.querySelector('#f-age em[data-age="' + v + '"]');
      if (em) em.textContent = base.filter(function (j) { return ageOk(j, v); }).length;
    });
  }
  function facetCounts(g) {
    var c = {};
    jobs.forEach(function (j) {
      if (!passes(j, g)) return;
      values(j, g).forEach(function (v) { c[v] = (c[v] || 0) + 1; });
    });
    return c;
  }

  /* ---------------- sidebar ---------------- */
  function option(group, value, label, count, dotColor) {
    var checked = state[group][value] ? " checked" : "";
    var dot = dotColor ? '<i class="dot" style="background:var(' + dotColor + ')"></i>' : "";
    return '<label class="opt"><input type="checkbox" data-g="' + group + '" value="' + esc(value) + '"' +
      checked + ">" + dot + "<span>" + label + "</span><em>" + (count || 0) + "</em></label>";
  }
  /* Long groups show their top SHOW options plus "See all". Ticked options always stay visible. */
  var SHOW = 5;
  var expanded = {};
  function byCount(c) { return function (a, b) { return c[b] - c[a] || (a < b ? -1 : 1); }; }
  function fill(group, items, showEverything) {
    var long = !showEverything && items.length > SHOW + 1; // never hide just one option
    var shown = !long || expanded[group] ? items :
      items.filter(function (it, i) { return i < SHOW || state[group][it[0]]; });
    var html = shown.map(function (it) { return option(group, it[0], it[1], it[2], it[3]); }).join("");
    if (long) {
      html += '<button type="button" class="see-all" data-more="' + group + '" aria-expanded="' + !!expanded[group] + '">' +
        (expanded[group] ? "Show less" : "See all (" + items.length + ")") + "</button>";
    }
    $("f-" + group).innerHTML = html;
  }
  function renderSidebar() {
    var c;
    c = facetCounts("cat");
    fill("cat", keys(data.categories).filter(function (k) {
      return c[k] || state.cat[k] || data.companies.some(function (co) { return co.category === k; });
    }).map(function (k) { return [k, esc(catLabel(k)), c[k], "--cat-" + k]; }));

    c = facetCounts("country");
    fill("country", keys(c).sort(byCount(c)).map(function (k) {
      return [k, k === "EU" ? "🇪🇺 Europe-wide / remote" : flag(k) + " " + esc(cname(k)), c[k]];
    }));

    c = facetCounts("city");
    keys(state.city).forEach(function (k) { c[k] = c[k] || 0; });
    fill("city", keys(c).sort(byCount(c)).map(function (k) { return [k, esc(k), c[k]]; }));

    c = facetCounts("role");
    fill("role", ROLE_ORDER.filter(function (r) { return c[r] || state.role[r]; })
      .sort(byCount(c)).map(function (r) { return [r, esc(r), c[r]]; }));

    c = facetCounts("degree");
    fill("degree", DEGREES.map(function (d) { return [d[0], d[1], c[d[0]]]; }));

    c = facetCounts("kind");
    fill("kind", keys(c).sort(byCount(c)).map(function (k) { return [k, esc(k), c[k]]; }));

    c = facetCounts("company");
    var find = $("co-search").value.trim().toLowerCase();
    fill("company", keys(c).sort(byCount(c))
      .filter(function (k) { return !find || k.toLowerCase().indexOf(find) !== -1 || state.company[k]; })
      .map(function (k) { return [k, esc(k), c[k]]; }), !!find);

    var open = jobs.filter(function (j) { return saved[j.url]; });
    $("n-saved").textContent = open.length;
    $("n-applied").textContent = open.filter(function (j) { return applied(j.url); }).length;
    $("f-saved").checked = state.savedOnly;
    $("f-hide").checked = state.hideApplied;
    Array.prototype.forEach.call(document.querySelectorAll('input[name="age"]'), function (r) {
      r.checked = r.value === state.age;
    });
    var n = GROUPS.reduce(function (a, g) { return a + keys(state[g]).length; }, 0) +
      (state.age ? 1 : 0) + (state.savedOnly ? 1 : 0) + (state.hideApplied ? 1 : 0) + (state.newOnly ? 1 : 0);
    $("fcount").hidden = !n;
    $("fcount").textContent = n;
  }

  /* ---------------- presets ---------------- */
  var PRESETS = [
    { label: "🇨🇭 Switzerland", group: "country", value: "CH" },
    { label: "🇬🇧 London", group: "city", value: "London" },
    { label: "Quant & Trading", group: "cat", value: "quant" },
    { label: "FAANG", group: "cat", value: "faang" },
    { label: "FAANG+", group: "cat", value: "faang_plus" },
    { label: "AI / ML", group: "role", value: "AI/ML" },
    { label: "🇩🇪 Germany", group: "country", value: "DE" },
    { label: "🇳🇱 Netherlands", group: "country", value: "NL" },
    { label: "🇮🇪 Ireland", group: "country", value: "IE" },
    { label: "🆕 New this week", group: "new" }
  ];
  function presetCount(p) {
    if (p.group === "new") return jobs.filter(function (j) { return j.isNew; }).length;
    return jobs.filter(function (j) { return values(j, p.group).indexOf(p.value) !== -1; }).length;
  }
  function presetOn(p) {
    if (p.group === "new") return state.newOnly;
    var k = keys(state[p.group]);
    return k.length === 1 && k[0] === p.value;
  }
  function renderPresets() {
    $("presets").innerHTML = PRESETS.map(function (p, i) {
      var n = presetCount(p);
      if (!n && !presetOn(p)) return "";
      return '<button type="button" class="preset' + (presetOn(p) ? " on" : "") + '" data-i="' + i + '">' +
        esc(p.label) + " <em>" + n + "</em></button>";
    }).join("");
  }

  /* ---------------- list ---------------- */
  function sorted(rows) {
    var by = state.sort;
    return rows.sort(function (a, b) {
      if (by === "company") return a.company < b.company ? -1 : a.company > b.company ? 1 : b.ageTs - a.ageTs;
      if (by === "added") return b.foundTs - a.foundTs || b.ageTs - a.ageTs;
      return b.ageTs - a.ageTs;
    });
  }
  function card(j) {
    var tags = ['<span class="tag">' + esc(j.role) + "</span>"];
    if (j.isNew) tags.unshift('<span class="tag new">New</span>');
    if (applied(j.url)) tags.unshift('<span class="tag st st-' + saved[j.url].s + '">' + esc(STATUS_LABEL[saved[j.url].s]) + "</span>");
    if (j.kind !== "Internship") tags.push('<span class="tag">' + esc(j.kind) + "</span>");
    if (j.degrees.length) tags.push('<span class="tag">' + esc(j.degrees.join(" / ")) + "</span>");
    if (j.season) tags.push('<span class="tag">' + esc(j.season) + "</span>");
    var when = j.posted ? "Posted " + ago(j.posted) : j.ageTs ? "Found " + ago(j.first_seen) : "No posting date";
    return '<li class="job">' + logo(j.company) +
      '<div class="job-main"><a class="job-title" href="' + esc(j.url) + '" target="_blank" rel="noopener">' + esc(j.title) + "</a>" +
      '<div class="job-co"><b>' + esc(j.company) + '</b><span class="cat cat-' + esc(j.category) + '">' + esc(catLabel(j.category)) +
      '</span><span class="place">' + PIN + esc(where(j)) + "</span></div>" +
      '<div class="job-meta">' + tags.join("") + "</div></div>" +
      '<div class="job-side"><div class="side-row"><a class="apply" href="' + esc(j.url) + '" target="_blank" rel="noopener">Apply</a>' +
      '<button type="button" class="save' + (saved[j.url] ? " on" : "") + '" data-url="' + esc(j.url) +
      '" title="' + (saved[j.url] ? "Remove from My jobs" : "Add to My jobs") + '" aria-label="' + (saved[j.url] ? "Remove from My jobs" : "Add to My jobs") +
      '" aria-pressed="' + !!saved[j.url] + '">' + (saved[j.url] ? "★" : "☆") + "</button></div>" +
      '<span class="when">' + (j.code ? '<b class="code" title="Reply &quot;submit ' + esc(j.code) + '&quot; to your applier bot">' + esc(j.code) + "</b> · " : "") + esc(when) + "</span></div></li>";
  }
  function renderChips() {
    var chips = [];
    GROUPS.forEach(function (g) {
      keys(state[g]).forEach(function (v) {
        var label = g === "cat" ? catLabel(v) : g === "country" ? (v === "EU" ? "Europe-wide" : flag(v) + " " + cname(v)) : v;
        chips.push('<button type="button" class="chip" data-g="' + g + '" data-v="' + esc(v) + '">' + esc(label) + "</button>");
      });
    });
    if (state.age) chips.push('<button type="button" class="chip" data-g="age">' + esc(AGE_LABEL[state.age] || "") + "</button>");
    if (state.newOnly) chips.push('<button type="button" class="chip" data-g="new">New this week</button>');
    if (state.savedOnly) chips.push('<button type="button" class="chip" data-g="saved">My jobs</button>');
    if (state.hideApplied) chips.push('<button type="button" class="chip" data-g="hide">Hiding applied</button>');
    if (state.q) chips.push('<button type="button" class="chip" data-g="q">“' + esc(state.q) + "”</button>");
    $("chips").innerHTML = chips.join("");
  }
  function renderList() {
    var rows = sorted(jobs.filter(function (j) { return passes(j); }));
    $("count").textContent = rows.length + (rows.length === 1 ? " internship" : " internships");
    $("list").innerHTML = rows.length ? rows.slice(0, shown).map(card).join("") :
      '<li class="empty">Nothing matches these filters right now. Try removing one, or set up an alert so you hear when something appears.</li>';
    $("more").hidden = rows.length <= shown;
    $("more").textContent = "Show more (" + (rows.length - shown) + " left)";
  }
  function refresh(keepPage) {
    if (!keepPage) shown = PAGE;
    writeHash();
    renderPresets();
    renderSidebar();
    renderAge();
    renderChips();
    renderList();
    renderMine();
  }

  /* ---------------- companies view ---------------- */
  var coCat = "";
  function renderCompanies() {
    var cats = keys(data.categories).filter(function (k) {
      return data.companies.some(function (co) { return co.category === k; });
    });
    $("co-cats").innerHTML = ['<button type="button" class="preset' + (coCat ? "" : " on") + '" data-cat="">All</button>']
      .concat(cats.map(function (k) {
        return '<button type="button" class="preset' + (coCat === k ? " on" : "") + '" data-cat="' + k + '">' + esc(catLabel(k)) + "</button>";
      })).join("");
    var label = { ok: "● Live", failed: "● Temporarily failing", not_covered: "○ Coming soon" };
    $("co-body").innerHTML = data.companies.filter(function (c) { return !coCat || c.category === coCat; })
      .sort(function (a, b) { return b.open - a.open || (a.name < b.name ? -1 : 1); })
      .map(function (c) {
        return "<tr><td><span class=\"co-name\">" + logo(c.name) + esc(c.name) + "</span></td>" +
          '<td><span class="cat cat-' + esc(c.category) + '">' + esc(catLabel(c.category)) + "</span></td>" +
          '<td class="hubs">' + esc((c.hubs || []).join(", ")) + "</td>" +
          '<td class="n">' + (c.open ? '<a href="#company=' + encodeURIComponent(c.name) + '" data-co="' + esc(c.name) + '">' + c.open + "</a>" : "0") + "</td>" +
          '<td class="n">' + (c.ever || 0) + "</td>" +
          '<td class="n">' + (c.median_days_open != null ? Math.round(c.median_days_open) : "–") + "</td>" +
          "<td>" + (c.busiest_month ? MONTHS[Number(c.busiest_month) - 1] : "–") + "</td>" +
          '<td><span class="status ' + esc(c.status) + '">' + (label[c.status] || esc(c.status)) + "</span></td></tr>";
      }).join("");
  }

  /* ---------------- My jobs view ---------------- */
  var mineFilter = "";
  var byUrl = {};
  function mineRows() {
    return keys(saved).map(function (u) {
      var live = byUrl[u];
      var info = live ? snapshot(live) : saved[u];
      return { url: u, rec: saved[u], info: info, live: !!live };
    }).sort(function (a, b) { return (b.rec.st || b.rec.t) - (a.rec.st || a.rec.t); });
  }
  function since(ts) {
    if (!ts) return "";
    var d = Math.floor((Date.now() - ts) / 864e5);
    return d <= 0 ? "today" : d === 1 ? "yesterday" : d < 30 ? d + " days ago" : Math.round(d / 30) + " mo ago";
  }
  function renderMine() {
    var rows = mineRows();
    var counts = {};
    rows.forEach(function (r) { counts[r.rec.s] = (counts[r.rec.s] || 0) + 1; });
    $("mine-count").hidden = !rows.length;
    $("mine-count").textContent = rows.length;
    if (mineFilter && !counts[mineFilter]) mineFilter = "";
    $("mine-filters").innerHTML = ['<button type="button" class="preset' + (mineFilter ? "" : " on") + '" data-st="">All <em>' + rows.length + "</em></button>"]
      .concat(STATUSES.filter(function (x) { return counts[x[0]]; }).map(function (x) {
        return '<button type="button" class="preset' + (mineFilter === x[0] ? " on" : "") + '" data-st="' + x[0] + '">' + esc(x[1]) + " <em>" + counts[x[0]] + "</em></button>";
      })).join("");
    var toApply = rows.filter(function (r) { return r.rec.s === "saved" && r.live; }).length;
    $("export-jobs").disabled = !rows.length;
    $("copy-links").disabled = !toApply;
    $("export-jobs").title = toApply + " to apply to, the rest marked done";
    var shownRows = rows.filter(function (r) { return !mineFilter || r.rec.s === mineFilter; });
    if (!rows.length) {
      $("mine-list").innerHTML = '<li class="empty">Nothing here yet. Star ☆ a listing on the Internships tab to add it.</li>';
      return;
    }
    $("mine-list").innerHTML = shownRows.map(function (r) {
      var i = r.info;
      var select = '<select class="st-select st-' + r.rec.s + '" data-url="' + esc(r.url) + '" aria-label="Status">' +
        STATUSES.map(function (x) {
          return '<option value="' + x[0] + '"' + (x[0] === r.rec.s ? " selected" : "") + ">" + esc(x[1]) + "</option>";
        }).join("") + "</select>";
      var note = (i.code ? i.code + " · " : "") + (r.rec.s === "saved" ? "Saved " : STATUS_LABEL[r.rec.s] + " · ") + since(r.rec.st || r.rec.t);
      return '<li class="mine-row">' + logo(i.company || "?") +
        '<div class="job-main"><a class="job-title" href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(i.title || r.url) + "</a>" +
        '<div class="job-co"><b>' + esc(i.company || "") + "</b>" +
        (i.category ? '<span class="cat cat-' + esc(i.category) + '">' + esc(catLabel(i.category)) + "</span>" : "") +
        (i.where ? '<span class="place">' + PIN + esc(i.where) + "</span>" : "") +
        (r.live ? "" : '<span class="tag closed">Listing closed</span>') + "</div></div>" +
        '<div class="mine-side">' + select + '<span class="when">' + esc(note) + "</span></div>" +
        '<button type="button" class="remove" data-url="' + esc(r.url) + '" title="Remove from My jobs" aria-label="Remove">×</button></li>';
    }).join("");
  }
  function setStatus(url, s) {
    if (!saved[url]) return;
    saved[url].s = s;
    saved[url].st = Date.now();
    persistSaved();
  }
  function removeSaved(url) {
    if (!saved[url]) return true;
    var r = saved[url];
    if (r.s !== "saved" && !confirm("Remove " + (r.title || "this job") + " from My jobs? Its status (" + STATUS_LABEL[r.s] + ") will be lost.")) return false;
    delete saved[url];
    persistSaved();
    return true;
  }
  function addSaved(j) {
    var now = Date.now();
    saved[j.url] = Object.assign({ t: now, s: "saved", st: now }, snapshot(j));
    persistSaved();
  }
  /* jobs.txt in the format AutoInternship's skill reads: one link per line, a note after "#"
     starting with the company, and finished links below a "# done" line. */
  function clean(s) { return String(s || "").replace(/[#|\n\r]+/g, " ").replace(/\s+/g, " ").trim(); }
  function exportText() {
    var rows = mineRows();
    var line = function (r, extra) {
      var i = r.info;
      return r.url + "  # " + [clean(i.company), clean(i.title), clean(i.plain || "")].concat(extra).filter(Boolean).join(" | ");
    };
    var todo = rows.filter(function (r) { return r.rec.s === "saved" && r.live; })
      .sort(function (a, b) { return (b.info.posted || "") < (a.info.posted || "") ? -1 : 1; })
      .map(function (r) { return line(r, [r.info.posted ? "posted " + r.info.posted : "", "fame 1"]); });
    var done = rows.filter(function (r) { return r.rec.s !== "saved"; })
      .map(function (r) { return line(r, [STATUS_LABEL[r.rec.s].toLowerCase() + " " + new Date(r.rec.st || r.rec.t).toISOString().slice(0, 10)]); });
    var closed = rows.filter(function (r) { return r.rec.s === "saved" && !r.live; })
      .map(function (r) { return line(r, ["listing closed"]); });
    return ["# InternRadar export, " + new Date().toISOString().slice(0, 10),
            '# Jobs to apply to come first. Ones you applied to, and closed listings, are below "# done".',
            ""].concat(todo, ["", "# done"], done, closed).join("\n") + "\n";
  }
  function download(name, text) {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }
  function flash(btn, text) {
    var old = btn.getAttribute("data-label") || btn.textContent;
    btn.setAttribute("data-label", old);
    btn.textContent = text;
    setTimeout(function () { btn.textContent = old; }, 1600);
  }

  /* ---------------- alerts view ---------------- */
  function renderAlerts(cfg) {
    var tg = (cfg.telegram || []).filter(function (t) { return t.url; });
    $("tg-list").innerHTML = tg.map(function (t) {
      return '<li><a href="' + esc(t.url) + '" target="_blank" rel="noopener">' + esc(t.label) + "</a></li>";
    }).join("");
    $("tg-empty").hidden = tg.length > 0;

    var feeds = [["all", "Everything"]];
    keys(data.categories).forEach(function (k) {
      if (data.companies.some(function (co) { return co.category === k; })) feeds.push([k.replace(/_/g, "-"), catLabel(k)]);
    });
    var countries = {};
    jobs.forEach(function (j) { j.countries.forEach(function (c) { countries[c] = true; }); });
    keys(countries).sort(function (a, b) { return cname(a) < cname(b) ? -1 : 1; })
      .forEach(function (c) { feeds.push(["country-" + c.toLowerCase(), flag(c) + " " + cname(c)]); });
    FEED_CITIES.forEach(function (c) { feeds.push(["city-" + c.toLowerCase(), "📍 " + c]); });
    $("feed-list").innerHTML = feeds.map(function (f) {
      return '<li><a href="feeds/' + f[0] + '.xml">' + esc(f[1]) + "</a></li>";
    }).join("");

    if (cfg.repo) { $("repo-link").href = cfg.repo; $("repo-link").hidden = false; }
  }

  /* ---------------- views ---------------- */
  function showView(v) {
    state.view = ["jobs", "companies", "mine", "alerts"].indexOf(v) === -1 ? "jobs" : v;
    ["jobs", "companies", "mine", "alerts"].forEach(function (name) {
      $("view-" + name).hidden = name !== state.view;
      $("tab-" + name).classList.toggle("active", name === state.view);
    });
    writeHash();
  }

  /* ---------------- theme ---------------- */
  var theme = "auto";
  try { theme = localStorage.getItem("theme") || "auto"; } catch (e) {}
  function applyTheme() {
    if (theme === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
  }
  applyTheme();
  $("theme-btn").addEventListener("click", function () {
    var dark = theme === "dark" || (theme === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
    theme = dark ? "light" : "dark";
    try { localStorage.setItem("theme", theme); } catch (e) {}
    applyTheme();
  });

  /* ---------------- events ---------------- */
  function bind() {
    document.querySelector(".tabs").addEventListener("click", function (e) {
      var t = e.target.closest(".tab");
      if (t) showView(t.getAttribute("data-view"));
    });
    $("sidebar").addEventListener("change", function (e) {
      var t = e.target;
      var g = t.getAttribute("data-g");
      if (g) { if (t.checked) state[g][t.value] = true; else delete state[g][t.value]; }
      else if (t.name === "age") state.age = t.value;
      else if (t.id === "f-saved") state.savedOnly = t.checked;
      else if (t.id === "f-hide") state.hideApplied = t.checked;
      refresh();
    });
    $("sidebar").addEventListener("click", function (e) {
      var b = e.target.closest(".see-all");
      if (!b) return;
      var g = b.getAttribute("data-more");
      expanded[g] = !expanded[g];
      renderSidebar();
    });
    $("co-search").addEventListener("input", renderSidebar);
    $("reset").addEventListener("click", function () { var v = state.view; state = freshState(); state.view = v; $("q").value = ""; refresh(); });
    $("q").addEventListener("input", function () { state.q = this.value.trim().toLowerCase(); refresh(); });
    $("sort").addEventListener("change", function () { state.sort = this.value; refresh(); });    $("more").addEventListener("click", function () { shown += PAGE; renderList(); });
    $("presets").addEventListener("click", function (e) {
      var b = e.target.closest(".preset");
      if (!b) return;
      var p = PRESETS[Number(b.getAttribute("data-i"))];
      var on = presetOn(p);
      if (p.group === "new") state.newOnly = !on;
      else { state[p.group] = {}; if (!on) state[p.group][p.value] = true; }
      refresh();
    });
    $("chips").addEventListener("click", function (e) {
      var b = e.target.closest(".chip");
      if (!b) return;
      var g = b.getAttribute("data-g");
      if (g === "age") state.age = "";
      else if (g === "new") state.newOnly = false;
      else if (g === "saved") state.savedOnly = false;
      else if (g === "hide") state.hideApplied = false;
      else if (g === "q") { state.q = ""; $("q").value = ""; }
      else delete state[g][b.getAttribute("data-v")];
      refresh();
    });
    $("list").addEventListener("click", function (e) {
      var b = e.target.closest(".save");
      if (!b) return;
      var url = b.getAttribute("data-url");
      if (saved[url]) { if (!removeSaved(url)) return; } else addSaved(byUrl[url]);
      refresh(true);
    });
    $("mine-filters").addEventListener("click", function (e) {
      var b = e.target.closest(".preset");
      if (!b) return;
      mineFilter = b.getAttribute("data-st");
      renderMine();
    });
    $("mine-list").addEventListener("change", function (e) {
      var sel = e.target.closest(".st-select");
      if (!sel) return;
      setStatus(sel.getAttribute("data-url"), sel.value);
      refresh(true);
    });
    $("mine-list").addEventListener("click", function (e) {
      var b = e.target.closest(".remove");
      if (b && removeSaved(b.getAttribute("data-url"))) refresh(true);
    });
    $("export-jobs").addEventListener("click", function () {
      download("jobs.txt", exportText());
      flash(this, "Downloaded");
    });
    $("copy-links").addEventListener("click", function () {
      var btn = this;
      var links = mineRows().filter(function (r) { return r.rec.s === "saved" && r.live; })
        .map(function (r) { return r.url; }).join("\n");
      navigator.clipboard.writeText(links + "\n").then(function () { flash(btn, "Copied"); },
        function () { flash(btn, "Copy failed"); });
    });
    $("co-cats").addEventListener("click", function (e) {
      var b = e.target.closest(".preset");
      if (!b) return;
      coCat = b.getAttribute("data-cat");
      renderCompanies();
    });
    $("co-body").addEventListener("click", function (e) {
      var a = e.target.closest("a[data-co]");
      if (!a) return;
      e.preventDefault();
      var v = state.view; state = freshState();
      state.company[a.getAttribute("data-co")] = true;
      $("q").value = "";
      showView("jobs");
      refresh();
      window.scrollTo(0, 0);
    });
    $("filters-toggle").addEventListener("click", function () {
      var open = $("sidebar").classList.toggle("open");
      this.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && document.activeElement.tagName !== "INPUT") { e.preventDefault(); $("q").focus(); }
    });
  }

  /* ---------------- load ---------------- */
  function getJSON(url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(url + " returned HTTP " + r.status);
      return r.json();
    });
  }
  Promise.all([getJSON("data/jobs.json"), getJSON("site-config.json").catch(function () { return {}; })])
    .then(function (res) {
      data = res[0];
      updatedAt = new Date(data.updated_at).getTime();
      var weekAgo = updatedAt - 7 * 864e5;
      todayTs = day(data.updated_at.slice(0, 10));
      // the first scrape's date: jobs first seen then may be much older than that
      seedTs = Math.min.apply(null, data.jobs.map(function (j) { return day(j.first_seen); }));
      jobs = data.jobs.map(function (j) {
        j.postedTs = day(j.posted);
        j.foundTs = day(j.first_seen);
        j.ageTs = j.postedTs || (j.foundTs > seedTs ? j.foundTs : 0);
        j.isNew = j.foundTs >= weekAgo;
        j.search = [j.code || "", j.title, j.company, j.role, j.kind, j.season || "", catLabel(j.category)]
          .concat(j.cities, j.locations, j.countries.map(cname)).join(" ").toLowerCase();
        return j;
      });
      jobs.forEach(function (j) {
        byUrl[j.url] = j;
        if (saved[j.url]) Object.assign(saved[j.url], snapshot(j));
      });
      persistSaved();
      readHash();
      $("q").value = state.q;
      $("sort").value = state.sort;
      var companies = {};
      jobs.forEach(function (j) { companies[j.company] = true; });
      $("hero-line").innerHTML = "<b>" + jobs.length + " open internships</b> at " + keys(companies).length +
        " top companies across Europe. Updated " + esc(ago(data.updated_at.slice(0, 10)) === "today" ? "today" : ago(data.updated_at.slice(0, 10))) +
        " from official careers sites.";
      var live = data.companies.filter(function (c) { return c.status === "ok"; }).length;
      var mins = Math.max(0, Math.round((Date.now() - updatedAt) / 6e4));
      var since = mins < 60 ? mins + " min ago" : mins < 48 * 60 ? Math.round(mins / 60) + " h ago" : Math.round(mins / 1440) + " days ago";
      $("readout").textContent = "Scanning " + live + " careers sites · last sweep " + since;
      $("updated").textContent = "Last update: " + new Date(data.updated_at).toUTCString().replace(":00 GMT", " UTC") + ".";
      renderAlerts(res[1]);
      renderCompanies();
      bind();
      showView(state.view);
      refresh();
    })
    .catch(function (err) {
      $("list").innerHTML = '<li class="empty">Could not load the listings (' + esc(err.message) + "). Try reloading the page.</li>";
      $("hero-line").textContent = "Listings could not be loaded.";
    });
  window.addEventListener("hashchange", function () {
    if (!data) return;
    readHash(); $("q").value = state.q; $("sort").value = state.sort; showView(state.view); refresh();
  });
})();
