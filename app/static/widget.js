/* Embeddable chat. Load from the API host. Chat only — no upload UI.
   Cross-origin pages need CORS_ALLOW_ALL=true on the API.
   <script src="https://YOUR_API/widget.js" data-name="Docs Assistant" data-color="#2f5d50" defer></script>
*/
(function () {
  var script = document.currentScript;
  if (!script) return;

  var name = (script.getAttribute("data-name") || "Docs Assistant").slice(0, 60);
  var color = script.getAttribute("data-color") || "#2f5d50";
  if (!/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(color)) color = "#2f5d50";
  var logo = script.getAttribute("data-logo") || "";
  if (logo && !/^https?:\/\//i.test(logo)) logo = "";
  var api = (script.getAttribute("data-api") || new URL(script.src, window.location.href).origin).replace(/\/$/, "");

  var root = document.createElement("div");
  root.setAttribute("data-acme-widget", "1");
  root.style.cssText = "position:fixed;right:20px;bottom:20px;z-index:2147483000;font-family:Georgia,serif;";

  var button = document.createElement("button");
  button.type = "button";
  button.textContent = name;
  button.setAttribute("aria-expanded", "false");
  button.style.cssText =
    "border:0;border-radius:999px;padding:12px 16px;cursor:pointer;color:#f4efe6;font:500 15px/1.2 Georgia,serif;box-shadow:0 8px 24px rgba(0,0,0,.18);background:" +
    color;

  var panel = document.createElement("section");
  panel.hidden = true;
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", name);
  panel.style.cssText =
    "position:absolute;right:0;bottom:58px;width:min(380px,calc(100vw - 32px));height:520px;background:#fffdf8;border:1px solid #d9d0c1;border-radius:16px;box-shadow:0 16px 40px rgba(0,0,0,.18);display:flex;flex-direction:column;overflow:hidden;";

  var header = document.createElement("header");
  header.style.cssText = "display:flex;align-items:center;gap:8px;padding:12px 14px;color:#f4efe6;background:" + color;
  if (logo) {
    var img = document.createElement("img");
    img.alt = "";
    img.src = logo;
    img.style.cssText = "width:28px;height:28px;object-fit:contain;border-radius:6px;background:#fff";
    img.addEventListener("error", function () { img.remove(); });
    header.appendChild(img);
  }
  var title = document.createElement("strong");
  title.textContent = name;
  title.style.cssText = "flex:1;font-size:16px";
  var close = document.createElement("button");
  close.type = "button";
  close.textContent = "×";
  close.setAttribute("aria-label", "Close chat");
  close.style.cssText = "border:0;background:transparent;color:inherit;font-size:22px;cursor:pointer";
  header.appendChild(title);
  header.appendChild(close);

  var log = document.createElement("div");
  log.style.cssText = "flex:1;overflow:auto;padding:12px;display:flex;flex-direction:column;gap:10px;";

  var form = document.createElement("form");
  form.style.cssText = "display:flex;gap:8px;padding:12px;border-top:1px solid #d9d0c1;";
  var input = document.createElement("input");
  input.type = "text";
  input.required = true;
  input.placeholder = "Ask about the docs";
  input.setAttribute("aria-label", "Question");
  input.style.cssText = "flex:1;border:1px solid #d9d0c1;border-radius:8px;padding:8px 10px;font:14px/1.3 sans-serif;";
  var send = document.createElement("button");
  send.type = "submit";
  send.textContent = "Ask";
  send.style.cssText = "border:0;border-radius:8px;padding:8px 12px;cursor:pointer;color:#f4efe6;background:" + color;
  form.appendChild(input);
  form.appendChild(send);

  panel.appendChild(header);
  panel.appendChild(log);
  panel.appendChild(form);
  root.appendChild(panel);
  root.appendChild(button);
  document.body.appendChild(root);

  function setOpen(open) {
    panel.hidden = !open;
    button.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) input.focus();
  }
  button.addEventListener("click", function () { setOpen(panel.hidden); });
  close.addEventListener("click", function () { setOpen(false); });

  function bubble(text, mine) {
    var el = document.createElement("div");
    el.textContent = text;
    el.style.cssText =
      "white-space:pre-wrap;font:14px/1.45 sans-serif;padding:8px 10px;border-radius:10px;max-width:92%;" +
      (mine
        ? "align-self:flex-end;background:#efe6d4;color:#1c1914;"
        : "align-self:flex-start;background:#fff;border:1px solid #d9d0c1;color:#1c1914;");
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function cites(items) {
    if (!items || !items.length) return;
    var el = document.createElement("div");
    el.style.cssText = "font:12px/1.4 ui-monospace,monospace;color:#6b6458;";
    el.textContent = items.map(function (item) { return item.path; }).join(" · ");
    log.appendChild(el);
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var question = input.value.trim();
    if (!question) return;
    input.value = "";
    bubble(question, true);
    var pending = bubble("Searching…", false);
    send.disabled = true;
    fetch(api + "/v1/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question })
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) throw new Error(data.detail || data.error || "Ask failed");
          return data;
        });
      })
      .then(function (data) {
        pending.textContent = data.answer || "No answer returned.";
        cites(data.citations);
      })
      .catch(function (err) {
        pending.textContent = err.message || "The assistant is unavailable.";
      })
      .finally(function () {
        send.disabled = false;
        log.scrollTop = log.scrollHeight;
      });
  });
})();
