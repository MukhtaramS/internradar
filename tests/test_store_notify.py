import unittest

from radar import store
from radar.notify import matches, notify


def rec(uid, company="Acme", **extra):
    base = {"uid": uid, "company": company, "title": "Intern", "url": "https://x/" + uid,
            "countries": ["CH"], "cities": ["Zurich"], "category": "quant", "role": "Software",
            "kind": "Internship", "degrees": [], "posted": None}
    base.update(extra)
    return base


class StoreTest(unittest.TestCase):
    def test_add_close_reopen(self):
        state = {"jobs": {}}
        added, closed, _ = store.merge(state, [rec("a"), rec("b")], {"Acme"}, date="2026-11-01")
        self.assertEqual(len(added), 2)

        added, closed, _ = store.merge(state, [rec("a")], {"Acme"}, date="2026-11-02")
        self.assertEqual([c["uid"] for c in closed], ["b"])
        self.assertEqual(state["jobs"]["b"]["closed"], "2026-11-02")

        _, _, reopened = store.merge(state, [rec("a"), rec("b")], {"Acme"}, date="2026-11-03")
        self.assertEqual([r["uid"] for r in reopened], ["b"])
        self.assertTrue(state["jobs"]["b"]["active"])
        self.assertEqual(state["jobs"]["b"]["first_seen"], "2026-11-01")
        self.assertNotIn("closed", state["jobs"]["b"])

    def test_failed_company_is_left_alone(self):
        state = {"jobs": {}}
        store.merge(state, [rec("a", company="Broken")], {"Broken"}, date="2026-11-01")
        _, closed, _ = store.merge(state, [], {"SomethingElse"}, date="2026-11-02")
        self.assertEqual(closed, [])
        self.assertTrue(state["jobs"]["a"]["active"])

    def test_known_posted_date_survives(self):
        state = {"jobs": {}}
        store.merge(state, [rec("a", posted="2026-10-01")], {"Acme"}, date="2026-11-01")
        store.merge(state, [rec("a", posted=None)], {"Acme"}, date="2026-11-02")
        self.assertEqual(state["jobs"]["a"]["posted"], "2026-10-01")


class NotifyTest(unittest.TestCase):
    def test_filters(self):
        job = rec("a")
        self.assertTrue(matches(job, None))
        self.assertTrue(matches(job, {"countries": ["CH"]}))
        self.assertTrue(matches(job, {"countries": ["CH"], "categories": ["quant"]}))
        self.assertFalse(matches(job, {"cities": ["London"]}))
        with self.assertRaises(ValueError):
            matches(job, {"colour": ["red"]})

    def test_routes_by_filter_and_skips_unset_secrets(self):
        sent = {}

        def fake(settings, jobs):
            sent[settings["name"]] = [j["uid"] for j in jobs]
            return 1

        import radar.notify as n
        old = dict(n.SENDERS)
        n.SENDERS["telegram"] = fake
        try:
            notify([rec("ch"), rec("uk", countries=["GB"], cities=["London"])], channels=[
                {"name": "all", "type": "telegram", "chat": "x"},
                {"name": "london", "type": "telegram", "chat": "y", "filter": {"cities": ["London"]}},
                {"name": "paris", "type": "telegram", "chat": "z", "filter": {"cities": ["Paris"]}},
            ])
        finally:
            n.SENDERS.update(old)
        self.assertEqual(sent, {"all": ["ch", "uk"], "london": ["uk"]})



class CombineTest(unittest.TestCase):
    def test_same_job_listed_per_office_is_merged(self):
        from radar.main import combine
        a = rec("x", locations=["Zurich, CH"], europe_wide=False, remote=False, posted="2026-10-02")
        b = rec("x", countries=["GB"], cities=["London"], locations=["London, UK"],
                europe_wide=False, remote=False, posted="2026-10-01")
        out = combine([a, b, rec("y", locations=[], europe_wide=False, remote=False)])
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["countries"], ["CH", "GB"])
        self.assertEqual(out[0]["cities"], ["London", "Zurich"])
        self.assertEqual(out[0]["posted"], "2026-10-01")


if __name__ == "__main__":
    unittest.main()
