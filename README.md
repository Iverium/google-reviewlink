# google-reviewlink

Maakt van elke Google Maps-link een directe link om een Google-review te schrijven. Wie de link opent, krijgt meteen het review-venster met de sterren te zien. Een API-sleutel is niet nodig.

Dit is de motor achter de gratis [Google-reviewlink en QR-poster op iverium.nl](https://www.iverium.nl/google-reviewlink-maken).

De tool accepteert alles wat een ondernemer uit Google Maps kan kopiëren:

- een deellink, zoals `https://maps.app.goo.gl/...`
- een volledige Google Maps-URL van het bedrijf
- een `g.page/r/...`-link
- een place ID (`ChIJ...`)

## Hoe het werkt

Een Google Maps-URL bevat het feature-id van de plek: `0x<a>:0x<b>`. Een place ID (`ChIJ...`) is precies diezelfde twee 64-bits getallen in een klein protobuf-bericht, gecodeerd in base64url. Het tweede getal is ook de `cid`, waarmee u een link naar het bedrijfsprofiel maakt. De tool hoeft dus niets aan Google te vragen.

Alleen een korte deellink moet worden opgevolgd. Dat gebeurt door de doorverwijzingen te lezen, en de tool maakt alleen verbinding met Google-domeinen. Ook de toestemmingspagina van Google (consent.google.com) wordt netjes overgeslagen.

## Installeren

```bash
pip install git+https://github.com/Iverium/google-reviewlink
```

Alleen de Python-standaardbibliotheek, Python 3.8 of nieuwer.

## Gebruik

```bash
google-reviewlink "https://maps.app.goo.gl/abc123"
google-reviewlink "https://www.google.com/maps/place/..." --json
google-reviewlink ChIJ7czjsLSIKogRrmpL4Vn3kPs --qr review.svg
```

Met `--qr` slaat de tool ook een QR-code van de reviewlink op, als SVG of PNG, bijvoorbeeld voor op de toonbank of de factuur. Daarvoor is [tinyqr](https://github.com/Iverium/tinyqr) nodig.

Vanuit Python:

```python
from google_reviewlink import LinkError, review_links

links = review_links("https://maps.app.goo.gl/abc123")
links["review_url"]   # https://search.google.com/local/writereview?placeid=ChIJ...
links["profile_url"]  # https://www.google.com/maps?cid=...
links["place_id"], links["name"]
```

Bij een onbruikbare link geeft `review_links` een `LinkError` met een Nederlandse uitleg voor de gebruiker. Met de parameter `opener` kunt u zelf bepalen hoe korte links worden opgehaald, bijvoorbeeld met een cache, of zonder netwerk in tests.

Losse hulpfuncties:

```python
from google_reviewlink import feature_from_place_id, place_id_from_feature

place_id_from_feature("0x47c9cd2a9b3d0f7b", "0x1a2b3c4d5e6f7a8b")  # 'ChIJew89myrNyUcRi3pvXk08Kxo'
feature_from_place_id("ChIJew89myrNyUcRi3pvXk08Kxo")              # ('0x47c9cd2a9b3d0f7b', '0x1a2b3c4d5e6f7a8b')
```

## English

`google-reviewlink` turns any Google Maps link into the direct "write a review" link:
- share links (`maps.app.goo.gl`)
- full Maps URLs
- `g.page` links
- place IDs

No API key is needed. A place ID is just the Maps feature id `0x<a>:0x<b>` as two little-endian 64-bit integers in a tiny protobuf, base64url-encoded, so it can be computed offline. Short links are resolved by following redirects, and only to Google hosts. It uses only the standard library and needs Python 3.8+. Error messages are Dutch.

## Andere tools

- [tinyqr](https://github.com/Iverium/tinyqr): QR-codes als SVG of PNG zonder afhankelijkheden
- [website-check](https://github.com/Iverium/website-check): vindbaarheid en techniek
- [toegankelijkheid-check](https://github.com/Iverium/toegankelijkheid-check): automatische WCAG-controle
- [cookie-check](https://github.com/Iverium/cookie-check): tracking en cookies vóór toestemming

## Licentie

MIT. Gemaakt door [Iverium Software](https://www.iverium.nl), webontwikkeling en vindbaarheid voor ondernemers in Groningen en Drenthe.
