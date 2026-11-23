"""Functional contracts of the generated site, the issue templates and the
issue-payload parsers (stdlib unittest, Python 3.10+).

Run: python -B -m unittest tools/test_site_contracts.py

The site is rendered in memory through tools/build.py, so a stale docs/index.html
cannot hide a template regression. Assertions cover behaviour that must survive a
visual redesign: element ids and their aria relationships, form limits that have
to agree with the server-side parsers, issue-template links that work without
JavaScript, group and category options, unique ids, news anchors and the archive
hook, the mark storage keys and the five-day NEW window. Copy, layout, CSS and
class names are deliberately not asserted.

Not covered here: the page's JavaScript, which assembles the prefilled issue
bodies at runtime. These tests check the static hrefs and prove that the parsers
accept the bodies those serializers are built to emit; only a browser can prove
the generated hrefs themselves. The two URL-normalisation order guards below
match the page's JavaScript source: they are source contracts, not runtime
proof, and the browser owner still exercises the real generated hrefs.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import unittest
import urllib.parse
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
TEMPLATE_DIR = ROOT / ".github" / "ISSUE_TEMPLATE"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build = load("gxr_build_contracts", "build.py")
issue_payload = load("gxr_issue_payload_contracts", "issue-payload.py")

REPO_SLUG = build.REPO_URL.split("github.com/", 1)[1]


# ---------------------------------------------------------------------------
# a small read-only DOM over the generated page
# ---------------------------------------------------------------------------

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "texts")

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.parent = parent
        self.texts = []

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()

    def __repr__(self):
        return f"<{self.tag} {self.attrs.get('id') or self.attrs.get('class') or ''}>"


class Doc(HTMLParser):
    """Builds a tolerant tree; script/style bodies stay inert text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {}, None)
        self.stack = [self.root]
        self.by_id = {}
        self.duplicate_ids = []

    def _open(self, tag, attrs, closed):
        node = Node(
            tag,
            {k.lower(): (v if v is not None else "") for k, v in attrs},
            self.stack[-1],
        )
        self.stack[-1].children.append(node)
        ident = node.attrs.get("id")
        if ident:
            if ident in self.by_id:
                self.duplicate_ids.append(ident)
            else:
                self.by_id[ident] = node
        if not closed and tag not in VOID:
            self.stack.append(node)
        return node

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, False)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, True)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].texts.append(data)


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def text_of(node):
    parts = []

    def rec(n):
        parts.extend(n.texts)
        for c in n.children:
            rec(c)

    rec(node)
    return " ".join("".join(parts).split())


