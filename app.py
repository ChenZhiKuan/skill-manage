#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib.parse
from dataclasses import asdict, dataclass
from functools import lru_cache
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable


APP_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = APP_DIR.parent
HOME = Path.home()
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
PACKAGE_LINE_RE = re.compile(
    r"^(?P<package>[A-Za-z0-9._-]+/[A-Za-z0-9._-]+@[\w./:-]+)(?:\s+(?P<installs>[0-9][0-9.,KMB]*\s+installs))?$"
)
SKILLS_URL_RE = re.compile(r"^└\s+(?P<url>https://skills\.sh/\S+)$")
PACKAGE_SPEC_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+@[\w./:-]+$")
SKILLS_COMMAND_TIMEOUT = 45


ROOT_SPECS: list[tuple[str, Path]] = [
    ("User Skills", HOME / ".agents" / "skills"),
    ("Codex System Skills", HOME / ".codex" / "skills"),
    ("Codex Plugins", HOME / ".codex" / "plugins"),
    ("Workspace Skills", WORKSPACE_ROOT / ".agents" / "skills"),
    ("Workspace Misc Skills", WORKSPACE_ROOT / "miscellany" / "agent" / "skills"),
]


CATEGORY_ORDER = [
    "通用开发与规划",
    "GitHub / Notion",
    "网页 / 研究 / 内容",
    "文档与 Office",
    "图像",
    "Chrome / 扩展",
    "财务 / 对账",
    "飞书 / Lark",
    "其他",
]


EXPLICIT_CATEGORY_MAP = {
    "brainstorming": "通用开发与规划",
    "codebase-spec-extractor": "通用开发与规划",
    "planning-with-files": "通用开发与规划",
    "loopback": "通用开发与规划",
    "frontend-design": "通用开发与规划",
    "openai-docs": "通用开发与规划",
    "plugin-creator": "通用开发与规划",
    "skill-creator": "通用开发与规划",
    "skill-create-flow": "通用开发与规划",
    "skill-review-audit": "通用开发与规划",
    "skill-auditor": "通用开发与规划",
    "find-skills": "通用开发与规划",
    "skill-installer": "通用开发与规划",
    "github:github": "GitHub / Notion",
    "github:gh-address-comments": "GitHub / Notion",
    "github:gh-fix-ci": "GitHub / Notion",
    "github:yeet": "GitHub / Notion",
    "notion:notion-knowledge-capture": "GitHub / Notion",
    "notion:notion-meeting-intelligence": "GitHub / Notion",
    "notion:notion-research-documentation": "GitHub / Notion",
    "notion:notion-spec-to-implementation": "GitHub / Notion",
    "daily-ai-news": "网页 / 研究 / 内容",
    "headless-web-viewer": "网页 / 研究 / 内容",
    "google-flights": "网页 / 研究 / 内容",
    "notebooklm": "网页 / 研究 / 内容",
    "docx-offline": "文档与 Office",
    "pdf-offline": "文档与 Office",
    "pptx-offline": "文档与 Office",
    "xlsx-offline": "文档与 Office",
    "imagegen": "图像",
    "nano-banana-2": "图像",
    "chrome-extension-development": "Chrome / 扩展",
    "reconciliation": "财务 / 对账",
}


DISCOVER_SUGGESTIONS = [
    {
        "label": "React",
        "query": "react",
        "description": "组件实践、性能与前端工程",
    },
    {
        "label": "Testing",
        "query": "testing",
        "description": "单测、E2E 与自动化校验",
    },
    {
        "label": "PR Review",
        "query": "pr review",
        "description": "代码评审与改评审意见",
    },
    {
        "label": "Docs",
        "query": "docs",
        "description": "README、文档与知识整理",
    },
    {
        "label": "Automation",
        "query": "automation",
        "description": "工作流、脚本与 agent 自动化",
    },
    {
        "label": "GitHub",
        "query": "github",
        "description": "PR、issue、CI 与仓库协作",
    },
]


@dataclass(frozen=True)
class SkillRecord:
    slug: str
    name: str
    title: str
    description: str
    license_name: str
    category: str
    source_group: str
    source_root: str
    skill_path: str
    folder_path: str
    relative_folder: str
    readme_path: str | None
    detail_markdown: str


