/* 浏览量计数器前端：扫描 [data-view-path]，hit=自增并展示，count=只读展示 */
(function () {
  function fmt(n) { return (n == null ? 0 : n).toLocaleString("en-US"); }
  function updateOne(node) {
    if (node.__vc_done) return;
    var path = node.getAttribute("data-view-path");
    var mode = node.getAttribute("data-view-mode") || "hit";
    if (!path) return;
    node.__vc_done = true;
    function set(v) { node.textContent = fmt(v); }
    if (mode === "hit") {
      fetch("/api/view", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: path })
      }).then(function (r) { return r.json(); })
        .then(function (d) { set(d.count); })
        .catch(function () { set(0); });
    } else {
      fetch("/api/view?path=" + encodeURIComponent(path))
        .then(function (r) { return r.json(); })
        .then(function (d) { set(d.count); })
        .catch(function () { set(0); });
    }
  }
  function scan() {
    var nodes = document.querySelectorAll("[data-view-path]");
    for (var i = 0; i < nodes.length; i++) updateOne(nodes[i]);
  }
  scan();
  if (window.MutationObserver) {
    var obs = new MutationObserver(function () { scan(); });
    obs.observe(document.documentElement, { childList: true, subtree: true });
    setTimeout(function () { obs.disconnect(); }, 12000);
  } else {
    var t = 0, iv = setInterval(function () { scan(); t += 500; if (t > 12000) clearInterval(iv); }, 500);
  }
  window.__vc_scan = scan;
})();
