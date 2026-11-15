import unittest

from radar import store
from radar.notify import matches, notify
from radar.notify import telegram


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


class CodeTest(unittest.TestCase):
    def test_codes_are_stable_and_never_reused(self):
        state = {"jobs": {}}
        store.merge(state, [rec("a"), rec("b")], {"Acme"}, date="2026-11-01")
        self.assertEqual(sorted(j["code"] for j in state["jobs"].values()), ["J1", "J2"])
        store.merge(state, [rec("a")], {"Acme"}, date="2026-11-02")          # b closes
        store.merge(state, [rec("a"), rec("c")], {"Acme"}, date="2026-11-03")
        self.assertEqual(state["jobs"]["a"]["code"], "J1")
        self.assertEqual(state["jobs"]["c"]["code"], "J3")
        self.assertEqual(store.by_code(state, "j3")["uid"], "c")

    def test_backfill_keeps_existing_codes(self):
        state = {"jobs": {"x": dict(rec("x"), first_seen="2026-11-02", code="J7"),
                          "y": dict(rec("y"), first_seen="2026-11-01")}}
        store.assign_codes(state)
        self.assertEqual(state["jobs"]["x"]["code"], "J7")
        self.assertEqual(state["jobs"]["y"]["code"], "J8")
        self.assertEqual(state["next_code"], 9)


class PersonalTest(unittest.TestCase):
    def test_any_of_filter(self):
        flt = [{"countries": ["CH"]}, {"cities": ["London"]}]
        self.assertTrue(matches(rec("a"), flt))
        self.assertTrue(matches(rec("b", countries=["GB"], cities=["London"]), flt))
        self.assertFalse(matches(rec("c", countries=["DE"], cities=["Berlin"]), flt))

    def test_personal_message_has_code_and_hint(self):
        job = dict(rec("a"), code="J42", season=None)
        text = telegram.personal_message(job)
        self.assertIn("<b>J42</b>", text)
        self.assertIn("<code>submit J42</code>", text)

    def test_personal_list_splits_long_batches(self):
        jobs = [dict(rec(str(i)), code="J{}".format(i), title="Intern " * 10) for i in range(60)]
        texts = telegram.personal_list(jobs, limit=1000)
        self.assertGreater(len(texts), 1)
        self.assertTrue(all(len(t) <= 1000 for t in texts))
        self.assertIn("J59", texts[-1])