@dataclass(frozen=True)
class DiscoverResult:
    package: str
    name: str
    url: str
    installs: str
    source_repo: str
    description: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local skill browser for Codex-style skills.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8421, help="Port to bind. Default: 8421")
    return parser.parse_args()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "skill"


def parse_frontmatter(markdown_text: str) -> tuple[dict[str, str], str]:
    if not markdown_text.startswith("---\n"):
        return {}, markdown_text

    parts = markdown_text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, markdown_text

    frontmatter_text, body = parts
    metadata: dict[str, str] = {}
    for line in frontmatter_text.splitlines()[1:]:
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        metadata[key.strip()] = raw_value.strip().strip('"').strip("'")
    return metadata, body.lstrip("\n")


def classify_skill(name: str, description: str) -> str:
    if name in EXPLICIT_CATEGORY_MAP:
        return EXPLICIT_CATEGORY_MAP[name]
    if name.startswith("lark-"):
        return "飞书 / Lark"
    if name.startswith("github:") or name.startswith("notion:"):
        return "GitHub / Notion"

    lowered = f"{name} {description}".lower()
    if any(token in lowered for token in ("docx", "pptx", "xlsx", "pdf", "office")):
        return "文档与 Office"
    if any(token in lowered for token in ("image", "bitmap", "illustration")):
        return "图像"
    if "chrome extension" in lowered:
        return "Chrome / 扩展"
    if any(token in lowered for token in ("reconcile", "reconciliation", "gl")):
        return "财务 / 对账"
    if any(token in lowered for token in ("github", "notion", "pull request", "issue")):
        return "GitHub / Notion"
    if any(token in lowered for token in ("web", "research", "news", "browser", "flight")):
        return "网页 / 研究 / 内容"
    return "其他"


def choose_readme(skill_dir: Path) -> Path | None:
    for candidate_name in ("README.md", "README.zh-CN.md", "README.txt"):
        candidate = skill_dir / candidate_name
        if candidate.exists():
            return candidate
    return None


def scan_skill_root(label: str, root: Path) -> list[SkillRecord]:
    if not root.exists():
        return []

    records: list[SkillRecord] = []
    for skill_file in sorted(root.rglob("SKILL.md")):
        try:
            markdown_text = skill_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            markdown_text = skill_file.read_text(encoding="utf-8", errors="replace")

        metadata, body = parse_frontmatter(markdown_text)
        skill_dir = skill_file.parent
        folder_name = skill_dir.name
        name = metadata.get("name") or folder_name
        title = name
        description = metadata.get("description") or first_non_empty_line(body)
        license_name = metadata.get("license", "")
        category = classify_skill(name, description)
        relative_folder = str(skill_dir.relative_to(root))
        readme_path = choose_readme(skill_dir)
        slug = slugify(f"{label}-{relative_folder}")
        detail_markdown = body

        records.append(
            SkillRecord(
                slug=slug,
                name=name,
                title=title,
                description=description,
                license_name=license_name,
                category=category,
                source_group=label,
                source_root=str(root),
                skill_path=str(skill_file),
                folder_path=str(skill_dir),
                relative_folder=relative_folder,
                readme_path=str(readme_path) if readme_path else None,
                detail_markdown=detail_markdown,
            )
        )
    return records


def first_non_empty_line(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


@lru_cache(maxsize=1)
def load_skills() -> list[SkillRecord]:
    records: list[SkillRecord] = []
    for label, root in ROOT_SPECS:
        records.extend(scan_skill_root(label, root))

    records.sort(key=lambda item: (CATEGORY_ORDER.index(item.category) if item.category in CATEGORY_ORDER else 999, item.name.lower(), item.folder_path.lower()))
    return records


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def skills_command_env() -> dict[str, str]:
    env = dict(**os.environ)
    env["NO_COLOR"] = "1"
    env["FORCE_COLOR"] = "0"
    env["CI"] = "1"
    return env


def run_skills_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=SKILLS_COMMAND_TIMEOUT,
        env=skills_command_env(),
        cwd=str(APP_DIR),
        check=False,
    )


