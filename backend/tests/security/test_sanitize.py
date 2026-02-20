"""Tests for input sanitization."""

from __future__ import annotations

import unittest

from backend.security.sanitize import (
    escape_html,
    has_mongo_operators,
    strip_mongo_operators,
    strip_script_tags,
)


class TestStripMongoOperators(unittest.TestCase):
    def test_strips_dollar_prefixed_keys(self) -> None:
        data = {"name": "test", "$gt": "", "$ne": "admin"}
        result = strip_mongo_operators(data)
        self.assertEqual(result, {"name": "test"})

    def test_strips_nested_operators(self) -> None:
        data = {"user": {"email": "a@b.com", "$where": "1==1"}}
        result = strip_mongo_operators(data)
        self.assertEqual(result, {"user": {"email": "a@b.com"}})

    def test_strips_in_lists(self) -> None:
        data = [{"$gt": 0}, {"name": "ok"}]
        result = strip_mongo_operators(data)
        self.assertEqual(result, [{}, {"name": "ok"}])

    def test_preserves_clean_data(self) -> None:
        data = {"name": "Alice", "age": 30, "tags": ["a", "b"]}
        result = strip_mongo_operators(data)
        self.assertEqual(result, data)

    def test_scalar_passthrough(self) -> None:
        self.assertEqual(strip_mongo_operators(42), 42)
        self.assertEqual(strip_mongo_operators("hello"), "hello")


class TestHasMongoOperators(unittest.TestCase):
    def test_detects_operators(self) -> None:
        self.assertTrue(has_mongo_operators({"$gt": 5}))
        self.assertTrue(has_mongo_operators({"a": {"$ne": ""}}))
        self.assertTrue(has_mongo_operators([{"$where": "true"}]))

    def test_clean_data_returns_false(self) -> None:
        self.assertFalse(has_mongo_operators({"name": "safe"}))
        self.assertFalse(has_mongo_operators([1, 2, 3]))
        self.assertFalse(has_mongo_operators("string"))


class TestEscapeHtml(unittest.TestCase):
    def test_escapes_angle_brackets(self) -> None:
        self.assertEqual(escape_html("<b>bold</b>"), "&lt;b&gt;bold&lt;/b&gt;")

    def test_escapes_quotes(self) -> None:
        self.assertEqual(escape_html('a"b\'c'), "a&quot;b&#x27;c")

    def test_escapes_ampersand(self) -> None:
        self.assertEqual(escape_html("a&b"), "a&amp;b")


class TestStripScriptTags(unittest.TestCase):
    def test_removes_script_block(self) -> None:
        html = 'Hello<script>alert("xss")</script>World'
        self.assertEqual(strip_script_tags(html), "HelloWorld")

    def test_removes_multiline_script(self) -> None:
        html = "before<script>\nalert(1)\n</script>after"
        self.assertEqual(strip_script_tags(html), "beforeafter")

    def test_preserves_clean_text(self) -> None:
        text = "No scripts here"
        self.assertEqual(strip_script_tags(text), text)


if __name__ == "__main__":
    unittest.main()
