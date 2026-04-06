const THEME_STORAGE_KEY = "skill-atlas-theme";
const THEME_CHOICES = new Set(["light", "dark", "system"]);

const searchInput = document.getElementById("skillSearch");
const modalBackdrop = document.getElementById("skillModalBackdrop");
const modalClose = document.getElementById("skillModalClose");
const modalTitle = document.getElementById("skillModalTitle");
const modalDescription = document.getElementById("skillModalDescription");
const modalCategory = document.getElementById("skillModalCategory");
const modalSource = document.getElementById("skillModalSource");
const modalPath = document.getElementById("skillModalPath");
const themeButtons = Array.from(document.querySelectorAll("[data-theme-choice]"));
const discoverForm = document.getElementById("discoverForm");
const discoverInput = document.getElementById("discoverInput");
const discoverResults = document.getElementById("discoverResults");
const discoverFeedback = document.getElementById("discoverFeedback");
const discoverReset = document.getElementById("discoverReset");

function readThemePreference() {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (THEME_CHOICES.has(stored)) {
      return stored;
    }
  } catch (_error) {
    return "system";
  }

  return "system";
}

function writeThemePreference(theme) {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch (_error) {
    return;
  }
}

function updateThemeButtons(theme) {
  for (const button of themeButtons) {
    const active = button.dataset.themeChoice === theme;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  }
}

function applyTheme(theme) {
  const nextTheme = THEME_CHOICES.has(theme) ? theme : "system";
  document.documentElement.dataset.theme = nextTheme;

  if (nextTheme === "system") {
    document.documentElement.style.removeProperty("color-scheme");
  } else {
    document.documentElement.style.colorScheme = nextTheme;
  }

  updateThemeButtons(nextTheme);
}

function syncSystemTheme() {
  if (readThemePreference() === "system") {
    applyTheme("system");
  }
}

applyTheme(readThemePreference());

if (window.matchMedia) {
  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
  if (typeof systemTheme.addEventListener === "function") {
    systemTheme.addEventListener("change", syncSystemTheme);
  } else if (typeof systemTheme.addListener === "function") {
    systemTheme.addListener(syncSystemTheme);
  }
}

if (searchInput) {
  const cards = Array.from(document.querySelectorAll("[data-skill-card]"));

  searchInput.addEventListener("input", (event) => {
    const value = String(event.target.value || "").trim().toLowerCase();

    for (const card of cards) {
      const haystack = card.getAttribute("data-search") || "";
      const visible = !value || haystack.includes(value);
      card.classList.toggle("is-hidden", !visible);
    }
  });
}

function closeModal() {
  if (!modalBackdrop) {
    return;
  }

  modalBackdrop.hidden = true;
  document.body.classList.remove("modal-open");
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setDiscoverFeedback(message, tone = "muted") {
  if (!discoverFeedback) {
    return;
  }

  discoverFeedback.className = `discover-feedback is-${tone}`;
  discoverFeedback.textContent = message || "";
}

function renderSuggestions(suggestions) {
  if (!discoverResults) {
    return;
  }

  const cards = suggestions
    .map(
      (item) => `
        <button class="discover-card discover-suggestion" type="button" data-discover-query="${escapeHtml(item.query)}">
          <span class="discover-card-tag">推荐搜索</span>
          <h3>${escapeHtml(item.label)}</h3>
          <p>${escapeHtml(item.description)}</p>
          <code>${escapeHtml(item.query)}</code>
        </button>
      `,
    )
    .join("");

  discoverResults.innerHTML = `<div class="discover-grid">${cards}</div>`;
}

function renderDiscoverItems(items) {
  if (!discoverResults) {
    return;
  }

  const safeItems = Array.isArray(items) ? items : [];
  if (!safeItems.length) {
    discoverResults.innerHTML = `
      <div class="discover-empty">
        <h3>没有找到匹配的 Skill</h3>
        <p>可以换一个更具体的关键词，或者回到推荐搜索继续探索。</p>
      </div>
    `;
    return;
  }

  const cards = safeItems
    .map(
      (item) => `
        <article class="skill-card discover-result-card">
          <div class="skill-card-main">
            <div class="skill-card-top">
              <span class="skill-tag">Skill</span>
              <span class="skill-source discover-install-count">${escapeHtml(item.installs || "installs unknown")}</span>
            </div>
            <h3>${escapeHtml(item.name)}</h3>
            <p class="skill-description">${escapeHtml(item.description || "可通过 Skills CLI 安装的第三方 skill。")}</p>
            <div class="skill-meta">
              <code>${escapeHtml(item.package)}</code>
            </div>
          </div>
          <div class="skill-card-actions discover-result-actions">
            <button class="summary-button" type="button" data-install-package="${escapeHtml(item.package)}">一键安装</button>
            <a class="detail-link discover-source-link" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">skills.sh</a>
          </div>
        </article>
      `,
    )
    .join("");

  discoverResults.innerHTML = `<div class="discover-grid discover-grid-results">${cards}</div>`;
}

async function loadDiscover(query = "") {
  if (!discoverResults) {
    return;
  }

  const trimmedQuery = String(query || "").trim();
  const endpoint = trimmedQuery ? `/api/discover-skills?q=${encodeURIComponent(trimmedQuery)}` : "/api/discover-skills";

  setDiscoverFeedback(trimmedQuery ? `正在搜索 “${trimmedQuery}” ...` : "正在加载推荐搜索 ...", "muted");
  discoverResults.innerHTML = `<div class="discover-empty"><p>Loading...</p></div>`;

  try {
    const response = await fetch(endpoint);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.message || "Discovery request failed.");
    }

    if (payload.mode === "recommend") {
      renderSuggestions(payload.suggestions || []);
      setDiscoverFeedback("试试这些推荐搜索，或输入你自己的关键词。", "muted");
      return;
    }

    renderDiscoverItems(payload.items || []);
    const total = payload.items?.length || 0;
    setDiscoverFeedback(`已返回 ${total} 条搜索结果。`, "success");
  } catch (error) {
    discoverResults.innerHTML = `
      <div class="discover-empty">
        <h3>搜索失败</h3>
        <p>${escapeHtml(error.message || "Skills search failed.")}</p>
      </div>
    `;
    setDiscoverFeedback("Skills CLI 搜索失败，请检查网络或本机 npx skills 环境。", "error");
  }
}