def parse_find_results(raw_output: str) -> list[DiscoverResult]:
    lines = [strip_ansi(line).strip() for line in raw_output.splitlines()]
    results: list[DiscoverResult] = []

    for line in lines:
        if not line:
            continue

        package_match = PACKAGE_LINE_RE.match(line)
        if package_match:
            package = package_match.group("package")
            skill_name = package.split("@", 1)[1]
            source_repo = package.split("@", 1)[0]
            results.append(
                DiscoverResult(
                    package=package,
                    name=skill_name,
                    url="",
                    installs=package_match.group("installs") or "",
                    source_repo=source_repo,
                    description=f"来自 {source_repo} 的 {skill_name} skill。",
                )
            )
            continue

        url_match = SKILLS_URL_RE.match(line)
        if url_match and results:
            last = results[-1]
            results[-1] = DiscoverResult(
                package=last.package,
                name=last.name,
                url=url_match.group("url"),
                installs=last.installs,
                source_repo=last.source_repo,
                description=last.description,
            )

    return results


def discover_skills(query: str) -> dict[str, object]:
    cleaned_query = query.strip()
    if not cleaned_query:
        return {
            "mode": "recommend",
            "query": "",
            "suggestions": DISCOVER_SUGGESTIONS,
        }

    command = ["npx", "-y", "skills", "find", *cleaned_query.split()]
    completed = run_skills_command(command)
    combined_output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()

    if completed.returncode != 0:
        raise RuntimeError(strip_ansi(combined_output) or "Skills CLI search failed.")

    items = [asdict(item) for item in parse_find_results(completed.stdout)]
    return {
        "mode": "search",
        "query": cleaned_query,
        "items": items,
        "raw_output": strip_ansi(completed.stdout).strip(),
    }


def install_skill(package: str) -> dict[str, object]:
    normalized = package.strip()
    if not PACKAGE_SPEC_RE.match(normalized):
        raise ValueError("Invalid skill package format. Expected owner/repo@skill.")

    command = ["npx", "-y", "skills", "add", normalized, "-g", "-y"]
    completed = run_skills_command(command)
    combined_output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    clean_output = strip_ansi(combined_output)

    if completed.returncode != 0:
        raise RuntimeError(clean_output or "Skills CLI install failed.")

    load_skills.cache_clear()
    return {
        "ok": True,
        "package": normalized,
        "message": "Installed successfully.",
        "details": clean_output.strip(),
    }


def group_by(items: Iterable[SkillRecord], key_fn) -> list[tuple[str, list[SkillRecord]]]:
    grouped: dict[str, list[SkillRecord]] = {}
    for item in items:
        grouped.setdefault(key_fn(item), []).append(item)

    def sort_key(group_name: str) -> tuple[int, str]:
        if group_name in CATEGORY_ORDER:
            return (CATEGORY_ORDER.index(group_name), group_name)
        return (999, group_name.lower())

    return [(name, sorted(values, key=lambda record: (record.name.lower(), record.relative_folder.lower()))) for name, values in sorted(grouped.items(), key=lambda pair: sort_key(pair[0]))]


def markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.replace("\r\n", "\n").split("\n")
    chunks: list[str] = []
    in_code_block = False
    code_lang = ""
    code_lines: list[str] = []
    list_items: list[str] = []
    paragraph_lines: list[str] = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            chunks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            paragraph = " ".join(part.strip() for part in paragraph_lines)
            chunks.append(f"<p>{inline_markdown(paragraph)}</p>")
            paragraph_lines = []

    for line in lines:
        if line.startswith("```"):
            flush_list()
            flush_paragraph()
            if in_code_block:
                code = html.escape("\n".join(code_lines))
                lang_attr = f' data-lang="{html.escape(code_lang)}"' if code_lang else ""
                chunks.append(f"<pre class=\"doc-code\"{lang_attr}><code>{code}</code></pre>")
                in_code_block = False
                code_lines = []
                code_lang = ""
            else:
                in_code_block = True
                code_lang = line[3:].strip()
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            flush_list()
            flush_paragraph()
            continue

        if stripped.startswith(("# ", "## ", "### ")):
            flush_list()
            flush_paragraph()
            level = 1 if stripped.startswith("# ") else 2 if stripped.startswith("## ") else 3
            chunks.append(f"<h{level}>{inline_markdown(stripped[level + 1:])}</h{level}>")
            continue

        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            list_items.append(inline_markdown(stripped[2:]))
            continue

        if stripped.startswith("> "):
            flush_list()
            flush_paragraph()
            chunks.append(f"<blockquote>{inline_markdown(stripped[2:])}</blockquote>")
            continue

        paragraph_lines.append(stripped)

    flush_list()
    flush_paragraph()

    if in_code_block:
        code = html.escape("\n".join(code_lines))
        lang_attr = f' data-lang="{html.escape(code_lang)}"' if code_lang else ""
        chunks.append(f"<pre class=\"doc-code\"{lang_attr}><code>{code}</code></pre>")

    return "\n".join(chunks)


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noreferrer">\1</a>', escaped)
    return escaped


