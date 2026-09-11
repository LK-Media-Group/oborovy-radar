import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("collect", ROOT / "scripts/collect.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

class RadarTests(unittest.TestCase):
    def report(self, config=None, start="2026-09-07T00:00:00Z", end="2026-09-14T00:00:00Z"):
        return c.collect(config or json.loads((ROOT/"examples/sources.json").read_text()), c.date(start), c.date(end), ROOT/"examples")
    def test_rss_atom_and_dedup(self):
        r = self.report()
        self.assertEqual(len(r["items"]), 2)
        self.assertEqual(len(r["items"][1]["sources"]), 2)
        self.assertEqual(r["problems"], [])
    def test_window_end_exclusive(self):
        r = self.report(start="2026-09-08T07:00:00Z", end="2026-09-09T11:00:00Z")
        self.assertEqual(len(r["items"]), 1)
    def test_one_feed_failure_keeps_other(self):
        config = json.loads((ROOT/"examples/sources.json").read_text())
        config["feeds"][1]["fixture"] = "missing.xml"
        r = self.report(config)
        self.assertEqual(r["sources_ok"], 1)
        self.assertEqual(len(r["items"]), 1)
        self.assertTrue(r["problems"])
    def test_missing_timezone_and_date(self):
        self.assertIsNone(c.date("2026-09-09T11:00:00"))
        entries, skipped = c.parse(b'<rss><channel><item><title>X</title><link>https://a.example/</link></item></channel></rss>', "https://a.example")
        self.assertEqual((entries, skipped), ([], 1))
    def test_entities_rejected(self):
        with self.assertRaises(ValueError): c.parse(b'<!DOCTYPE rss [<!ENTITY e "x">]><rss/>', "https://a.example")
    def test_unsafe_link_and_tracking(self):
        for url in ["javascript:alert(1)", "http://a.example", "https://user:pass@a.example"]:
            with self.assertRaises(ValueError): c.canonical(url)
        self.assertEqual(c.canonical("https://a.example/x?utm_source=x&id=2#part"), "https://a.example/x?id=2")

if __name__ == "__main__": unittest.main()
