#!/usr/bin/env python
"""Focused tests for the module firmware schema and its rendering.

Run with: python tools/test_modules_schema.py

These tests import the real implementation in tools/build.py rather than
re-implementing the checks. They cover the agreed contract:
    - firmware is an array of "AZJ2" / "AZF3" only
    - firmware_source is a valid HTTPS URL required when firmware is set
    - firmware_source is forbidden when firmware is absent/empty
    - family is a canonical slug; missing families default to repo-qualified ids
    - test_note, when present, is a non-empty string of at most 240 chars
    - renderer groups modules by firmware and keeps compare packages separate
"""

import html.parser
import importlib.util
import re
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
BUILD_PATH = TOOLS_DIR / "build.py"
SPEC = importlib.util.spec_from_file_location("build", str(BUILD_PATH))
build = importlib.util.module_from_spec(SPEC)
sys.modules["build"] = build
SPEC.loader.exec_module(build)


class TestHttpsValidator(unittest.TestCase):
    def test_valid_https_urls(self):
        for url in [
            "https://github.com/booinspace/galaxyxr-modules/releases/tag/v1",
            "https://example.com/path",
        ]:
            with self.subTest(url=url):
                self.assertTrue(build._is_https(url))

    def test_invalid_rejected(self):
        for value in [
            "http://example.com",
            "https://",
            "https://localhost",
            "https://foo",
            "ftp://example.com",
            "not-a-url",
            "https://.example.com",
            "https://example.com.",
            123,
            None,
        ]:
            with self.subTest(value=value):
                self.assertFalse(build._is_https(value))


class TestFirmwareSchema(unittest.TestCase):
    def test_valid_azj2(self):
        fw_set, evidence, errors = build._module_firmware({
            "firmware": ["AZJ2"],
            "firmware_source": "https://github.com/booinspace/galaxyxr-modules/releases/tag/v1",
        })
        self.assertEqual(fw_set, {"AZJ2"})
        self.assertEqual(errors, [])
        self.assertEqual(evidence, "https://github.com/booinspace/galaxyxr-modules/releases/tag/v1")

    def test_valid_azf3(self):
        fw_set, _, errors = build._module_firmware({
            "firmware": ["AZF3"],
            "firmware_source": "https://github.com/4uva4ek/galaxyxr-modules/releases/tag/v1",
        })
        self.assertEqual(fw_set, {"AZF3"})
        self.assertEqual(errors, [])

    def test_multiple_valid(self):
        fw_set, _, errors = build._module_firmware({
            "firmware": ["AZJ2", "AZF3"],
            "firmware_source": "https://example.com/evidence",
        })
        self.assertEqual(fw_set, {"AZJ2", "AZF3"})
        self.assertEqual(errors, [])

    def test_absent_firmware_allowed(self):
        fw_set, evidence, errors = build._module_firmware({})
        self.assertEqual(fw_set, set())
        self.assertIsNone(evidence)
        self.assertEqual(errors, [])

    def test_string_rejected(self):
        _, _, errors = build._module_firmware({
            "firmware": "AZJ2",
            "firmware_source": "https://example.com/evidence",
        })
        self.assertTrue(any("array" in e.lower() for e in errors))

    def test_blank_entry_rejected(self):
        _, _, errors = build._module_firmware({
            "firmware": ["AZJ2", ""],
            "firmware_source": "https://example.com/evidence",
        })
        self.assertTrue(any("blank" in e.lower() for e in errors))

    def test_unknown_rejected(self):
        _, _, errors = build._module_firmware({
            "firmware": ["AZJ3"],
            "firmware_source": "https://example.com/evidence",
        })
        self.assertTrue(any("unsupported" in e.lower() for e in errors))

    def test_duplicate_rejected(self):
        _, _, errors = build._module_firmware({
            "firmware": ["AZJ2", "AZJ2"],
            "firmware_source": "https://example.com/evidence",
        })
        self.assertTrue(any("duplicate" in e.lower() for e in errors))

    def test_evidence_forbidden_without_firmware(self):
        _, _, errors = build._module_firmware({
            "firmware_source": "https://example.com/evidence",
        })
        self.assertTrue(errors)
        self.assertTrue(any("firmware_source" in e.lower() for e in errors))

    def test_evidence_forbidden_with_empty_array(self):
        _, _, errors = build._module_firmware({
            "firmware": [],
            "firmware_source": "https://example.com/evidence",
        })
        self.assertTrue(errors)
        self.assertTrue(any("firmware_source" in e.lower() for e in errors))

    def test_evidence_required_when_firmware_set(self):
        _, _, errors = build._module_firmware({"firmware": ["AZJ2"]})
        self.assertTrue(any("required" in e.lower() for e in errors))

    def test_evidence_must_be_valid_https(self):
        _, _, errors = build._module_firmware({
            "firmware": ["AZJ2"],
            "firmware_source": "https://foo",
        })
        self.assertTrue(any("valid HTTPS URL" in e for e in errors))


