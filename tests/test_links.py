import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google_reviewlink import LinkError, feature_from_place_id, parse, place_id_from_feature, review_links  # noqa: E402

HIGH, LOW = "0x47c9cd2a9b3d0f7b", "0x1a2b3c4d5e6f7a8b"
MAPS_URL = ("https://www.google.com/maps/place/Bakkerij+De+Punt/@53.1,6.6,17z/data=!3m1!4b1!4m6!3m5!1s%s:%s"
            "!8m2!3d53.1!4d6.6!16s" % (HIGH, LOW))


def no_network(url):
    raise AssertionError("unexpected request to %s" % url)


class PlaceIds(unittest.TestCase):
    def test_round_trip(self):
        place_id = place_id_from_feature(HIGH, LOW)
        self.assertTrue(place_id.startswith("ChIJ"))
        self.assertEqual(feature_from_place_id(place_id), (HIGH, LOW))

    def test_other_place_id_forms(self):
        self.assertIsNone(feature_from_place_id("EiRTb21lIFN0cmVldCwgU29tZSBDaXR5"))


class Links(unittest.TestCase):
    def test_full_maps_url(self):
        links = review_links(MAPS_URL, opener=no_network)
        place_id = place_id_from_feature(HIGH, LOW)
        self.assertEqual(links["review_url"], "https://search.google.com/local/writereview?placeid=" + place_id)
        self.assertEqual(links["profile_url"], "https://www.google.com/maps?cid=%d" % int(LOW, 16))
        self.assertEqual(links["name"], "Bakkerij De Punt")
        self.assertEqual(links["source"], "maps")

    def test_bare_place_id(self):
        links = review_links("ChIJ7czjsLSIKogRrmpL4Vn3kPs", opener=no_network)
        self.assertEqual(links["review_url"],
                         "https://search.google.com/local/writereview?placeid=ChIJ7czjsLSIKogRrmpL4Vn3kPs")

    def test_gpage(self):
        links = review_links("https://g.page/r/CYt6b15NPCsaEAE", opener=no_network)
        self.assertEqual(links["review_url"], "https://g.page/r/CYt6b15NPCsaEAE/review")

    def test_scheme_is_added(self):
        self.assertEqual(review_links(MAPS_URL.replace("https://", ""), opener=no_network)["source"], "maps")

    def test_short_link_through_consent_page(self):
        def opener(url):
            self.assertEqual(url, "https://maps.app.goo.gl/abc123")
            return 302, "https://consent.google.com/m?continue=" + MAPS_URL.replace("&", "%26")
        links = review_links("https://maps.app.goo.gl/abc123", opener=opener)
        self.assertEqual(links["place_id"], place_id_from_feature(HIGH, LOW))

    def test_short_link_must_stay_on_google(self):
        with self.assertRaises(LinkError):
            review_links("https://maps.app.goo.gl/abc123", opener=lambda url: (302, "https://evil.example/maps"))

    def test_short_link_network_failure(self):
        def opener(url):
            raise OSError("offline")
        with self.assertRaises(LinkError):
            review_links("https://maps.app.goo.gl/abc123", opener=opener)

    def test_rejects(self):
        for raw in ("", "https://example.com/maps/place/x", "javascript:alert(1)", "https://www.google.com/maps",
                    "https://www.google.com/maps?cid=1234567890"):
            with self.assertRaises(LinkError, msg=raw):
                review_links(raw, opener=no_network)

    def test_parse_cid_only(self):
        self.assertEqual(parse("https://www.google.com/maps?cid=1234567890"), {"name": "", "cid": "1234567890"})


if __name__ == "__main__":
    unittest.main()
