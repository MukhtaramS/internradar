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
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem("saved-jobs") || "{}"); } catch (e) { saved = {}; }

  function freshState() {
    var s = { view: "jobs", q: "", age: "", savedOnly: false, newOnly: false, sort: "posted" };
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

  /* ---------------- URL hash <-> state ---------------- */
  function readHash() {
    var s = freshState();
    var p = new URLSearchParams(location.hash.replace(/^#/, ""));
    if (p.get("view")) s.view = p.get("view");
    s.q = p.get("q") || "";
    s.age = p.get("age") || "";
    s.sort = p.get("sort") || "posted";
    s.newOnly = p.get("new") === "1";
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
    if (state.newOnly && !j.isNew) return false;
    return true;
  }
  /* Date posted, like LinkedIn. Sites give dates without times, so whole days are compared:
     "Past 24 hours" = posted today or yesterday. A job with no posting date uses the day we
     first found it, except jobs from the very first scrape, whose real age is unknown. */
  var AGE_LABEL = { "": "Any time", "1": "Past 24 hours", "7": "Past week", "30": "Past month" };
  var AGE_ORDER = ["", "1", "7", "30"]; // same order as the <option>s; object key order would put "" last
  function ageOk(j, age) {
    return !age || (j.ageTs > 0 && j.ageTs >= todayTs - Number(age) * 864e5);
  }
  function renderAge() {
    var base = jobs.filter(function (j) { return passes(j, "age"); });
    var sel = $("age-select");
    AGE_ORDER.forEach(function (v, i) {
      var n = base.filter(function (j) { return ageOk(j, v); }).length;
      sel.options[i].textContent = AGE_LABEL[v] + " (" + n + ")";
      var em = document.querySelector('#f-age em[data-age="' + v + '"]');
      if (em) em.textContent = n;
    });
    sel.value = state.age;
    sel.classList.toggle("active", !!state.age);
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
  function renderSidebar() {
    var c;
    c = facetCounts("cat");
    $("f-cat").innerHTML = keys(data.categories).filter(function (k) {
      return c[k] || state.cat[k] || data.companies.some(function (co) { return co.category === k; });
    }).map(function (k) {
      return option("cat", k, esc(catLabel(k)), c[k], "--cat-" + k);
    }).join("");

    c = facetCounts("country");
    $("f-country").innerHTML = keys(c).sort(function (a, b) { return c[b] - c[a]; }).map(function (k) {
      return option("country", k, k === "EU" ? "🇪🇺 Europe-wide / remote" : flag(k) + " " + esc(cname(k)), c[k]);
    }).join("");

    c = facetCounts("city");
    var cities = keys(c).sort(function (a, b) { return c[b] - c[a] || (a < b ? -1 : 1); });
    var top = cities.slice(0, 14);
    keys(state.city).forEach(function (k) { if (top.indexOf(k) === -1) top.push(k); });
    $("f-city").innerHTML = top.map(function (k) { return option("city", k, esc(k), c[k]); }).join("");

    c = facetCounts("role");
    $("f-role").innerHTML = ROLE_ORDER.filter(function (r) { return c[r] || state.role[r]; })
      .map(function (r) { return option("role", r, esc(r), c[r]); }).join("");

    c = facetCounts("degree");
    $("f-degree").innerHTML = DEGREES.map(function (d) { return option("degree", d[0], d[1], c[d[0]]); }).join("");

    c = facetCounts("kind");
    $("f-kind").innerHTML = keys(c).sort(function (a, b) { return c[b] - c[a]; })
      .map(function (k) { return option("kind", k, esc(k), c[k]); }).join("");

    c = facetCounts("company");
    var find = $("co-search").value.trim().toLowerCase();
    $("f-company").innerHTML = keys(c).sort(function (a, b) { return c[b] - c[a] || (a < b ? -1 : 1); })
      .filter(function (k) { return !find || k.toLowerCase().indexOf(find) !== -1 || state.company[k]; })
      .map(function (k) { return option("company", k, esc(k), c[k]); }).join("");

    $("n-saved").textContent = keys(saved).length;
    $("f-saved").checked = state.savedOnly;
    Array.prototype.forEach.call(document.querySelectorAll('input[name="age"]'), function (r) {
      r.checked = r.value === state.age;
    });
    var n = GROUPS.reduce(function (a, g) { return a + keys(state[g]).length; }, 0) +
      (state.age ? 1 : 0) + (state.savedOnly ? 1 : 0) + (state.newOnly ? 1 : 0);
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
      '" title="' + (saved[j.url] ? "Remove from saved" : "Save") + '" aria-label="Save">' + (saved[j.url] ? "★" : "☆") + "</button></div>" +
      '<span class="when">' + esc(when) + "</span></div></li>";
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
    if (state.savedOnly) chips.push('<button type="button" class="chip" data-g="saved">Saved</button>');
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
    state.view = ["jobs", "companies", "alerts"].indexOf(v) === -1 ? "jobs" : v;
    ["jobs", "companies", "alerts"].forEach(function (name) {
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
      refresh();
    });
    $("co-search").addEventListener("input", renderSidebar);
    $("reset").addEventListener("click", function () { var v = state.view; state = freshState(); state.view = v; $("q").value = ""; refresh(); });
    $("q").addEventListener("input", function () { state.q = this.value.trim().toLowerCase(); refresh(); });
    $("sort").addEventListener("change", function () { state.sort = this.value; refresh(); });
    $("age-select").addEventListener("change", function () { state.age = this.value; refresh(); });
    $("more").addEventListener("click", function () { shown += PAGE; renderList(); });
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
      else if (g === "q") { state.q = ""; $("q").value = ""; }
      else delete state[g][b.getAttribute("data-v")];
      refresh();
    });
    $("list").addEventListener("click", function (e) {
      var b = e.target.closest(".save");
      if (!b) return;
      var url = b.getAttribute("data-url");
      if (saved[url]) delete saved[url]; else saved[url] = Date.now();
      persistSaved();
      refresh(true);
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
        j.search = [j.title, j.company, j.role, j.kind, j.season || "", catLabel(j.category)]
          .concat(j.cities, j.locations, j.countries.map(cname)).join(" ").toLowerCase();
        return j;
      });
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
