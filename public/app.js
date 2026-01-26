const chat = document.getElementById("chat");
const input = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");
const saveBtn = document.getElementById("saveBtn");

let items = [];
let theme = "";
let originalNotes = "";
let hasProcessed = false;

function addMsg(text, who, showCopy = false) {
  const div = document.createElement("div");
  div.className = `msg ${who}`;

  if (showCopy) {
    const content = document.createElement("div");
    content.className = "msg-content";
    content.textContent = text;

    const copyBtn = document.createElement("button");
    copyBtn.className = "copy-btn";
    copyBtn.textContent = "Copy";
    copyBtn.onclick = () => {
      navigator.clipboard.writeText(text).then(() => {
        copyBtn.textContent = "Copied!";
        setTimeout(() => copyBtn.textContent = "Copy", 2000);
      });
    };

    div.appendChild(content);
    div.appendChild(copyBtn);
  } else {
    div.textContent = text;
  }

  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

sendBtn.onclick = async () => {
  const text = input.value.trim();
  if (!text) return;

  addMsg(text, "user");
  input.value = "";

  const loading = addMsg("Thinking…", "system");

  try {
    let res, data;

    // ✅ 自动判断：新内容 or refine
    if (!hasProcessed || text.length > 200 || text.includes("\n\n")) {
      // ---------- PROCESS ----------
      originalNotes = text;

      res = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: text }),
      });
    } else {
      // ---------- REFINE ----------
      res = await fetch("/api/refine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items: items,
          notes: originalNotes,
          feedback: text,
        }),
      });
    }

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`API error ${res.status}: ${errorText}`);
    }

    data = await res.json();
    hasProcessed = true;

    loading.remove();

    addMsg(data.preview, "system", true);

    items = data.items || items;
    theme = data.theme || theme;

  } catch (err) {
    loading.textContent = "❌ Error: " + err.message;
    console.error("API error:", err);
  }
};

saveBtn.onclick = async () => {
  if (!items.length) {
    addMsg("Nothing to save.", "system");
    return;
  }

  const loading = addMsg("Saving to Notion…", "system");

  try {
    const res = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items, theme }),
    });

    const data = await res.json();
    loading.textContent = `Saved: ${data.saved}, Failed: ${data.failed}`;
  } catch {
    loading.textContent = "❌ Save failed";
  }
};
