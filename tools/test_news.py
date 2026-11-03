"""Regression tests for news Markdown list support (stdlib unittest).

Run: python -m unittest tools/test_news.py   (or python tools/test_news.py)
Covers: issue parser -> CLI normalization -> validation -> renderer, for both
the inline page and the docs/news.json archive path.
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build = load("gxr_build_t", "build.py")
add_news = load("gxr_add_news_t", "add-news.py")
issue_payload = load("gxr_issue_payload_t", "issue-payload.py")

ISSUE_BODY = """### Title

List post

### Category

community

### News

Intro line that explains things.
- first *item*
* second <b>item</b>
+ third `code`

Steps:
1. one
2) two
Closing line after the list.

Plain second paragraph with a * b * c and **bold**.

### Summary

_No response_
"""


def run_issue(body):
    env = dict(os.environ, ISSUE_BODY=body, ISSUE_NUMBER="7", ISSUE_USER="tester")
    res = subprocess.run(
        [sys.executable, str(TOOLS / "issue-payload.py"), "--news"],
        env=env, capture_output=True, text=True, cwd=str(TOOLS.parent),
    )
    return res


class ParserAndCli(unittest.TestCase):
    def payload(self):
        res = run_issue(ISSUE_BODY)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def test_parser_preserves_newlines(self):
        paras = issue_payload.paragraphs(
            "Intro  text\n-  a\n- b\n\n\nNext   para\nsecond line"
        )
        self.assertEqual(paras, ["Intro text\n- a\n- b", "Next para\nsecond line"])

    def test_cli_normalization_preserves_newlines(self):
        self.assertEqual(
            add_news.as_paragraphs("Intro\n- a\n-   b\n\nTail"),
            ["Intro\n- a\n- b", "Tail"],
        )
        self.assertEqual(add_news.as_paragraphs(["x\n- y", "  "]), ["x\n- y"])
        self.assertEqual(add_news.as_paragraphs(None), [])

    def test_issue_to_cli_to_render(self):
        p = self.payload()
        body = add_news.as_paragraphs(p["body"])
        self.assertEqual(body, p["body"])  # idempotent
        self.assertEqual(len(body), 3)
        entry = {"date": "2026-01-02", "title": "List post", "kind": "community",
                 "body": body}
        errors, _ = build.validate_news(
            {"entries": [dict(entry, _file="2026-01-02-list-post.json")]},
            {"groups": []},
        )
        self.assertEqual(errors, [])
        entry["_file"] = "2026-01-02-list-post.json"
        out = build.render_news_item(entry, {})
        self.assertIn('<p class="lede">Intro line that explains things.</p>', out)
        self.assertIn("<ul><li>first *item*</li>", out)
        self.assertIn("<li>second &lt;b&gt;item&lt;/b&gt;</li>", out)
        self.assertIn("<li>third <code>code</code></li></ul>", out)
        self.assertIn("<p>Steps:</p><ol><li>one</li><li>two</li></ol>", out)
        self.assertIn("<p>Closing line after the list.</p>", out)
        self.assertIn("<p>Plain second paragraph with a * b * c and "
                      "<strong>bold</strong>.</p>", out)
        self.assertNotIn("<b>", out)

        # archive path: same renderer, carried through news.d JSON
        idx = json.loads(build.render_news_index({"entries": [entry]}, {"groups": []}))
        self.assertEqual(idx["items"][0]["html"], out)


class Renderer(unittest.TestCase):
    def test_legacy_paragraphs_and_lede(self):
        entry = {"_file": "2026-01-01-x.json", "date": "2026-01-01", "title": "T",
                 "body": ["First para.", "Second **bold** `c`."]}
        out = build.render_news_item(entry, {})
        self.assertIn('<p class="lede">First para.</p><p>Second <strong>bold</strong> '
                      "<code>c</code>.</p>", out)
        self.assertNotIn("<ul", out)
        # with a summary the lede class is dropped
        entry["summary"] = "sum"
        self.assertNotIn('class="lede"', build.render_news_item(entry, {}))

    def test_string_body_multi_paragraph(self):
        # hand-written string bodies still split on blank lines
        b = "A para.\n\nB para.\n- x"
        parts = [p.strip() for p in __import__("re").split(r"\n\s*\n", b)]
        html_out = "".join(build.render_news_block(p) for p in parts)
        self.assertEqual(html_out, "<p>A para.</p><p>B para.</p><ul><li>x</li></ul>")

    def test_inline_asterisks_are_not_lists(self):
        for text in ["*emphasis* start", "**bold** start", "-nospace", "1.5 version",
                     "a - b"]:
            self.assertNotIn("<li>", build.render_news_block(text), text)

    def test_hostile_html_escaped(self):
        out = build.render_news_block(
            '<script>alert(1)</script>\n- <img src=x onerror=1>\n1. "q" & <i>'
        )
        self.assertNotIn("<script", out)
        self.assertNotIn("<img", out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("<li>&lt;img src=x onerror=1&gt;</li>", out)
        self.assertIn("&amp;", out)

    def test_marker_change_starts_new_list(self):
        out = build.render_news_block("- a\n* b\n1. c\n2. d")
        self.assertEqual(
            out,
            "<ul><li>a</li></ul><ul><li>b</li></ul><ol><li>c</li><li>d</li></ol>",
        )

    def test_list_first_is_not_lede_paragraph(self):
        out = build.render_news_block("- a\ntext after", lede=True)
        self.assertEqual(out, "<ul><li>a</li></ul><p>text after</p>")


if __name__ == "__main__":
    unittest.main()
