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