def render_layout(title: str, content: str) -> bytes:
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <script>
    (() => {{
      const key = "skill-atlas-theme";
      const allowed = new Set(["system", "light", "dark"]);
      let theme = "system";
      try {{
        const stored = window.localStorage.getItem(key);
        if (allowed.has(stored)) {{
          theme = stored;
        }}
      }} catch (_error) {{
        theme = "system";
      }}
      document.documentElement.dataset.theme = theme;
    }})();
  </script>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <div class="texture"></div>
  <div class="shell">
    <div class="utility-bar">
      <div class="theme-switcher" aria-label="切换外观">
        <span class="theme-switcher-label">外观</span>
        <div class="theme-switcher-options" role="group" aria-label="主题模式">
          <button class="theme-option" type="button" data-theme-choice="light">浅色</button>
          <button class="theme-option" type="button" data-theme-choice="dark">深色</button>
          <button class="theme-option" type="button" data-theme-choice="system">跟随系统</button>
        </div>
      </div>
    </div>
    {content}
  </div>
  <script src="/static/app.js"></script>
</body>
</html>
"""
    return page.encode("utf-8")


def render_home(view_mode: str) -> bytes:
    skills = load_skills()
    groups = group_by(skills, lambda item: item.source_group if view_mode == "path" else item.category)
    summary = {
        "skills": len(skills),
        "paths": len({item.source_group for item in skills}),
        "categories": len({item.category for item in skills}),
    }

    groups_html = []
    for group_name, items in groups:
        cards = "\n".join(render_skill_card(item) for item in items)
        groups_html.append(
            f"""
            <section class="group-block" data-group="{html.escape(group_name.lower())}">
              <div class="group-head">
                <div>
                  <p class="eyebrow">{'PATH VIEW' if view_mode == 'path' else 'FUNCTION VIEW'}</p>
                  <h2>{html.escape(group_name)}</h2>
                </div>
                <div class="count-chip">{len(items)} skills</div>
              </div>
              <div class="card-grid">
                {cards}
              </div>
            </section>
            """
        )

    content = f"""
    <header class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Skill Atlas</p>
        <h1>本机 Skill 地图</h1>
        <p class="hero-text">
          一个可本地运行的 skill 浏览器。它从常见 Codex skill 根目录扫描技能，
          支持按路径来源与按功能分区查看，并可进入详情页直接阅读 <code>SKILL.md</code>。
        </p>
      </div>
      <div class="hero-panel">
        <div class="metric">
          <span class="metric-label">已收录</span>
          <strong>{summary['skills']}</strong>
        </div>
        <div class="metric">
          <span class="metric-label">扫描路径</span>
          <strong>{summary['paths']}</strong>
        </div>
        <div class="metric">
          <span class="metric-label">功能分区</span>
          <strong>{summary['categories']}</strong>
        </div>
      </div>
    </header>

    <section class="discover-panel" id="discoverPanel">
      <div class="discover-head">
        <div>
          <p class="eyebrow">Skill Discovery</p>
          <h2>搜索并安装新 Skill</h2>
        </div>
        <p class="discover-note">
          输入关键词会调用 <code>npx skills find</code> 搜索；留空则显示推荐搜索方向。
        </p>
      </div>
      <form class="discover-toolbar" id="discoverForm">
        <label class="discover-search">
          <span>发现更多能力</span>
          <input id="discoverInput" name="q" type="search" placeholder="输入 react、testing、review、docs 等关键词">
        </label>
        <div class="discover-actions">
          <button class="summary-button discover-submit" type="submit">搜索 Skill</button>
          <button class="switch-pill discover-reset" id="discoverReset" type="button">恢复推荐</button>
        </div>
      </form>
      <div class="discover-feedback" id="discoverFeedback" aria-live="polite"></div>
      <div class="discover-results" id="discoverResults"></div>
    </section>

    <section class="toolbar">
      <div class="view-switch">
        <a class="switch-pill {'active' if view_mode == 'path' else ''}" href="/?view=path">按路径分类</a>
        <a class="switch-pill {'active' if view_mode == 'category' else ''}" href="/?view=category">按功能分类</a>
      </div>
      <label class="search-box">
        <span>现场筛选</span>
        <input id="skillSearch" type="search" placeholder="输入 skill 名、描述或路径">
      </label>
    </section>

    <section class="source-strip">
      {"".join(f'<div class="source-chip"><span>{html.escape(label)}</span><code>{html.escape(str(path))}</code></div>' for label, path in ROOT_SPECS if path.exists())}
    </section>

    <main class="groups">
      {''.join(groups_html)}
    </main>

    <div class="modal-backdrop" id="skillModalBackdrop" hidden>
      <div class="modal-shell" role="dialog" aria-modal="true" aria-labelledby="skillModalTitle">
        <button class="modal-close" id="skillModalClose" aria-label="关闭简介弹窗">×</button>
        <p class="eyebrow">Skill Summary</p>
        <h2 id="skillModalTitle">Skill</h2>
        <div class="modal-meta">
          <span id="skillModalCategory" class="skill-tag"></span>
          <span id="skillModalSource" class="skill-source"></span>
        </div>
        <p class="modal-description" id="skillModalDescription"></p>
        <div class="modal-paths">
          <div>
            <span>Relative Folder</span>
            <code id="skillModalPath"></code>
          </div>
        </div>
      </div>
    </div>
    """
    return render_layout("Skill Atlas", content)


def render_skill_card(item: SkillRecord) -> str:
    description = html.escape(item.description or "No description")
    return f"""
    <article class="skill-card" data-skill-card data-search="{html.escape((item.name + ' ' + item.description + ' ' + item.relative_folder + ' ' + item.source_group).lower())}">
      <div class="skill-card-main">
        <div class="skill-card-top">
          <span class="skill-tag">{html.escape(item.category)}</span>
          <span class="skill-source">{html.escape(item.source_group)}</span>
        </div>
        <h3>{html.escape(item.title)}</h3>
        <p class="skill-description">{description}</p>
        <div class="skill-meta">
          <code>{html.escape(item.relative_folder)}</code>
        </div>
      </div>
      <div class="skill-card-actions">
        <button
          class="summary-button"
          type="button"
          data-open-summary
          data-title="{html.escape(item.title)}"
          data-description="{description}"
          data-category="{html.escape(item.category)}"
          data-source="{html.escape(item.source_group)}"
          data-path="{html.escape(item.relative_folder)}"
        >
          查看简介
        </button>
        <a class="detail-link" href="/skill/{urllib.parse.quote(item.slug)}">查看详情</a>
      </div>
    </article>
    """


def render_detail(item: SkillRecord) -> bytes:
    detail_html = markdown_to_html(item.detail_markdown)
    readme_row = f'<li><span>README</span><code>{html.escape(item.readme_path)}</code></li>' if item.readme_path else ""
    content = f"""
    <header class="detail-hero">
      <div>
        <p class="eyebrow">{html.escape(item.category)}</p>
        <h1>{html.escape(item.title)}</h1>
        <p class="hero-text">{html.escape(item.description)}</p>
      </div>
      <a class="back-link" href="/?view=category">返回总览</a>
    </header>

    <section class="detail-grid">
      <aside class="info-panel">
        <h2>Skill 元信息</h2>
        <ul class="info-list">
          <li><span>Name</span><code>{html.escape(item.name)}</code></li>
          <li><span>Source Group</span><code>{html.escape(item.source_group)}</code></li>
          <li><span>Source Root</span><code>{html.escape(item.source_root)}</code></li>
          <li><span>Folder</span><code>{html.escape(item.folder_path)}</code></li>
          <li><span>SKILL.md</span><code>{html.escape(item.skill_path)}</code></li>
          {readme_row}
          <li><span>License</span><code>{html.escape(item.license_name or 'N/A')}</code></li>
        </ul>
      </aside>
      <article class="doc-panel">
        <div class="doc-head">
          <span class="doc-badge">SKILL.md</span>
          <code>{html.escape(item.skill_path)}</code>
        </div>
        <div class="doc-body">
          {detail_html}
        </div>
      </article>
    </section>
    """
    return render_layout(f"{item.title} · Skill Atlas", content)


def render_json(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


class SkillAtlasHandler(BaseHTTPRequestHandler):
    server_version = "SkillAtlas/0.1"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            view_mode = query.get("view", ["category"])[0]
            if view_mode not in {"category", "path"}:
                view_mode = "category"
            self.respond(HTTPStatus.OK, "text/html; charset=utf-8", render_home(view_mode))
            return

        if path == "/api/skills":
            payload = [asdict(skill) for skill in load_skills()]
            self.respond(HTTPStatus.OK, "application/json; charset=utf-8", render_json(payload))
            return

        if path == "/api/health":
            payload = {"status": "ok", "skills": len(load_skills())}
            self.respond(HTTPStatus.OK, "application/json; charset=utf-8", render_json(payload))
            return

        if path == "/api/discover-skills":
            try:
                search_query = query.get("q", [""])[0]
                payload = discover_skills(search_query)
                self.respond(HTTPStatus.OK, "application/json; charset=utf-8", render_json(payload))
            except RuntimeError as error:
                self.respond(
                    HTTPStatus.BAD_GATEWAY,
                    "application/json; charset=utf-8",
                    render_json({"ok": False, "message": str(error)}),
                )
            return

        if path.startswith("/skill/"):
            slug = urllib.parse.unquote(path.removeprefix("/skill/"))
            match = next((skill for skill in load_skills() if skill.slug == slug), None)
            if not match:
                self.respond(HTTPStatus.NOT_FOUND, "text/html; charset=utf-8", render_layout("Not Found", "<main class='empty-state'><h1>Skill not found</h1></main>"))
                return
            self.respond(HTTPStatus.OK, "text/html; charset=utf-8", render_detail(match))
            return

        if path.startswith("/static/"):
            asset_path = APP_DIR / path.lstrip("/")
            if asset_path.is_file():
                content_type = "text/plain; charset=utf-8"
                if asset_path.suffix == ".css":
                    content_type = "text/css; charset=utf-8"
                elif asset_path.suffix == ".js":
                    content_type = "application/javascript; charset=utf-8"
                self.respond(HTTPStatus.OK, content_type, asset_path.read_bytes())
                return

        self.respond(HTTPStatus.NOT_FOUND, "text/html; charset=utf-8", render_layout("Not Found", "<main class='empty-state'><h1>Page not found</h1></main>"))

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path != "/api/install-skill":
            self.respond(HTTPStatus.NOT_FOUND, "application/json; charset=utf-8", render_json({"ok": False, "message": "Not found"}))
            return

        try:
            payload = self.read_json_body()
            package = str(payload.get("package", ""))
            result = install_skill(package)
            self.respond(HTTPStatus.OK, "application/json; charset=utf-8", render_json(result))
        except ValueError as error:
            self.respond(HTTPStatus.BAD_REQUEST, "application/json; charset=utf-8", render_json({"ok": False, "message": str(error)}))
        except RuntimeError as error:
            self.respond(HTTPStatus.BAD_GATEWAY, "application/json; charset=utf-8", render_json({"ok": False, "message": str(error)}))
        except json.JSONDecodeError:
            self.respond(HTTPStatus.BAD_REQUEST, "application/json; charset=utf-8", render_json({"ok": False, "message": "Invalid JSON body."}))

    def log_message(self, format: str, *args) -> None:
        message = "%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args)
        sys.stderr.write(message)

    def read_json_body(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        payload = json.loads(body or "{}")
        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object.")
        return payload

    def respond(self, status: HTTPStatus, content_type: str, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), SkillAtlasHandler)
    print(textwrap.dedent(
        f"""
        Skill Atlas is running.
        URL: http://{args.host}:{args.port}
        Scan roots:
        """
    ).strip(), flush=True)
    for label, root in ROOT_SPECS:
        state = "exists" if root.exists() else "missing"
        print(f"  - {label}: {root} [{state}]", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Skill Atlas...", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
