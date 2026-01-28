const chat = document.getElementById("chat");
const input = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");
const saveBtn = document.getElementById("saveBtn");
const clearBtn = document.getElementById("clearBtn");

let items = [];
let theme = "";
let originalNotes = "";
let hasProcessed = false;
let currentSuggestions = [];

// Auto-resize textarea
input.addEventListener("input", () => {
  input.style.height = "24px";
  input.style.height = Math.min(input.scrollHeight, 100) + "px";
});

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

function showSuggestions(suggestions) {
  if (!suggestions || suggestions.length === 0) return;

  currentSuggestions = suggestions;

  const div = document.createElement("div");
  div.className = "msg system suggestions-box";
  div.id = "suggestions-container";

  const header = document.createElement("div");
  header.className = "suggestions-header";
  header.textContent = "Suggestions based on theme (select to add):";
  div.appendChild(header);

  const list = document.createElement("div");
  list.className = "suggestions-list";

  suggestions.forEach((s, idx) => {
    const item = document.createElement("div");
    item.className = "suggestion-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = `suggestion-${idx}`;
    checkbox.className = "suggestion-checkbox";

    const label = document.createElement("label");
    label.htmlFor = `suggestion-${idx}`;
    label.className = "suggestion-label";
    label.innerHTML = `<strong>${s.english}</strong> ${s.chinese}<br><span class="suggestion-example">Example: ${s.example_en} ${s.example_zh}</span>`;

    item.appendChild(checkbox);
    item.appendChild(label);
    list.appendChild(item);
  });

  div.appendChild(list);

  const btnContainer = document.createElement("div");
  btnContainer.className = "suggestions-actions";

  const addBtn = document.createElement("button");
  addBtn.className = "btn primary small";
  addBtn.textContent = "Add Selected";
  addBtn.onclick = addSelectedSuggestions;

  const dismissBtn = document.createElement("button");
  dismissBtn.className = "btn secondary small";
  dismissBtn.textContent = "Dismiss";
  dismissBtn.onclick = () => div.remove();

  btnContainer.appendChild(addBtn);
  btnContainer.appendChild(dismissBtn);
  div.appendChild(btnContainer);

  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function showGrammarCheck(grammar) {
  const div = document.createElement("div");
  div.className = "msg system grammar-box";

  if (!grammar.has_issues) {
    div.classList.add("grammar-ok");
    div.innerHTML = `<span class="grammar-icon">✓</span> Grammar checked — No issues found`;
  } else {
    div.classList.add("grammar-issues");
    let html = `<span class="grammar-icon">!</span> Grammar checked — ${grammar.issues.length} issue(s) found:<div class="grammar-issues-list">`;
    grammar.issues.forEach(issue => {
      html += `<div class="grammar-issue-item">
        <strong>Item ${issue.item_index}</strong> (${issue.field === 'english' ? 'phrase' : 'example'}):<br>
        <span class="grammar-original">${issue.original}</span> →
        <span class="grammar-corrected">${issue.corrected}</span>
        <div class="grammar-explanation">${issue.explanation}</div>
      </div>`;
    });
    html += `</div>`;
    div.innerHTML = html;
  }

  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function addSelectedSuggestions() {
  const container = document.getElementById("suggestions-container");
  if (!container) return;

  const selected = [];
  currentSuggestions.forEach((s, idx) => {
    const checkbox = document.getElementById(`suggestion-${idx}`);
    if (checkbox && checkbox.checked) {
      selected.push(s);
    }
  });

  if (selected.length === 0) {
    addMsg("Please select at least one suggestion to add.", "system");
    return;
  }

  // Add selected items
  items = [...items, ...selected];

  // Rebuild preview
  let preview = theme ? `【主题】${theme}\n\n` : "";
  items.forEach((it, i) => {
    preview += `${i + 1}. ${it.english} ${it.chinese}\n`;
    preview += `例句: ${it.example_en} ${it.example_zh}\n\n`;
  });

  container.remove();
  addMsg(`Added ${selected.length} suggestion(s). Updated list:`, "system");
  addMsg(preview.trim(), "system", true);
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

    // Show grammar check result (only on process, not refine)
    if (data.grammar && data.grammar.checked) {
      showGrammarCheck(data.grammar);
    }

    // Show suggestions if available (only on process, not refine)
    if (data.suggestions && data.suggestions.length > 0) {
      showSuggestions(data.suggestions);
    }

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

clearBtn.onclick = () => {
  // Clear chat
  chat.innerHTML = "";

  // Reset state
  items = [];
  theme = "";
  originalNotes = "";
  hasProcessed = false;
  currentSuggestions = [];

  // Clear input
  input.value = "";

  addMsg("Chat cleared. Paste your new notes to start.", "system");
};
