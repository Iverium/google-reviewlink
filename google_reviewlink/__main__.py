"""Command line: google-reviewlink <maps link or place ID> [--json] [--qr poster.svg]"""
import argparse
import json
import sys

from .links import LinkError, review_links


def main(argv=None):
    parser = argparse.ArgumentParser(prog="google-reviewlink",
                                     description="Turn a Google Maps link, share link or place ID into the direct "
                                                 "'write a review' link.")
    parser.add_argument("link", help="Google Maps link (e.g. https://maps.app.goo.gl/...) or place ID (ChIJ...)")
    parser.add_argument("--json", action="store_true", help="print all links as JSON")
    parser.add_argument("--qr", metavar="FILE", help="also save a QR code of the review link (.svg or .png); "
                                                     "needs the tinyqr package")
    args = parser.parse_args(argv)
    try:
        links = review_links(args.link)
    except LinkError as error:
        print(error, file=sys.stderr)
        return 2
    if args.qr:
        try:
            import tinyqr
        except ImportError:
            print("--qr needs tinyqr: pip install git+https://github.com/Iverium/tinyqr", file=sys.stderr)
            return 2
        if args.qr.lower().endswith(".png"):
            with open(args.qr, "wb") as handle:
                handle.write(tinyqr.png(links["review_url"]))
        else:
            with open(args.qr, "w", encoding="utf-8") as handle:
                handle.write(tinyqr.svg(links["review_url"]))
    if args.json:
        print(json.dumps(links, ensure_ascii=False, indent=2))
    else:
        print(links["review_url"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
