"""Google review link generator: turns any Google Maps link into the direct "write a review" link.

Accepts whatever a business owner can copy from Google Maps: a share link (maps.app.goo.gl/...), a full Maps URL,
a g.page review link or a bare place ID.

No Google API key is needed: a Maps URL contains the place's feature id "0x<a>:0x<b>", and a place ID ("ChIJ...")
is just those two 64-bit numbers in a small protobuf, base64url-encoded. The cid (for the plain profile link) is
<b>. Short links are resolved by reading their redirects, and only Google hosts are ever contacted.
Error messages are Dutch and meant for visitors. Standard library only, Python 3.8+.

The engine behind https://www.iverium.nl/google-reviewlink-maken, by Iverium Software.
"""
import base64
import http.client
import re
import struct
from urllib.parse import parse_qs, unquote_plus, urljoin, urlsplit

USER_AGENT = "Mozilla/5.0 (compatible; google-reviewlink/1.0; +https://github.com/Iverium/google-reviewlink)"
TIMEOUT = 8

SHORT_HOSTS = ("maps.app.goo.gl", "goo.gl", "g.co", "share.google")
GOOGLE_HOST = re.compile(r"(^|\.)(google\.[a-z.]+|goo\.gl|g\.page|g\.co|share\.google)$")
FEATURE_ID = re.compile(r"(0x[0-9a-f]{1,16}):(0x[0-9a-f]{1,16})", re.I)
PLACE_ID = re.compile(r"\b((?:ChIJ|GhIJ|EiQ|Ei[A-Za-z0-9])[A-Za-z0-9_-]{10,})")
CID = re.compile(r"[?&](?:cid|ludocid)=(\d{5,20})")
GPAGE_REVIEW = re.compile(r"^https?://g\.page/r/([A-Za-z0-9_-]+)")


class LinkError(Exception):
    """A problem explained to the visitor in plain Dutch (the message can be shown as is)."""


def place_id_from_feature(high, low):
    """Place ID for the feature id parts found in Maps URLs, e.g. ("0x47c9cd...", "0x2a1b...")."""
    raw = b"\x0a\x12\x09" + struct.pack("<Q", int(high, 16)) + b"\x11" + struct.pack("<Q", int(low, 16))
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def feature_from_place_id(place_id):
    """The reverse: (high, low) hex strings, or None for place IDs that are not in this simple form."""
    try:
        raw = base64.urlsafe_b64decode(place_id + "=" * (-len(place_id) % 4))
    except (ValueError, TypeError):
        return None
    if len(raw) != 20 or raw[:3] != b"\x0a\x12\x09" or raw[11:12] != b"\x11":
        return None
    return hex(struct.unpack("<Q", raw[3:11])[0]), hex(struct.unpack("<Q", raw[12:20])[0])


def _name_from_url(url):
    match = re.search(r"/maps/place/([^/@?]+)", url)
    if not match:
        return ""
    name = unquote_plus(match.group(1)).strip()
    return name if not FEATURE_ID.match(name) else ""


def parse(url):
    """Pull whatever identifiers a Google URL contains: dict with name and, when present, place_id and cid."""
    text = unquote_plus(url)
    found = {"name": _name_from_url(text)}
    feature = FEATURE_ID.search(text)
    if feature:
        found["place_id"] = place_id_from_feature(feature.group(1), feature.group(2))
        found["cid"] = str(int(feature.group(2), 16))
    cid = CID.search(text)
    if cid and "cid" not in found:
        found["cid"] = cid.group(1)
    place = re.search(r"place_?id[=:]([A-Za-z0-9_-]{16,})", text, re.I)
    if place and "place_id" not in found:
        found["place_id"] = place.group(1)
    return found