def template_meta(filename):
    """Front matter of an issue template as a dict."""
    text = (TEMPLATE_DIR / filename).read_text(encoding="utf-8")
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        raise AssertionError(f"{filename}: no front matter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"')
    return meta


def template_headings(filename):
    text = (TEMPLATE_DIR / filename).read_text(encoding="utf-8")
    body = re.sub(r"\A---.*?\n---\n", "", text, flags=re.S)
    return [h.strip().lower() for h in re.findall(r"^#{2,4}\s+(.+?)\s*$", body, re.M)]


def run_issue(args, body, number="12", user="tester"):
    env = dict(
        os.environ,
        ISSUE_BODY=body,
        ISSUE_NUMBER=number,
        ISSUE_USER=user,
        PYTHONDONTWRITEBYTECODE="1",
    )
    return subprocess.run(
        [sys.executable, "-B", str(TOOLS / "issue-payload.py"), *args],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )


def parsed(res, testcase):
    testcase.assertEqual(res.returncode, 0, res.stderr)
    return json.loads(res.stdout)


# Bodies in the shape the page's dialogs emit; the dialog serializers are JS,
# so these are the shapes their parsers must keep accepting.
def repo_body(url, group, about=None):
    body = f"### Repo URL\n{url}\n\n### Group\n{group}\n"
    if about is not None:
        body += f"\n### About\n{about}\n"
    return body


def news_body(title, text, summary=None, kind=None, repo=None, link=None, day=None):
    body = f"### Title\n{title}\n\n### News\n{text}\n"
    if summary is not None:
        body += f"\n### Summary\n{summary}\n"
    if kind is not None:
        body += f"\n### Category\n{kind}\n"
    if repo is not None:
        body += f"\n### Related repo\n{repo}\n"
    if link is not None:
        body += f"\n### Link\n{link}\n"
    if day is not None:
        body += f"\n### Date\n{day}\n"
    return body


def template_body(filename):
    """The body GitHub pre-fills from a template, without its front matter."""
    text = (TEMPLATE_DIR / filename).read_text(encoding="utf-8")
    return re.sub(r"\A---\r?\n.*?\r?\n---\r?\n", "", text, flags=re.S)


def fill_template(filename, values):
    """Fill `### Heading` sections, keeping every comment and replacing examples."""
    parts = re.split(r"(?m)^(#{2,4}\s+.+)$", template_body(filename))
    out = [parts[0]]
    for heading, content in zip(parts[1::2], parts[2::2]):
        value = values.get(heading.lstrip("#").strip().lower())
        if value:
            kept = []
            in_comment = False
            for line in content.splitlines():
                stripped = line.strip()
                if in_comment:
                    kept.append(line)
                    in_comment = "-->" not in stripped
                elif stripped.startswith("<!--"):
                    kept.append(line)
                    in_comment = "-->" not in stripped
                elif not stripped:
                    kept.append(line)
                # any other line is template example text and is replaced
            content = "\n".join(kept).rstrip("\n") + f"\n\n{value}\n\n"
        out.extend([heading, content])
    return "".join(out)


# Page-JS source contracts. Minimal on purpose: brace matching plus a marker
# that identifies which same-named function is meant, not a JS parser.
JS_TRIM_SLASH = re.compile(r"while \(([A-Za-z_$][\w$]*)\.slice\(-1\) === '/'\)")
JS_STRIP_DOT_GIT = re.compile(r"([A-Za-z_$][\w$]*)\.slice\(-4\) === '\.git'")


def js_function_body(text, name, marker):
    """Body of the named function whose text contains `marker`."""
    pattern = re.compile(r"function\s+" + re.escape(name) + r"\s*\(")
    for match in pattern.finditer(text):
        brace = text.find("{", match.end())
        if brace == -1:
            continue
        depth = 0
        for i in range(brace, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    body = text[match.start():i + 1]
                    if marker in body:
                        return body
                    break
    raise AssertionError(
        f"no function {name}(...) using {marker!r} in the rendered page"
    )


# ---------------------------------------------------------------------------
# the rendered site
# ---------------------------------------------------------------------------


class SiteContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = build.load_catalog()
        cls.changelog = build.load_changelog()
        cls.modules = build.load_modules(cls.cat)
        cls.news = build.load_news()
        cls.page = build.render_site(cls.cat, cls.changelog, cls.modules, cls.news)
        cls.doc = Doc()
        cls.doc.feed(cls.page)
        cls.group_ids = [g["id"] for g in cls.cat["groups"]]

    def node(self, ident):
        self.assertIn(ident, self.doc.by_id, f"missing element #{ident}")
        return self.doc.by_id[ident]

    def test_no_unsubstituted_placeholders(self):
        leftovers = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]*__", self.page)))
        self.assertEqual(leftovers, [], "template placeholders left in the page")

    def test_ids_are_unique(self):
        self.assertEqual(self.doc.duplicate_ids, [], "duplicate id attributes")

    def test_aria_id_references_resolve(self):
        missing = []
        for node in walk(self.doc.root):
            for attr in ("aria-labelledby", "aria-controls", "aria-describedby", "aria-owns"):
                for ref in node.attrs.get(attr, "").split():
                    if ref not in self.doc.by_id:
                        missing.append(f"{node.tag}[{node.attrs.get('id', '?')}] {attr}={ref}")
        self.assertEqual(missing, [])

    def test_labels_point_at_their_control(self):
        problems = []
        for node in walk(self.doc.root):
            if node.tag != "label":
                continue
            target = node.attrs.get("for")
            if not target:
                problems.append(f"label without for: {text_of(node)[:40]!r}")
            elif target not in self.doc.by_id:
                problems.append(f"label for={target} has no target")
            elif self.doc.by_id[target].tag not in ("input", "select", "textarea"):
                problems.append(f"label for={target} targets <{self.doc.by_id[target].tag}>")
        self.assertEqual(problems, [])

    def test_tabs_and_panels_are_paired(self):
        tabs = [n for n in walk(self.doc.root) if n.attrs.get("role") == "tab"]
        self.assertGreaterEqual(len(tabs), 4)
        for tab in tabs:
            panel = self.node(tab.attrs.get("aria-controls", ""))
            self.assertEqual(panel.attrs.get("role"), "tabpanel", tab.attrs.get("id"))
            self.assertEqual(panel.attrs.get("aria-labelledby"), tab.attrs.get("id"))

    def test_dialogs_are_labelled_and_controllable(self):
        for dialog_id, heading_id in (
            ("post-news-dialog", "post-news-title"),
            ("add-repo-dialog", "add-repo-title"),
        ):
            dialog = self.node(dialog_id)
            self.assertEqual(dialog.tag, "dialog")
            self.assertEqual(dialog.attrs.get("aria-labelledby"), heading_id)
            self.assertTrue(text_of(self.node(heading_id)), f"{dialog_id} heading is empty")

            controls = [n for n in walk(dialog) if n.tag in ("input", "select", "textarea")]
            self.assertTrue(controls, dialog_id)
            for control in controls:
                control_id = control.attrs.get("id")
                self.assertTrue(control_id, f"{dialog_id}: control without id")
                labelled = any(
                    n.tag == "label" and n.attrs.get("for") == control_id
                    for n in walk(dialog)
                )
                self.assertTrue(labelled, f"{control_id} has no label[for]")

            closes = [
                n for n in walk(dialog)
                if n.tag == "button" and "Close" in n.attrs.get("aria-label", "")
            ]
            self.assertEqual(len(closes), 1, f"{dialog_id}: one close button with aria-label")

            submits = [n for n in walk(dialog) if n.tag == "a" and n.has_class("add-submit")]
            self.assertEqual(len(submits), 1, f"{dialog_id}: one submit anchor")
            self.assertEqual(submits[0].attrs.get("target"), "_blank")
            self.assertIn("noopener", submits[0].attrs.get("rel", ""))

    def test_suggest_button_points_at_its_dialog(self):
        button = self.node("add-repo-btn")
        self.assertEqual(button.attrs.get("aria-haspopup"), "dialog")
        self.assertEqual(button.attrs.get("aria-controls"), "add-repo-dialog")

    def test_issue_links_use_a_real_template_without_js(self):
        links = [
            n for n in walk(self.doc.root)
            if n.tag == "a" and "/issues/new" in n.attrs.get("href", "")
        ]
        self.assertGreaterEqual(len(links), 2, "both call-to-action issue links")
        for anchor in links:
            parts = urllib.parse.urlsplit(anchor.attrs["href"])
            self.assertEqual(parts.scheme, "https")
            self.assertEqual(parts.netloc, "github.com")
            self.assertEqual(parts.path, f"/{REPO_SLUG}/issues/new")
            query = urllib.parse.parse_qs(parts.query)
            template = query.get("template", [""])[0]
            self.assertTrue(template, f"issue link without template: {anchor.attrs['href']}")
            self.assertTrue((TEMPLATE_DIR / template).is_file(), template)
            meta = template_meta(template)
            self.assertEqual(query.get("labels", [""])[0], meta.get("labels"), template)

        add_template = urllib.parse.parse_qs(
            urllib.parse.urlsplit(self.node("add-repo-btn").attrs["href"]).query
        )["template"][0]
        news_template = urllib.parse.parse_qs(
            urllib.parse.urlsplit(self.node("post-news-btn").attrs["href"]).query
        )["template"][0]
        self.assertEqual(add_template, "add-repo.md")
        self.assertEqual(news_template, "add-news.md")

    def test_no_script_urls(self):
        bad = [
            n.attrs.get("href")
            for n in walk(self.doc.root)
            if n.tag == "a" and n.attrs.get("href", "").strip().lower().startswith("javascript:")
        ]
        self.assertEqual(bad, [])

    def test_blank_target_links_are_noopener(self):
        bad = [
            n.attrs.get("href")
            for n in walk(self.doc.root)
            if n.tag == "a" and n.attrs.get("target") == "_blank"
            and "noopener" not in n.attrs.get("rel", "")
        ]
        self.assertEqual(bad, [])

    def test_form_limits_match_the_parsers(self):
        self.assertEqual(
            self.node("post-news-title-input").attrs.get("maxlength"),
            str(build.NEWS_MAX_TITLE),
        )
        self.assertEqual(build.NEWS_MAX_TITLE, issue_payload.NEWS_MAX_TITLE)
        self.assertEqual(
            self.node("post-news-summary").attrs.get("maxlength"),
            str(build.NEWS_MAX_SUMMARY),
        )
        self.assertEqual(build.NEWS_MAX_SUMMARY, issue_payload.NEWS_MAX_SUMMARY)
        # 160 is the catalog `about` limit enforced by build.validate(); see
        # CatalogLimits.test_about_limit_matches_the_form below.
        self.assertEqual(self.node("add-repo-about").attrs.get("maxlength"), "160")
        self.assertEqual(self.node("add-repo-url").attrs.get("type"), "url")
        self.assertEqual(self.node("post-news-link-url").attrs.get("type"), "url")
        self.assertEqual(self.node("post-news-body").tag, "textarea")

    def test_group_options_match_the_catalog(self):
        select = self.node("add-repo-group")
        options = [n for n in walk(select) if n.tag == "option"]
        self.assertEqual([o.attrs.get("value") for o in options], self.group_ids)
        for option, group in zip(options, self.cat["groups"]):
            self.assertTrue(
                text_of(option).endswith(group["title"]),
                f"{option.attrs['value']}: option text lacks the group title",
            )

    def test_group_chips_and_sections_match_the_catalog(self):
        chips = [
            n for n in walk(self.doc.root)
            if n.tag == "button" and n.has_class("chip") and "data-group" in n.attrs
        ]
        self.assertEqual([c.attrs["data-group"] for c in chips], ["all"] + self.group_ids)
        for group_id in self.group_ids:
            self.assertRegex(group_id, r"^[a-z0-9][a-z0-9-]*$")
            self.assertIn(group_id, self.doc.by_id, "group section anchor")
            self.assertEqual(self.node(group_id).tag, "section")

    def test_category_options_match_the_generators(self):
        select = self.node("post-news-kind")
        values = [n.attrs.get("value") for n in walk(select) if n.tag == "option"]
        self.assertEqual(sorted(values), sorted(build.NEWS_KINDS))
        self.assertEqual(set(build.NEWS_KINDS), set(issue_payload.NEWS_KINDS))
        for value in values:
            self.assertIn(issue_payload.news_kind(value), build.NEWS_KINDS)
        selected = [
            n.attrs.get("value") for n in walk(select)
            if n.tag == "option" and "selected" in n.attrs
        ]
        self.assertEqual(selected, ["community"])
        self.assertEqual(issue_payload.news_kind(""), "community")

    def test_mark_flags_and_storage_keys(self):
        self.assertIn("gxrforge.marks", self.page, "localStorage key")
        self.assertIn("gxrforge_marks", self.page, "cookie key")
        flags = [
            n.attrs.get("data-flag") for n in walk(self.doc.root)
            if n.tag == "button" and "data-flag" in n.attrs
        ]
        self.assertEqual(sorted(set(flags)), ["done", "fav"])
        for node in walk(self.doc.root):
            if node.tag == "button" and "data-flag" in node.attrs:
                self.assertIn(node.attrs.get("aria-pressed"), {"true", "false"})

    def test_url_normalisation_trims_slashes_before_dropping_dot_git(self):
        """Source contract for two page functions; not runtime proof.

        `https://github.com/o/n.git/`, `.../n/` and `.../n.git` must end up as
        `o/n`. This only pins the order in the source: the browser owner still
        exercises the real generated hrefs, and the catalog / proposal duplicate
        lookups that `norm()` feeds.
        """
        for name, marker in (("issueHref", "urlInput.value"), ("norm", "toLowerCase")):
            body = js_function_body(self.page, name, marker)
            slash = JS_TRIM_SLASH.search(body)
            self.assertIsNotNone(slash, f"{name}: trailing-slash trim loop missing")
            git = JS_STRIP_DOT_GIT.search(body)
            self.assertIsNotNone(git, f"{name}: .git strip missing")
            self.assertLess(
                slash.start(), git.start(),
                f"{name}: trim trailing slashes before dropping .git",
            )
            self.assertEqual(slash.group(1), git.group(1), f"{name}: same variable")
            self.assertEqual(body.count(".git"), 1, f"{name}: one .git strip")

    def test_new_badge_hooks(self):
        self.assertIn("dataset.added", self.page, "NEW badge reads data-added")
        self.assertRegex(
            self.page,
            r"5 \* 24 \* 60 \* 60 \* 1000",
            "NEW badge window is five days",
        )

    def test_news_archive_is_fetched_from_news_json(self):
        self.assertIn("news.json", self.page)


class CatalogLimits(unittest.TestCase):
    def cat(self, about):
        return {
            "groups": [
                {
                    "id": "tools",
                    "title": "Tools",
                    "icon": "T",
                    "hue": "#f97316",
                    "blurb": "Tooling.",
                    "repos": [
                        {
                            "repo": "o/n",
                            "url": "https://github.com/o/n",
                            "about": about,
                        }
                    ],
                }
            ]
        }

    def test_about_limit_matches_the_form(self):
        errors, _ = build.validate(self.cat("a" * 160))
        self.assertEqual(errors, [])
        errors, _ = build.validate(self.cat("a" * 161))
        self.assertTrue(any("about too long" in e for e in errors), errors)


class NewWindow(unittest.TestCase):
    def cat(self, dates):
        repos = []
        for i, added in enumerate(dates):
            repo = {"repo": f"o/n{i}", "url": f"https://github.com/o/n{i}", "about": "x"}
            if added is not None:
                repo["added"] = added
            repos.append(repo)
        return {
            "groups": [
                {"id": "tools", "title": "Tools", "icon": "T", "hue": "#0af",
                 "blurb": "Tooling.", "repos": repos}
            ]
        }

    def test_count_new_is_five_days(self):
        today = date.today()
        dates = [
            today.isoformat(),
            (today - timedelta(days=4)).isoformat(),
            (today - timedelta(days=5)).isoformat(),
            (today - timedelta(days=30)).isoformat(),
            None,
            "not-a-date",
        ]
        self.assertEqual(build.count_new(self.cat(dates)), 2)
        self.assertEqual(build.count_new(self.cat(dates), days=5), 2)

    def test_cards_carry_data_added_only_when_dated(self):
        today = date.today().isoformat()
        rendered = build.render_sections(self.cat([today, None]))
        self.assertIn(f'data-added="{today}"', rendered)
        self.assertEqual(rendered.count("data-added="), 1)

    def test_new_chip_starts_at_the_build_count(self):
        today = date.today().isoformat()
        chips = build.render_status_chips(self.cat([today, None]))
        self.assertIn(f'id="cnt-new">{build.count_new(self.cat([today, None]))}</b>', chips)


# ---------------------------------------------------------------------------
# repo issues through the real parser
# ---------------------------------------------------------------------------


class RepoIssuePayload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
        cls.groups = [g["id"] for g in catalog["groups"]]
        cls.group = cls.groups[0]

    def payload(self, body):
        return parsed(run_issue([], body), self)

    def test_site_dialog_shape_round_trips(self):
        data = self.payload(repo_body("https://github.com/owner/name", self.group))
        self.assertEqual(data["repo"], "https://github.com/owner/name")
        self.assertEqual(data["group"], self.group)
        self.assertIsNone(data["about"])
        self.assertEqual(data["issue"], 12)

    def test_about_is_carried_when_present(self):
        data = self.payload(
            repo_body("https://github.com/owner/name", self.group, "One short line.")
        )
        self.assertEqual(data["about"], "One short line.")

    def test_url_is_normalised(self):
        for raw in (
            "https://github.com/owner/name.git",
            "https://github.com/owner/name/",
            "https://github.com/owner/name.git/",
        ):
            data = self.payload(repo_body(raw, self.group))
            self.assertEqual(data["repo"], "https://github.com/owner/name", raw)

    def test_unicode_quotes_and_ampersands_survive(self):
        about = 'Ünïcode ✓ & "quotes" and <tags>'
        data = self.payload(repo_body("https://github.com/owner/name", self.group, about))
        self.assertEqual(data["about"], about)

    def test_group_is_case_insensitive(self):
        data = self.payload(repo_body("https://github.com/o/n", self.group.upper()))
        self.assertEqual(data["group"], self.group)

    def test_about_never_exceeds_the_form_limit(self):
        for length in (160, 161, 400):
            data = self.payload(
                repo_body("https://github.com/o/n", self.group, "b" * length)
            )
            self.assertLessEqual(len(data["about"]), 160, length)
        long_about = self.payload(
            repo_body("https://github.com/o/n", self.group, "b" * 400)
        )["about"]
        self.assertTrue(long_about.endswith("\u2026"))

    def test_invalid_bodies_fail_loudly(self):
        res = run_issue([], "### Repo URL\n\nhttps://gitlab.com/o/n\n\n### Group\n\ntools\n")
        self.assertEqual(res.returncode, 1)
        self.assertIn("no GitHub repository URL", res.stderr)

        res = run_issue([], repo_body("https://github.com/o/n", "no-such-group"))
        self.assertEqual(res.returncode, 1)
        for group in self.groups:
            self.assertIn(group, res.stderr, "the error lists the real group ids")
        self.assertNotIn("repo must be", res.stderr)

    def test_template_headings_reach_the_parser(self):
        headings = template_headings("add-repo.md")
        self.assertEqual(
            sorted(headings), ["about (optional)", "group", "repo url"]
        )
        body = (
            "### Repo URL\n\nhttps://github.com/owner/name\n\n"
            "### Group\n\n" + self.group + "\n"
        )
        self.assertEqual(self.payload(body)["group"], self.group)

    def test_filled_template_keeps_its_comments_and_carries_every_field(self):
        template = template_body("add-repo.md")
        body = fill_template(
            "add-repo.md",
            {
                "repo url": "https://github.com/owner/example",
                "group": self.group,
                "about (optional)": "One short factual line.",
            },
        )
        # GitHub keeps the template's instructional comments in the issue body.
        self.assertGreater(template.count("<!--"), 0)
        self.assertEqual(body.count("<!--"), template.count("<!--"))

        data = self.payload(body)
        self.assertEqual(data["repo"], "https://github.com/owner/example")
        self.assertEqual(data["group"], self.group)
        self.assertEqual(data["about"], "One short factual line.")

    def test_filled_template_without_a_description_leaves_about_empty(self):
        body = fill_template(
            "add-repo.md",
            {"repo url": "https://github.com/owner/example", "group": self.group},
        )
        # the About section holds only its comment, which is not content
        self.assertIn("<!-- One short factual line", body)
        data = self.payload(body)
        self.assertIsNone(data["about"])
        self.assertEqual(data["group"], self.group)

    def test_about_optional_heading_is_read(self):
        data = self.payload(
            "### Repo URL\n\nhttps://github.com/owner/name\n\n"
            "### Group\n\n" + self.group + "\n\n"
            "### About (optional)\n\nA line.\n"
        )
        self.assertEqual(data["about"], "A line.")

    def test_notes_heading_still_reads_as_about(self):
        data = self.payload(
            "### Repo URL\n\nhttps://github.com/owner/name\n\n"
            "### Group\n\n" + self.group + "\n\n"
            "### Notes\n\nOlder heading.\n"
        )
        self.assertEqual(data["about"], "Older heading.")

    def test_about_wins_over_notes(self):
        data = self.payload(
            "### Repo URL\n\nhttps://github.com/owner/name\n\n"
            "### Group\n\n" + self.group + "\n\n"
            "### Notes\n\nOlder heading.\n\n### About\n\nThe card line.\n"
        )
        self.assertEqual(data["about"], "The card line.")

    def test_about_wins_even_when_the_optional_heading_comes_first(self):
        data = self.payload(
            "### Repo URL\n\nhttps://github.com/owner/name\n\n"
            "### Group\n\n" + self.group + "\n\n"
            "### About (optional)\n\nOptional heading text.\n\n"
            "### About\n\nThe card line.\n"
        )
        self.assertEqual(data["about"], "The card line.")

    def test_arbitrary_parenthesized_suffixes_are_not_aliases(self):
        for heading in ("About (bogus)", "About (optional) text", "Notes (anything)"):
            data = self.payload(
                "### Repo URL\n\nhttps://github.com/owner/name\n\n"
                "### Group\n\n" + self.group + "\n\n"
                f"### {heading}\n\nNot a supported heading.\n"
            )
            self.assertIsNone(data["about"], heading)

    def test_template_group_comment_does_not_poison_the_group(self):
        data = self.payload(
            "### Repo URL\n\nhttps://github.com/owner/name\n\n"
            "### Group\n\n<!-- one of: tools, games -->\n\n" + self.group + "\n"
        )
        self.assertEqual(data["group"], self.group)

    def test_comment_only_group_still_errors(self):
        body = fill_template(
            "add-repo.md", {"repo url": "https://github.com/owner/example"}
        )
        res = run_issue([], body)
        self.assertEqual(res.returncode, 1)
        self.assertIn("group must be one of", res.stderr)

    def test_invalid_group_with_template_comments_still_errors(self):
        body = fill_template(
            "add-repo.md",
            {"repo url": "https://github.com/owner/example", "group": "no-such-group"},
        )
        res = run_issue([], body)
        self.assertEqual(res.returncode, 1)
        self.assertIn("group must be one of", res.stderr)
        for group in self.groups:
            self.assertIn(group, res.stderr)


# ---------------------------------------------------------------------------
# news issues through the real parser
# ---------------------------------------------------------------------------


class NewsIssuePayload(unittest.TestCase):
    def payload(self, body):
        return parsed(run_issue(["--news"], body), self)

    def test_full_issue_round_trips(self):
        data = self.payload(
            news_body(
                "A post \u2014 with Unicode \u2713",
                "First para with & and \"quotes\".\n\nSecond: `code` and **bold**.",
                summary="One line.",
                kind="site",
                repo="https://github.com/owner/name",
                link="Release notes | https://example.com/notes?a=1&b=2",
            )
        )
        self.assertEqual(data["title"], "A post \u2014 with Unicode \u2713")
        self.assertEqual(
            data["body"],
            ["First para with & and \"quotes\".", "Second: `code` and **bold**."],
        )
        self.assertEqual(data["summary"], "One line.")
        self.assertEqual(data["kind"], "site")
        self.assertEqual(data["repo"], "owner/name")
        self.assertEqual(
            data["links"],
            [{"label": "Release notes", "url": "https://example.com/notes?a=1&b=2"}],
        )
        self.assertEqual(data["author"], "tester")
        self.assertEqual(data["issue"], 12)

    def test_defaults_for_the_optional_fields(self):
        data = self.payload(news_body("T", "Body."))
        self.assertIsNone(data["summary"])
        self.assertEqual(data["kind"], "community")
        self.assertIsNone(data["repo"])
        self.assertEqual(data["links"], [])
        self.assertEqual(data["date"], date.today().isoformat())

    def test_blank_optional_sections_are_defaults(self):
        body = news_body("T", "Body.") + (
            "\n### Summary\n\n### Category\n\n### Related repo\n\n### Link\n"
        )
        data = self.payload(body)
        self.assertIsNone(data["summary"])
        self.assertEqual(data["kind"], "community")
        self.assertIsNone(data["repo"])
        self.assertEqual(data["links"], [])

    def test_paragraphs_and_list_lines_are_preserved(self):
        data = self.payload(news_body("T", "Intro\n- a\n- b\n\nSecond para."))
        self.assertEqual(data["body"], ["Intro\n- a\n- b", "Second para."])

    def test_bare_link_gets_the_default_label(self):
        data = self.payload(news_body("T", "B.", link="https://example.com/x"))
        self.assertEqual(data["links"], [{"label": "Link", "url": "https://example.com/x"}])

    def test_related_repo_accepts_url_and_bare_name(self):
        for raw in ("https://github.com/O/N.git", "O/N", "`O/N`"):
            data = self.payload(news_body("T", "B.", repo=raw))
            self.assertEqual(data["repo"], "O/N", raw)

    def test_category_aliases(self):
        self.assertEqual(self.payload(news_body("T", "B.", kind="site update"))["kind"], "site")
        for kind in issue_payload.NEWS_KINDS:
            self.assertEqual(self.payload(news_body("T", "B.", kind=kind))["kind"], kind)

    def test_explicit_and_rejected_dates(self):
        self.assertEqual(
            self.payload(news_body("T", "B.", day="2026-01-05"))["date"], "2026-01-05"
        )
        future = (date.today() + timedelta(days=1)).isoformat()
        res = run_issue(["--news"], news_body("T", "B.", day=future))
        self.assertEqual(res.returncode, 1)
        self.assertIn("in the future", res.stderr)
        res = run_issue(["--news"], news_body("T", "B.", day="05/01/2026"))
        self.assertEqual(res.returncode, 1)
        self.assertIn("YYYY-MM-DD", res.stderr)

    def test_invalid_bodies_fail_loudly(self):
        cases = {
            "no title": "### News\n\nB.\n",
            "no body": "### Title\n\nT\n",
            "unknown category": news_body("T", "B.", kind="news"),
            "nine paragraphs": news_body("T", "\n\n".join(f"P{i}." for i in range(9))),
            "long title": news_body("T" * 121, "B."),
            "long link label": news_body(
                "T", "B.", link="L" * 61 + " | https://example.com/x"
            ),
            "non-https link": news_body("T", "B.", link="ftp://example.com/x"),
            "junk repo": news_body("T", "B.", repo="not a repo"),
        }
        for name, body in cases.items():
            res = run_issue(["--news"], body)
            self.assertEqual(res.returncode, 1, f"{name} should be rejected")
            self.assertTrue(res.stderr.strip(), f"{name}: error message on stderr")

    def test_comment_only_optional_sections_stay_empty(self):
        body = (
            "### Title\n\nT\n\n### News\n\n<!-- note -->\n\nBody.\n\n"
            "### Summary\n\n<!-- One line shown under the headline, 200 characters max. -->\n"
        )
        data = self.payload(body)
        self.assertIsNone(data["summary"])
        self.assertEqual(data["kind"], "community")
        self.assertIsNone(data["repo"])

    def test_template_headings_are_all_understood(self):
        headings = template_headings("add-news.md")
        self.assertEqual(
            sorted(headings),
            [
                "category (optional)",
                "link (optional)",
                "news",
                "related repo (optional)",
                "summary (optional)",
                "title",
            ],
        )
        body = (
            "<!-- template comment -->\n\n### Title\n\nA title\n\n"
            "### News\n\n<!-- note -->\n\nA body line.\n\n"
            "### Summary (optional)\n\nA summary.\n\n"
            "### Category (optional)\n\n<!-- one of: ... -->\n\nguide\n\n"
            "### Related repo (optional)\n\nowner/name\n"
        )
        data = self.payload(body)
        self.assertEqual(data["title"], "A title")
        self.assertEqual(data["body"], ["A body line."])
        self.assertEqual(data["summary"], "A summary.")
        self.assertEqual(data["kind"], "guide")
        self.assertEqual(data["repo"], "owner/name")


# ---------------------------------------------------------------------------
# news rendering: anchors, archive and escaping
# ---------------------------------------------------------------------------

NEWS_CAT = {
    "groups": [
        {
            "id": "tools",
            "title": "Tools",
            "icon": "T",
            "hue": "#0af",
            "blurb": "Tooling.",
            "repos": [
                {"repo": "owner/name", "url": "https://github.com/owner/name", "about": "x"}
            ],
        }
    ]
}


def news_fixture(count):
    entries = []
    base = date(2026, 1, 20)
    for i in range(count):
        day = (base - timedelta(days=i)).isoformat()
        entries.append(
            {
                "_file": f"{day}-post-{i}.json",
                "date": day,
                "title": f"Post {i}",
                "body": [f"Body {i}."],
                "kind": "community",
            }
        )
    return {"entries": entries}


class NewsArchive(unittest.TestCase):
    def test_first_page_is_bounded_and_points_at_the_archive(self):
        page = build.render_news_view(news_fixture(9), NEWS_CAT)
        self.assertEqual(page.count('class="news-item"'), build.NEWS_PAGE_SIZE)
        self.assertIn(f'data-page-size="{build.NEWS_PAGE_SIZE}"', page)
        self.assertIn('data-total="9"', page)
        self.assertIn('id="news-more"', page)
        self.assertIn('aria-controls="news-feed"', page)
        self.assertIn('href="news.json"', page, "no-JS route to the archive")

    def test_no_more_button_when_everything_fits(self):
        page = build.render_news_view(news_fixture(build.NEWS_PAGE_SIZE), NEWS_CAT)
        self.assertEqual(page.count('class="news-item"'), build.NEWS_PAGE_SIZE)
        self.assertNotIn('id="news-more"', page)

    def test_empty_feed(self):
        page = build.render_news_view({"entries": []}, NEWS_CAT)
        self.assertIn("No news yet", page)
        self.assertNotIn('class="news-item"', page)

    def test_item_ids_anchor_and_kind(self):
        entry = news_fixture(1)["entries"][0]
        item = build.render_news_item(entry, {})
        stem = entry["_file"][:-5]
        self.assertIn(f'id="news-{stem}"', item)
        self.assertIn(f'href="#news-{stem}"', item)
        self.assertIn('aria-label="Link to this post"', item)
        self.assertIn('data-kind="community"', item)
        self.assertIn(build.NEWS_KIND_LABEL["community"], item)

    def test_archive_carries_every_post_with_the_same_ids(self):
        news = news_fixture(9)
        page = build.render_news_view(news, NEWS_CAT)
        payload = json.loads(build.render_news_index(news, NEWS_CAT))
        self.assertEqual(payload["pageSize"], build.NEWS_PAGE_SIZE)
        self.assertEqual(payload["total"], 9)
        self.assertEqual(payload["updated"], news["entries"][0]["date"])
        stems = [e["_file"][:-5] for e in news["entries"]]
        self.assertEqual([i["id"] for i in payload["items"]], [f"news-{s}" for s in stems])
        for item in payload["items"]:
            self.assertIn(f'id="{item["id"]}"', item["html"])
        # a post beyond the first page keeps its deep link in the archive
        oldest = f'id="news-{stems[-1]}"'
        self.assertNotIn(oldest, page)
        self.assertEqual(payload["items"][-1]["id"], f"news-{stems[-1]}")
        self.assertIn(oldest, payload["items"][-1]["html"])

    def test_repo_and_links_render_only_where_allowed(self):
        entry = news_fixture(1)["entries"][0]
        entry.update(
            repo="owner/name",
            links=[{"label": "Notes", "url": "https://example.com/n?a=1&b=2"}],
        )
        item = build.render_news_item(
            entry, {"owner/name": (NEWS_CAT["groups"][0], NEWS_CAT["groups"][0]["repos"][0])}
        )
        self.assertIn('href="https://github.com/owner/name"', item)
        self.assertIn('class="news-link"', item)
        self.assertIn("&amp;b=2", item)
        self.assertNotIn("<script", item)

        entry.pop("repo")
        item = build.render_news_item(entry, {})
        self.assertNotIn('class="news-repo"', item)

    def test_hostile_text_is_escaped(self):
        entry = news_fixture(1)["entries"][0]
        entry.update(
            title="<script>alert(1)</script>",
            summary='a & b "c"',
            body=["<img src=x onerror=1> & **bold**"],
        )
        item = build.render_news_item(entry, {})
        self.assertNotIn("<script", item)
        self.assertNotIn("<img", item)
        self.assertIn("&lt;script&gt;", item)
        self.assertIn("&amp;", item)
        self.assertIn("<strong>bold</strong>", item)


if __name__ == "__main__":
    unittest.main()