async function installDiscoverPackage(pkg, button) {
  if (!pkg) {
    return;
  }

  const confirmed = window.confirm(`确认安装这个 skill 吗？\n\n${pkg}\n\n这会调用 npx skills add 并修改本地 skill 环境。`);
  if (!confirmed) {
    return;
  }

  if (button) {
    button.disabled = true;
    button.textContent = "安装中...";
  }

  setDiscoverFeedback(`正在安装 ${pkg} ...`, "muted");

  try {
    const response = await fetch("/api/install-skill", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ package: pkg }),
    });
    const payload = await response.json();

    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || "Install failed.");
    }

    setDiscoverFeedback(`${pkg} 安装成功。页面即将刷新，本地 skill 列表会同步更新。`, "success");
    if (button) {
      button.textContent = "已安装";
      button.disabled = true;
    }
    window.setTimeout(() => {
      window.location.reload();
    }, 900);
  } catch (error) {
    setDiscoverFeedback(`安装失败：${error.message || "unknown error"}`, "error");
    if (button) {
      button.textContent = "重试安装";
      button.disabled = false;
    }
  }
}

function openModal(button) {
  if (!modalBackdrop || !modalTitle || !modalDescription || !modalCategory || !modalSource || !modalPath) {
    return;
  }

  modalTitle.textContent = button.dataset.title || "Skill";
  modalDescription.textContent = button.dataset.description || "";
  modalCategory.textContent = button.dataset.category || "";
  modalSource.textContent = button.dataset.source || "";
  modalPath.textContent = button.dataset.path || "";
  modalBackdrop.hidden = false;
  document.body.classList.add("modal-open");
}

document.addEventListener("click", (event) => {
  const themeButton = event.target.closest("[data-theme-choice]");
  if (themeButton) {
    const nextTheme = themeButton.dataset.themeChoice || "system";
    writeThemePreference(nextTheme);
    applyTheme(nextTheme);
    return;
  }

  const suggestionButton = event.target.closest("[data-discover-query]");
  if (suggestionButton && discoverInput) {
    const query = suggestionButton.dataset.discoverQuery || "";
    discoverInput.value = query;
    void loadDiscover(query);
    return;
  }

  const installButton = event.target.closest("[data-install-package]");
  if (installButton) {
    const pkg = installButton.dataset.installPackage || "";
    void installDiscoverPackage(pkg, installButton);
    return;
  }

  const trigger = event.target.closest("[data-open-summary]");
  if (trigger) {
    openModal(trigger);
    return;
  }

  if (event.target === modalBackdrop || event.target === modalClose) {
    closeModal();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeModal();
  }
});

if (discoverForm && discoverInput) {
  discoverForm.addEventListener("submit", (event) => {
    event.preventDefault();
    void loadDiscover(discoverInput.value);
  });
}

if (discoverReset && discoverInput) {
  discoverReset.addEventListener("click", () => {
    discoverInput.value = "";
    void loadDiscover("");
  });
}

if (discoverResults) {
  void loadDiscover("");
}
