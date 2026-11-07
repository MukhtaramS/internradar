import unittest

from radar.locations import parse_location, parse_locations, split_locations


class ParseLocationTest(unittest.TestCase):
    def check(self, text, city, country, europe):
        p = parse_location(text)
        self.assertEqual((p.city, p.country, p.in_europe), (city, country, europe), text)

    def test_common_shapes(self):
        self.check("London, UK", "London", "GB", True)
        self.check("London, England, United Kingdom", "London", "GB", True)
        self.check("Zürich, Switzerland", "Zurich", "CH", True)
        self.check("Zurich, CH", "Zurich", "CH", True)
        self.check("Germany, Munich", "Munich", "DE", True)
        self.check("Frankenthal, DEU", "Frankenthal", "DE", True)
        self.check("United Kingdom, Berkshire, Reading", "Reading", "GB", True)
        self.check("Amsterdam", "Amsterdam", "NL", True)
        self.check("LDN", "London", "GB", True)
        self.check("Paris, FR", "Paris", "FR", True)

    def test_us_lookalikes_are_not_europe(self):
        self.check("Cambridge, MA", None, "US", False)
        self.check("London, Ontario, Canada", None, "CA", False)
        self.check("London, ON", None, "CA", False)
        self.check("Menlo Park, CA", None, "US", False)
        self.check("Paris, TX", None, "US", False)
        self.check("New York, NY", None, "US", False)

    def test_state_code_that_matches_the_city_country(self):
        # DE is Delaware and Germany; Munich decides.
        self.check("Munich, DE", "Munich", "DE", True)

    def test_europe_wide_and_unknown(self):
        p = parse_location("Remote - EMEA")
        self.assertTrue(p.in_europe)
        self.assertTrue(p.remote)
        self.assertIsNone(p.country)
        self.check("2 Locations", None, None, False)
        self.check("", None, None, False)

    def test_split_multi(self):
        self.assertEqual(split_locations(["London; Paris", "Zurich or Remote"]),
                         ["London", "Paris", "Zurich", "Remote"])
        places = parse_locations(["New York, NY; London, UK"])
        self.assertEqual([p.in_europe for p in places], [False, True])


if __name__ == "__main__":
    unittest.main()
