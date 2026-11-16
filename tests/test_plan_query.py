"""Tests for /plan URL query parsing (shared contract with client)."""

from __future__ import annotations

import unittest

from lenses.plan_query import parse_plan_query


class PlanQueryTests(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(parse_plan_query(""), {})

    def test_strip_question(self) -> None:
        self.assertEqual(
            parse_plan_query("?repo=r1&wbs_p=docs/a.md&id=M1E1S1&tab=today"),
            {
                "repo": "r1",
                "wbs_p": "docs/a.md",
                "id": "M1E1S1",
                "tab": "today",
            },
        )

    def test_last_wins_duplicate_keys(self) -> None:
        self.assertEqual(parse_plan_query("tab=plan&tab=today"), {"tab": "today"})


if __name__ == "__main__":
    unittest.main()
