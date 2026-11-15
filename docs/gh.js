/* Your private GitHub repo, read and written straight from the browser with a fine-grained token.
   The repo holds profile.json, your CV in resume/, applications.json (what you asked the applier
   on your Mac to do, and what it did) and myjobs.json (starred jobs, shared across devices).
   The token stays in this browser's storage and is only ever sent to api.github.com. */
(function () {
  "use strict";
  var KEY = "private-repo";
  var API = "https://api.github.com";
  var cfg = null;
  try { cfg = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { cfg = null; }

  function enc(path) { return path.split("/").map(encodeURIComponent).join("/"); }
  function b64FromText(text) {
    var bytes = new TextEncoder().encode(text), bin = "";
    for (var i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(bin);
  }
  function textFromB64(b64) {
    var bin = atob(b64.replace(/\s/g, ""));
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  }
  function b64FromFile(file) {
    return new Promise(function (resolve, reject) {
      var r = new FileReader();
      r.onload = function () { resolve(String(r.result).split(",")[1] || ""); };
      r.onerror = function () { reject(r.error); };
      r.readAsDataURL(file);
    });
  }

  function req(method, path, body, accept, conf) {
    var c = conf || cfg;
    if (!c) return Promise.reject(new Error("Not connected to your private repo"));
    var opts = {
      method: method, cache: "no-store",
      headers: { "Authorization": "Bearer " + c.token, "Accept": accept || "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28" }
    };
    if (body) { opts.body = JSON.stringify(body); opts.headers["Content-Type"] = "application/json"; }
    return fetch(API + path, opts).then(function (r) {
      if (r.ok) return r;
      return r.text().then(function (t) {
        var msg = t;
        try { msg = JSON.parse(t).message || t; } catch (e) {}
        var err = new Error("GitHub " + r.status + ": " + msg);
        err.status = r.status;
        throw err;
      });
    });
  }
  function contents(path) { return "/repos/" + cfg.repo + "/contents/" + enc(path); }

  /* {data, sha} for a JSON file; {data: fallback, sha: null} if it doesn't exist yet. */
  function getJSON(path, fallback) {
    return req("GET", contents(path)).then(function (r) { return r.json(); }).then(function (j) {
      var text = j.content ? textFromB64(j.content) : "";
      var data = fallback;
      try { data = text ? JSON.parse(text) : fallback; } catch (e) { throw new Error(path + " is not valid JSON"); }
      return { data: data, sha: j.sha };
    }, function (err) {
      if (err.status === 404) return { data: fallback, sha: null };
      throw err;
    });
  }
  function putB64(path, b64, message, sha) {
    var body = { message: message, content: b64 };
    if (sha) body.sha = sha;
    return req("PUT", contents(path), body).then(function (r) { return r.json(); })
      .then(function (j) { return j.content && j.content.sha; });
  }
  function putJSON(path, data, sha, message) {
    return putB64(path, b64FromText(JSON.stringify(data, null, 1) + "\n"), message, sha);
  }
  /* Read, change with fn(data) (return the new data, or nothing to skip), write; retries when
     someone else (the Mac, another device) wrote in between. */
  function update(path, fallback, fn, message) {
    var tries = 0;
    function attempt() {
      return getJSON(path, fallback).then(function (got) {
        var next = fn(JSON.parse(JSON.stringify(got.data)));
        if (next === undefined) return got.data;
        return putJSON(path, next, got.sha, message).then(function () { return next; });
      }).catch(function (err) {
        if ((err.status === 409 || err.status === 422) && ++tries < 5) {
          return new Promise(function (res) { setTimeout(res, 800 * tries); }).then(attempt);
        }
        throw err;
      });
    }
    return attempt();
  }
  function list(path) {
    return req("GET", contents(path)).then(function (r) { return r.json(); }).then(function (j) {
      return Array.isArray(j) ? j : [];
    }, function (err) { if (err.status === 404) return []; throw err; });
  }
  function getBlob(path) {
    return req("GET", contents(path), null, "application/vnd.github.raw+json").then(function (r) { return r.blob(); });
  }
  function getText(path) { return getBlob(path).then(function (b) { return b.text(); }); }
  function remove(path, sha, message) {
    return req("DELETE", contents(path), { message: message, sha: sha });
  }

  /* Check a repo + token before saving them: the repo must exist, be private and be writable. */
  function test(repo, token) {
    var c = { repo: repo, token: token };
    return req("GET", "/repos/" + repo, null, null, c).then(function (r) { return r.json(); }).then(function (j) {
      if (!j.private) throw new Error(repo + " is public. Use a private repo: your CV and answers would be visible to anyone.");
      if (j.permissions && j.permissions.push === false) throw new Error("This token can read " + repo + " but not write to it. Give it Contents: Read and write.");
      return j;
    }, function (err) {
      if (err.status === 401) throw new Error("GitHub didn't accept this token. Check you copied all of it, and that it hasn't expired.");
      if (err.status === 404) throw new Error("Can't see " + repo + ". Check the name, and that the token has access to this repository.");
      throw err;
    });
  }

  window.GH = {
    connected: function () { return !!(cfg && cfg.repo && cfg.token); },
    repo: function () { return cfg ? cfg.repo : ""; },
    connect: function (repo, token) {
      repo = repo.trim().replace(/^https?:\/\/github\.com\//, "").replace(/\.git$/, "").replace(/\/$/, "");
      token = token.trim();
      return test(repo, token).then(function () {
        cfg = { repo: repo, token: token };
        try { localStorage.setItem(KEY, JSON.stringify(cfg)); } catch (e) {}
        document.dispatchEvent(new Event("gh-connection"));
        return repo;
      });
    },
    disconnect: function () {
      cfg = null;
      try { localStorage.removeItem(KEY); } catch (e) {}
      document.dispatchEvent(new Event("gh-connection"));
    },
    getJSON: getJSON, putJSON: putJSON, update: update, list: list,
    getBlob: getBlob, getText: getText, putB64: putB64, b64FromFile: b64FromFile, remove: remove
  };
})();