class TestFamilyAndLabels(unittest.TestCase):
    def test_explicit_family_key_and_label(self):
        m = {"family": "window-controls"}
        self.assertEqual(build._module_compare_key(m, "gxr_window", "a/b"), "window-controls")
        self.assertEqual(build._module_compare_label(m, "gxr_window", "Name"), "Window Controls")

    def test_no_family_uses_repo_qualified_id(self):
        m = {}
        self.assertEqual(
            build._module_compare_key(m, "gxr_window_curvature", "BlueScorpioVR/galaxyxr-modules"),
            "BlueScorpioVR/galaxyxr-modules:gxr_window_curvature",
        )
        self.assertEqual(
            build._module_compare_label(m, "gxr_window_curvature", "Galaxy XR Window"),
            "Galaxy XR Window",
        )

    def test_family_slug_validation(self):
        self.assertTrue(build._is_valid_family("window-controls"))
        self.assertTrue(build._is_valid_family("wifi-adb"))
        self.assertFalse(build._is_valid_family("Window Controls"))
        self.assertFalse(build._is_valid_family("window_controls"))
        self.assertFalse(build._is_valid_family(""))
        self.assertFalse(build._is_valid_family("-leading"))
        self.assertFalse(build._is_valid_family(123))


class TestTestNote(unittest.TestCase):
    def test_valid_note(self):
        self.assertEqual(build._module_test_note({"test_note": "Works on AZJ2."}), "Works on AZJ2.")

    def test_absent_allowed(self):
        self.assertIsNone(build._module_test_note({}))

    def test_blank_rejected(self):
        self.assertIsNone(build._module_test_note({"test_note": "   "}))

    def test_overlong_rejected(self):
        self.assertIsNone(build._module_test_note({"test_note": "x" * 241}))

    def test_non_string_rejected(self):
        self.assertIsNone(build._module_test_note({"test_note": 123}))


class TestModuleValidator(unittest.TestCase):
    def _cat(self, repo):
        return {
            "groups": [
                {
                    "id": "kernelsu-modules",
                    "title": "Kernelsu",
                    "icon": "⚡",
                    "hue": "#34d399",
                    "blurb": "x",
                    "repos": [{"repo": repo, "url": "https://github.com/" + repo, "status": "ok"}],
                }
            ]
        }

    def _entry(self, repo, mods):
        return {"_file": repo.replace("/", "__") + ".json", "repo": repo, "checked": "2026-11-15", "modules": mods}

    def test_blank_test_note_errors(self):
        cat = self._cat("owner/repo")
        idx = [self._entry("owner/repo", [{"id": "m1", "name": "M", "about": "x", "status": "stable", "test_note": "  "}])]
        errors, _ = build.validate_modules(cat, idx)
        self.assertTrue(any("test_note" in e and "blank" in e for e in errors))

    def test_overlong_test_note_errors(self):
        cat = self._cat("owner/repo")
        idx = [self._entry("owner/repo", [{"id": "m1", "name": "M", "about": "x", "status": "stable", "test_note": "x" * 241}])]
        errors, _ = build.validate_modules(cat, idx)
        self.assertTrue(any("test_note" in e and "too long" in e for e in errors))

    def test_invalid_family_slug_errors(self):
        cat = self._cat("owner/repo")
        idx = [self._entry("owner/repo", [{"id": "m1", "name": "M", "about": "x", "status": "stable", "family": "Bad Slug"}])]
        errors, _ = build.validate_modules(cat, idx)
        self.assertTrue(any("family" in e and "slug" in e for e in errors))

    def test_evidence_without_firmware_errors(self):
        cat = self._cat("owner/repo")
        idx = [self._entry("owner/repo", [{"id": "m1", "name": "M", "about": "x", "status": "stable", "firmware_source": "https://example.com/e"}])]
        errors, _ = build.validate_modules(cat, idx)
        self.assertTrue(any("firmware_source" in e for e in errors))

    def test_string_firmware_errors(self):
        cat = self._cat("owner/repo")
        idx = [self._entry("owner/repo", [{"id": "m1", "name": "M", "about": "x", "status": "stable", "firmware": "AZJ2", "firmware_source": "https://example.com/e"}])]
        errors, _ = build.validate_modules(cat, idx)
        self.assertTrue(any("array" in e for e in errors))

    def test_blank_firmware_entry_errors(self):
        cat = self._cat("owner/repo")
        idx = [self._entry("owner/repo", [{"id": "m1", "name": "M", "about": "x", "status": "stable", "firmware": ["AZJ2", ""], "firmware_source": "https://example.com/e"}])]
        errors, _ = build.validate_modules(cat, idx)
        self.assertTrue(any("blank" in e.lower() for e in errors))


class TestRenderAgainstCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = build.load_catalog()
        cls.module_index = build.load_modules(cls.cat)
        cls.html = build.render_modules_view(cls.cat, cls.module_index)

    def test_required_ids_present(self):
        for ident in ["mod-btn-group", "mod-btn-compare", "mod-grouped", "mod-compare"]:
            self.assertIn(f'id="{ident}"', self.html)

    def test_aria_relationships(self):
        self.assertIn('role="tabpanel" aria-labelledby="mod-btn-group"', self.html)
        self.assertIn('role="tabpanel" aria-labelledby="mod-btn-compare"', self.html)
        self.assertRegex(self.html, r'id="mod-btn-group"[^\u003e]*role="tab"[^\u003e]*aria-controls="mod-grouped"')
        self.assertRegex(self.html, r'id="mod-btn-compare"[^\u003e]*role="tab"[^\u003e]*aria-controls="mod-compare"')
        self.assertIn("Compare mode needs JavaScript", self.html)

    def test_firmware_group_counts(self):
        # <details class="fw-group" open><summary>...AZJ2...12 modules...
        groups = re.findall(
            r'<details class="fw-group"( open)?><summary>.*?(AZJ2|AZF3|Other).*?(\d+) module',
            self.html,
            re.S,
        )
        counts = {}
        for _, label, count in groups:
            counts[label] = int(count)
        self.assertEqual(counts.get("AZJ2"), 12)
        self.assertEqual(counts.get("AZF3"), 1)
        self.assertEqual(counts.get("Other"), 32)

    def test_compare_rows_preserve_package_identity(self):
        compare_groups = {}
        for entry in self.module_index:
            repo = entry["repo"]
            for m in entry["modules"]:
                key = build._module_compare_key(m, m.get("id", ""), repo)
                compare_groups.setdefault(key, []).append((repo, m.get("id"), m.get("name")))

        rows = re.findall(r'<div class="mod-compare-row">', self.html)
        self.assertEqual(len(rows), len(compare_groups))

        # window-controls row has two distinct repo cells because family is explicit
        window_match = re.search(
            r'<div class="mod-compare-feature"><span>Window Controls</span></div>'
            r'.*?<div class="mod-compare-cells">(.*?)</div>\s*</div>',
            self.html,
            re.S,
        )
        self.assertTrue(window_match)
        cell_repos = re.findall(r'<a class="mod-compare-repo"[^>]*>([^<]+)</a>', window_match.group(1))
        self.assertEqual(len(cell_repos), 2)
        self.assertIn("BlueScorpioVR/galaxyxr-modules", cell_repos)
        self.assertIn("booinspace/galaxyxr-modules", cell_repos)

    def test_same_id_without_family_not_conflated(self):
        # Two repos share the same module id but neither has an explicit family
        cat = {
            "groups": [
                {
                    "id": "kernelsu-modules",
                    "title": "Kernelsu",
                    "icon": "⚡",
                    "hue": "#34d399",
                    "blurb": "x",
                    "repos": [
                        {"repo": "repo-a/x", "url": "https://github.com/repo-a/x"},
                        {"repo": "repo-b/x", "url": "https://github.com/repo-b/x"},
                    ],
                }
            ]
        }
        idx = [
            {"repo": "repo-a/x", "checked": "2026-11-15", "modules": [{"id": "shared-id", "name": "Shared A", "about": "a", "status": "stable"}]},
            {"repo": "repo-b/x", "checked": "2026-11-15", "modules": [{"id": "shared-id", "name": "Shared B", "about": "b", "status": "stable"}]},
        ]
        out = build.render_modules_view(cat, idx)
        rows = re.findall(r'<div class="mod-compare-row">', out)
        self.assertEqual(len(rows), 2)
        self.assertIn("Shared A", out)
        self.assertIn("Shared B", out)

    def test_render_escapes_markup(self):
        cat = {
            "groups": [
                {
                    "id": "kernelsu-modules",
                    "title": "Kernelsu",
                    "icon": "⚡",
                    "hue": "#34d399",
                    "blurb": "x",
                    "repos": [{"repo": "owner/repo", "url": "https://github.com/owner/repo"}],
                }
            ]
        }
        idx = [{
            "repo": "owner/repo",
            "checked": "2026-11-15",
            "modules": [{
                "id": "m1",
                "name": '<script>alert(1)</script>',
                "about": '**bold** & `code`',
                "status": "stable",
                "firmware": ["AZJ2"],
                "firmware_source": "https://github.com/owner/repo/releases/tag/v1",
            }],
        }]
        out = build.render_modules_view(cat, idx)
        self.assertNotIn("<script>alert(1)</script>", out)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", out)
        # Raw HTML/Markup is escaped to literals; ampersand becomes &amp;
        self.assertIn("**bold** &amp; \u0060code\u0060", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
