/* Profile page: connect your private repo, edit profile.json (the AutoInternship format, so the
   applier's skill and the AutoInternship extension read it as is) and upload your CV to resume/. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  var YESNO = [["", "Not set"], ["yes", "Yes"], ["no", "No"]];
  // [key, label, type, options/placeholder, hint]. "edu." keys edit the first education entry.
  var SECTIONS = [
    ["About you", [
      ["firstName", "First name", "text"], ["lastName", "Last name", "text"],
      ["preferredName", "Preferred name", "text", "", "Optional"],
      ["email", "Email", "email"], ["phone", "Phone", "tel", "+41 79 123 45 67"],
      ["city", "City", "text"], ["country", "Country", "text"],
      ["linkedin", "LinkedIn", "url", "https://linkedin.com/in/…"], ["github", "GitHub", "url", "https://github.com/…"],
      ["portfolio", "Portfolio or website", "url"]
    ]],
    ["Education", [
      ["edu.school", "University", "text"], ["edu.degree", "Degree", "text", "BSc, MSc, PhD…"],
      ["edu.field", "Subject", "text", "Computer Science"], ["edu.gpa", "Grade / GPA", "text", "", "Exactly as on your transcript"],
      ["edu.start", "Started", "text", "Sep 2024"], ["edu.end", "Ends", "text", "Jun 2027"],
      ["expectedGraduation", "Expected graduation", "text", "June 2027"],
      ["classStanding", "Year of study", "text", "2nd year"],
      ["enrolled", "Enrolled now", "select", YESNO],
      ["returningToSchool", "Returning to university after the internship", "select", YESNO],
      ["relevantCoursework", "Relevant courses", "textarea", "Algorithms, Operating Systems, Machine Learning…", "", true]
    ]],
    ["The internship", [
      ["internshipTerm", "Term", "text", "Summer 2027"],
      ["availableFrom", "Available from", "text", "June 1, 2027"], ["availableUntil", "Available until", "text", "September 15, 2027"],
      ["willingToRelocate", "Willing to relocate", "select", YESNO],
      ["workPreference", "Work preference", "select", [["", "Not set"], ["On-site", "On-site"], ["Hybrid", "Hybrid"], ["Remote", "Remote"], ["Any", "Any"]]],
      ["salary", "Salary expectation", "text", "", "Leave empty to have forms left for you"]
    ]],
    ["Right to work", [
      ["workAuthorized", "Allowed to work in the job's country", "select", YESNO],
      ["authCountry", "Countries you can work in", "text", "Switzerland, EU"],
      ["needsSponsorship", "Need visa sponsorship, now or later", "select", YESNO],
      ["needsSponsorshipForInternship", "Need sponsorship for the internship itself", "select", YESNO],
      ["workAuthDetails", "Your status in a sentence", "text", "EU citizen; UK Student visa until 2027", "Used for eligibility checks and written answers", true],
      ["governmentEmployee", "Current or former government employee", "select", YESNO],
      ["governmentRelative", "Close relative works for a government", "select", YESNO]
    ]],
    ["For written answers", [
      ["skills", "Skills", "textarea", "Python, C++, React, PyTorch…", "", true],
      ["summary", "About you in 2–3 sentences", "textarea", "", "", true],
      ["writingStyle", "How you write", "textarea", "Short and direct, no buzzwords", "Claude writes cover letters and answers in this style", true],
      ["extraRules", "Rules for Claude", "textarea", "One per line, e.g. Never mention my previous employer by name", "", true]
    ]]
  ];
  var REQUIRED = ["firstName", "lastName", "email", "phone", "workAuthorized", "needsSponsorship"];
  var CV_TYPES = /\.(docx|zip|pdf|tex)$/i;

  var profile = {}, sha = null, cvFiles = [], loaded = false, busy = false;

  function get(key) {
    if (key.indexOf("edu.") === 0) return ((profile.education || [])[0] || {})[key.slice(4)] || "";
    return profile[key] || "";
  }
  function set(key, value) {
    if (key.indexOf("edu.") === 0) {
      profile.education = profile.education && profile.education.length ? profile.education : [{}];
      profile.education[0][key.slice(4)] = value;
    } else profile[key] = value;
  }
  function field(f) {
    var key = f[0], label = f[1], type = f[2], extra = f[3], hint = f[4], wide = f[5];
    var id = "pf-" + key.replace(".", "-"), v = get(key), input;
    if (type === "select") {
      input = '<select id="' + id + '" data-key="' + key + '">' + extra.map(function (o) {
        return '<option value="' + esc(o[0]) + '"' + (o[0] === v ? " selected" : "") + ">" + esc(o[1]) + "</option>";
      }).join("") + "</select>";
    } else if (type === "textarea") {
      input = '<textarea id="' + id + '" data-key="' + key + '" rows="3" placeholder="' + esc(extra || "") + '">' + esc(v) + "</textarea>";
    } else {
      input = '<input id="' + id + '" data-key="' + key + '" type="' + type + '" value="' + esc(v) + '" placeholder="' + esc(extra || "") + '" autocomplete="off">';
    }
    var req = REQUIRED.indexOf(key) !== -1 ? ' <span class="req" title="Needed for applying">*</span>' : "";
    return '<label class="pf-field' + (wide ? " wide" : "") + '" for="' + id + '"><span>' + esc(label) + req + "</span>" + input +
      (hint ? '<small>' + esc(hint) + "</small>" : "") + "</label>";
  }
  function missing() {
    var m = REQUIRED.filter(function (k) { return !String(get(k)).trim(); });
    if (!cvFiles.length) m.unshift("cv");
    return m;
  }

  /* ---------------- rendering ---------------- */
  function renderConnect() {
    $("profile-root").innerHTML =
      '<div class="pf-grid"><section class="alert-card pf-connect">' +
      "<h2>Connect your private repo</h2>" +
      "<p>Your profile, CV and applications are kept in a <b>private</b> GitHub repo that only you can see. Your Mac reads the same repo when it applies. Connect it once on each device you use, phone included.</p>" +
      '<ol class="steps">' +
      '<li>Open <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">GitHub → new fine-grained token</a>.</li>' +
      "<li>Name it <b>InternRadar site</b>. Under <b>Repository access</b> choose <b>Only select repositories</b> and pick your private repo (e.g. <code>internradar-private</code>).</li>" +
      "<li>Under <b>Permissions → Repository permissions</b> set <b>Contents</b> to <b>Read and write</b>. Nothing else.</li>" +
      "<li>Generate it, copy it, and paste it below.</li></ol>" +
      '<form id="pf-connect" class="pf-form">' +
      '<label class="pf-field wide"><span>Private repo</span><input id="pf-repo" placeholder="your-username/internradar-private" value="' + esc(localStorage.getItem("private-repo-name") || "") + '" autocomplete="off" required></label>' +
      '<label class="pf-field wide"><span>Token</span><input id="pf-token" type="password" placeholder="github_pat_…" autocomplete="off" required></label>' +
      '<div class="pf-actions"><button class="btn primary" type="submit">Connect</button><span id="pf-connect-msg" class="pf-msg"></span></div>' +
      "</form>" +
      '<p class="small">The token is stored only in this browser and sent only to GitHub. It can reach that one repo and nothing else. Disconnect here, or delete the token on GitHub, at any time.</p>' +
      "</section></div>";
  }

  function renderProfile() {
    var m = missing();
    var cvList = cvFiles.length ? cvFiles.map(function (f) {
      return '<li><span class="cv-name">' + esc(f.name) + '</span><em>' + Math.max(1, Math.round(f.size / 1024)) + ' KB</em>' +
        '<button type="button" class="link-btn" data-cv-open="' + esc(f.path) + '">Open</button>' +
        '<button type="button" class="link-btn danger" data-cv-del="' + esc(f.path) + '" data-sha="' + esc(f.sha) + '">Remove</button></li>';
    }).join("") : '<li class="muted">No CV yet.</li>';
    var pdfOnly = cvFiles.length && cvFiles.every(function (f) { return /\.pdf$/i.test(f.name); });
    $("profile-root").innerHTML =
      '<div class="pf-status ' + (m.length ? "todo" : "ok") + '">' +
      (m.length ? "Still needed before applying: " + esc(m.map(function (k) { return k === "cv" ? "your CV" : labelOf(k); }).join(", ")) + "."
               : "✓ Profile complete. You can send applications from My jobs.") +
      '<span class="pf-conn">Connected to <b>' + esc(GH.repo()) + '</b> · <button type="button" class="link-btn" id="pf-disconnect">Disconnect</button></span></div>' +
      '<div class="pf-grid">' +
      '<section class="alert-card"><h2>CV</h2>' +
      "<p>Upload your full CV as a <b>Word .docx</b> or your <b>Overleaf project</b> (Overleaf → Menu → Download → Source, a .zip). Claude makes a tailored one-page version for every application. A PDF works too, but can't be tailored.</p>" +
      '<ul class="cv-list">' + cvList + "</ul>" +
      (pdfOnly ? '<p class="pf-warn">Only a PDF: applications will use it unchanged. Add a .docx or Overleaf .zip to get tailored CVs.</p>' : "") +
      '<label class="btn primary file-btn">Upload CV<input type="file" id="pf-cv" accept=".docx,.zip,.pdf,.tex"></label> <span id="pf-cv-msg" class="pf-msg"></span>' +
      "</section>" +
      '<section class="alert-card"><h2>Import or export</h2>' +
      "<p>Already filled in the AutoInternship extension? Click <b>Download backup</b> there and import that file here. It brings your work history, projects and saved answers too.</p>" +
      '<div class="pf-actions"><label class="btn file-btn">Import profile.json<input type="file" id="pf-import" accept=".json,application/json"></label>' +
      '<button type="button" class="btn" id="pf-export">Download profile.json</button></div>' +
      '<p class="small">To fill forms with the same answers, load the downloaded file in the AutoInternship extension with <b>Restore from backup</b>.</p>' +
      "</section></div>" +
      '<form id="pf-form" class="pf-form">' +
      SECTIONS.map(function (s) {
        return '<section class="alert-card pf-section"><h2>' + esc(s[0]) + '</h2><div class="pf-fields">' + s[1].map(field).join("") + "</div></section>";
      }).join("") +
      '<p class="small muted">Work history, projects and saved answers aren\'t edited here: Claude reads them from your CV, and saves answers you give it while applying.</p>' +
      '<div class="pf-save"><button class="btn primary" type="submit">Save profile</button><span id="pf-save-msg" class="pf-msg"></span></div>' +
      "</form>";
  }
  function labelOf(key) {
    for (var i = 0; i < SECTIONS.length; i++) for (var j = 0; j < SECTIONS[i][1].length; j++) {
      if (SECTIONS[i][1][j][0] === key) return SECTIONS[i][1][j][1].toLowerCase();
    }
    return key;
  }
  function msg(id, text, bad) {
    var el = $(id);
    if (!el) return;
    el.textContent = text;
    el.classList.toggle("bad", !!bad);
  }

  /* ---------------- data ---------------- */
  function load() {
    if (!GH.connected()) { renderConnect(); return Promise.resolve(); }
    $("profile-root").innerHTML = '<p class="muted">Loading your profile…</p>';
    return Promise.all([GH.getJSON("profile.json", {}), GH.list("resume")]).then(function (res) {
      profile = res[0].data || {};
      sha = res[0].sha;
      cvFiles = res[1].filter(function (f) { return f.type === "file" && CV_TYPES.test(f.name); });
      loaded = true;
      renderProfile();
      document.dispatchEvent(new CustomEvent("profile-state", { detail: { missing: missing() } }));
    }).catch(function (err) {
      $("profile-root").innerHTML = '<p class="pf-warn">Couldn\'t load your profile: ' + esc(err.message) + '</p>' +
        '<button type="button" class="btn" id="pf-disconnect">Disconnect</button>';
    });
  }
  function readForm() {
    Array.prototype.forEach.call(document.querySelectorAll("#pf-form [data-key]"), function (el) {
      set(el.getAttribute("data-key"), el.value.trim());
    });
  }
  function save() {
    if (busy) return;
    readForm();
    busy = true;
    msg("pf-save-msg", "Saving…");
    var mine = JSON.parse(JSON.stringify(profile));
    GH.update("profile.json", {}, function (remote) {
      // keep fields this page doesn't edit (work, projects, saved answers…) from the repo copy
      var merged = Object.assign({}, remote || {}, mine);
      if (remote && remote.education && remote.education.length > 1 && mine.education) {
        merged.education = [mine.education[0]].concat(remote.education.slice(1));
      }
      return merged;
    }, "Profile updated on the InternRadar site").then(function (saved) {
      profile = saved;
      busy = false;
      renderProfile();
      msg("pf-save-msg", "✓ Saved to your private repo");
      document.dispatchEvent(new CustomEvent("profile-state", { detail: { missing: missing() } }));
    }).catch(function (err) {
      busy = false;
      msg("pf-save-msg", "Not saved: " + err.message, true);
    });
  }
  function uploadCV(file) {
    if (!CV_TYPES.test(file.name)) { msg("pf-cv-msg", "Use a .docx, an Overleaf .zip or a .pdf", true); return; }
    if (file.size > 20 * 1024 * 1024) { msg("pf-cv-msg", "That file is over 20 MB", true); return; }
    var name = file.name.replace(/[^\w.\- ()]+/g, "_");
    var existing = cvFiles.filter(function (f) { return f.name === name; })[0];
    msg("pf-cv-msg", "Uploading…");
    GH.b64FromFile(file).then(function (b64) {
      return GH.putB64("resume/" + name, b64, "CV uploaded on the InternRadar site", existing && existing.sha);
    }).then(function () {
      msg("pf-cv-msg", "");
      return load();
    }).then(function () { msg("pf-cv-msg", "✓ Uploaded " + name); })
      .catch(function (err) { msg("pf-cv-msg", "Upload failed: " + err.message, true); });
  }
  function openFile(path) {
    var w = window.open("", "_blank");
    GH.getBlob(path).then(function (blob) {
      var type = /\.pdf$/i.test(path) ? "application/pdf" : blob.type;
      var url = URL.createObjectURL(new Blob([blob], { type: type }));
      if (w) w.location.href = url; else location.href = url;
    }).catch(function (err) { if (w) w.close(); alert("Couldn't open it: " + err.message); });
  }

  /* ---------------- events ---------------- */
  document.addEventListener("submit", function (e) {
    if (e.target.id === "pf-connect") {
      e.preventDefault();
      var repo = $("pf-repo").value, token = $("pf-token").value;
      msg("pf-connect-msg", "Checking…");
      GH.connect(repo, token).then(function (r) {
        try { localStorage.setItem("private-repo-name", r); } catch (err) {}
        load();
      }).catch(function (err) { msg("pf-connect-msg", err.message, true); });
    } else if (e.target.id === "pf-form") {
      e.preventDefault();
      save();
    }
  });
  document.addEventListener("change", function (e) {
    var t = e.target;
    if (t.id === "pf-cv" && t.files[0]) uploadCV(t.files[0]);
    if (t.id === "pf-import" && t.files[0]) {
      t.files[0].text().then(function (text) {
        var data = JSON.parse(text);
        if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("not a profile");
        readForm();
        profile = Object.assign({}, profile, data);
        renderProfile();
        msg("pf-save-msg", "Imported. Check it, then Save profile.");
        $("pf-save-msg").scrollIntoView({ block: "center", behavior: "smooth" });
      }).catch(function () { alert("That file isn't a profile.json backup."); });
    }
  });
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (t.id === "pf-disconnect") {
      if (confirm("Disconnect this browser from your private repo? Nothing in the repo is deleted.")) { GH.disconnect(); loaded = false; renderConnect(); }
    } else if (t.id === "pf-export") {
      readForm();
      var a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([JSON.stringify(profile, null, 2) + "\n"], { type: "application/json" }));
      a.download = "profile.json";
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 0);
    } else if (t.getAttribute("data-cv-open")) {
      openFile(t.getAttribute("data-cv-open"));
    } else if (t.getAttribute("data-cv-del")) {
      var path = t.getAttribute("data-cv-del");
      if (!confirm("Remove " + path.split("/").pop() + " from your private repo? (Its Git history keeps a copy.)")) return;
      GH.remove(path, t.getAttribute("data-sha"), "CV removed on the InternRadar site").then(load)
        .catch(function (err) { alert("Couldn't remove it: " + err.message); });
    }
  });

  window.Profile = {
    show: function () { if (!loaded || !GH.connected()) load(); },
    reload: load,
    missing: function () { return loaded ? missing() : null; }
  };
})();