def _location(url):
    """GET url and return (status, Location header). Callers only pass Google hosts."""
    parts = urlsplit(url)
    connection_class = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    conn = connection_class(parts.hostname, parts.port, timeout=TIMEOUT)
    try:
        conn.request("GET", (parts.path or "/") + ("?" + parts.query if parts.query else ""),
                     headers={"User-Agent": USER_AGENT, "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.5"})
        response = conn.getresponse()
        response.read(20000)
        return response.status, response.getheader("location")
    finally:
        conn.close()


def _resolve_short(url, opener=_location):
    """Follow a short link's redirects (Google hosts only) and return the first URL with usable identifiers."""
    for _ in range(5):
        status, location = opener(url)
        if status not in (301, 302, 303, 307, 308) or not location:
            raise LinkError("Deze link verwijst niet naar een bedrijf op Google Maps. Kopieer de link via 'Delen' "
                            "op uw bedrijfsprofiel in Google Maps.")
        location = urljoin(url, location)
        parts = urlsplit(location)
        if parts.hostname and parts.hostname.startswith("consent.google."):
            location = (parse_qs(parts.query).get("continue") or [location])[0]
            parts = urlsplit(location)
        if parts.scheme not in ("http", "https") or not parts.hostname or not GOOGLE_HOST.search(parts.hostname):
            raise LinkError("Deze link verwijst niet naar Google Maps.")
        found = parse(location)
        if found.get("place_id") or found.get("cid"):
            return location, found
        url = location
    raise LinkError("We konden deze link niet herleiden tot een bedrijf op Google Maps.")


def review_links(raw, opener=_location):
    """Return dict(review_url, profile_url, place_id, name, source) or raise LinkError (Dutch message).

    opener(url) -> (status, location) is only called for Google short links; pass your own to add caching or to
    run offline in tests.
    """
    raw = (raw or "").strip()
    if not raw:
        raise LinkError("Plak de link naar uw bedrijf op Google Maps.")
    if len(raw) > 2000:
        raise LinkError("Deze link is te lang.")
    bare = PLACE_ID.fullmatch(raw)
    if bare:
        place_id = bare.group(1)
        return dict(review_url="https://search.google.com/local/writereview?placeid=" + place_id,
                    profile_url="https://www.google.com/maps/place/?q=place_id:" + place_id,
                    place_id=place_id, name="", source="place_id")
    if "://" not in raw:
        raw = "https://" + raw
    parts = urlsplit(raw)
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or not GOOGLE_HOST.search(host):
        raise LinkError("Dit is geen link van Google Maps. Open uw bedrijf in Google Maps, klik op 'Delen' en kopieer "
                        "de link.")
    gpage = GPAGE_REVIEW.match(raw)
    if gpage:
        return dict(review_url="https://g.page/r/%s/review" % gpage.group(1),
                    profile_url="https://g.page/r/%s" % gpage.group(1), place_id="", name="", source="g.page")
    found = parse(raw)
    if not (found.get("place_id") or found.get("cid")):
        if host in SHORT_HOSTS or host.endswith(".app.goo.gl"):
            try:
                raw, found = _resolve_short(raw, opener)
            except LinkError:
                raise
            except Exception:
                raise LinkError("We konden de link niet openen. Probeer het opnieuw, of plak de volledige link uit de "
                                "adresbalk van Google Maps.")
        else:
            raise LinkError("In deze link staat geen bedrijf. Open uw bedrijf in Google Maps (zodat het bedrijfspaneel "
                            "zichtbaar is), klik op 'Delen' en kopieer die link.")
    place_id = found.get("place_id", "")
    if not place_id:
        raise LinkError("In deze link staat alleen een klant-ID van uw bedrijf, daarmee kan Google geen reviewlink "
                        "maken. Gebruik de link via 'Delen' in Google Maps.")
    profile = "https://www.google.com/maps?cid=" + found["cid"] if found.get("cid") else \
        "https://www.google.com/maps/place/?q=place_id:" + place_id
    return dict(review_url="https://search.google.com/local/writereview?placeid=" + place_id, profile_url=profile,
                place_id=place_id, name=found.get("name", ""), source="maps")
