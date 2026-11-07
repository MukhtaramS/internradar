"""Turn messy location strings into (city, country) pairs and decide what is in Europe.

Careers sites write locations in many shapes: "London, UK", "Zürich, Switzerland",
"Germany, Munich", "Frankenthal, Rhineland-Palatinate, DEU", "Cambridge, MA",
"Remote - EMEA", "LDN". Each string is split into parts and resolved in this order:

1. An explicit country (name, alias, ISO3, or an ISO2 code that is not also a
   US state code) wins.
2. A US state or Canadian province code means North America, unless the code
   is also the ISO2 of the country a known European city in the string is in
   ("Munich, DE" stays Germany, "Cambridge, MA" becomes the US).
3. A known European city gives its country.
4. "Europe", "EMEA" or "EU" with no country means somewhere in Europe.

Anything else is unknown and does not count as Europe.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Optional

# code: (display name, flag, aliases)  -- aliases include ISO3 codes
EUROPE = {
    "GB": ("United Kingdom", "🇬🇧", ["united kingdom", "uk", "u.k.", "england", "scotland", "wales",
                                      "northern ireland", "great britain", "britain", "gbr"]),
    "IE": ("Ireland", "🇮🇪", ["ireland", "irl", "republic of ireland"]),
    "CH": ("Switzerland", "🇨🇭", ["switzerland", "schweiz", "suisse", "svizzera", "che"]),
    "DE": ("Germany", "🇩🇪", ["germany", "deutschland", "deu"]),
    "FR": ("France", "🇫🇷", ["france", "fra"]),
    "NL": ("Netherlands", "🇳🇱", ["netherlands", "the netherlands", "holland", "nederland", "nld"]),
    "BE": ("Belgium", "🇧🇪", ["belgium", "belgique", "belgie", "bel"]),
    "LU": ("Luxembourg", "🇱🇺", ["luxembourg", "lux"]),
    "ES": ("Spain", "🇪🇸", ["spain", "espana", "esp"]),
    "PT": ("Portugal", "🇵🇹", ["portugal", "prt"]),
    "IT": ("Italy", "🇮🇹", ["italy", "italia", "ita"]),
    "AT": ("Austria", "🇦🇹", ["austria", "osterreich", "aut"]),
    "DK": ("Denmark", "🇩🇰", ["denmark", "danmark", "dnk"]),
    "SE": ("Sweden", "🇸🇪", ["sweden", "sverige", "swe"]),
    "NO": ("Norway", "🇳🇴", ["norway", "norge", "nor"]),
    "FI": ("Finland", "🇫🇮", ["finland", "suomi", "fin"]),
    "IS": ("Iceland", "🇮🇸", ["iceland", "isl"]),
    "PL": ("Poland", "🇵🇱", ["poland", "polska", "pol"]),
    "CZ": ("Czechia", "🇨🇿", ["czechia", "czech republic", "cze"]),
    "SK": ("Slovakia", "🇸🇰", ["slovakia", "svk"]),
    "HU": ("Hungary", "🇭🇺", ["hungary", "hun"]),
    "RO": ("Romania", "🇷🇴", ["romania", "rou"]),
    "BG": ("Bulgaria", "🇧🇬", ["bulgaria", "bgr"]),
    "GR": ("Greece", "🇬🇷", ["greece", "grc"]),
    "HR": ("Croatia", "🇭🇷", ["croatia", "hrv"]),
    "SI": ("Slovenia", "🇸🇮", ["slovenia", "svn"]),
    "RS": ("Serbia", "🇷🇸", ["serbia", "srb"]),
    "EE": ("Estonia", "🇪🇪", ["estonia", "est"]),
    "LV": ("Latvia", "🇱🇻", ["latvia", "lva"]),
    "LT": ("Lithuania", "🇱🇹", ["lithuania", "ltu"]),
    "CY": ("Cyprus", "🇨🇾", ["cyprus", "cyp"]),
    "MT": ("Malta", "🇲🇹", ["malta", "mlt"]),
    "UA": ("Ukraine", "🇺🇦", ["ukraine", "ukr"]),
    "TR": ("Turkey", "🇹🇷", ["turkey", "turkiye", "tur"]),
}

# Recognised only so they can be ruled out.
NON_EUROPE = {
    "US": ["united states", "united states of america", "usa", "u.s.", "u.s.a.", "us"],
    "CA": ["canada", "can"], "MX": ["mexico", "mex"], "BR": ["brazil", "brasil", "bra"],
    "AR": ["argentina", "arg"], "CL": ["chile", "chl"], "CO": ["colombia", "col"],
    "IN": ["india", "ind"], "CN": ["china", "chn", "prc"], "JP": ["japan", "jpn"],
    "KR": ["south korea", "korea", "republic of korea", "kor"], "SG": ["singapore", "sgp"],
    "HK": ["hong kong", "hkg", "hong kong sar"], "TW": ["taiwan", "twn"],
    "AU": ["australia", "aus"], "NZ": ["new zealand", "nzl"], "IL": ["israel", "isr"],
    "AE": ["united arab emirates", "uae", "are"], "SA": ["saudi arabia", "sau"],
    "QA": ["qatar", "qat"], "ZA": ["south africa", "zaf"], "EG": ["egypt", "egy"],
    "MA": ["morocco", "mar"], "NG": ["nigeria", "nga"], "KE": ["kenya", "ken"],
    "MY": ["malaysia", "mys"], "ID": ["indonesia", "idn"], "TH": ["thailand", "tha"],
    "VN": ["vietnam", "vnm"], "PH": ["philippines", "phl"], "CR": ["costa rica", "cri"],
}

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT",
    "VT", "VA", "WA", "WV", "WI", "WY",
}
US_STATE_NAMES = {
    "california", "washington", "new york", "texas", "massachusetts", "illinois",
    "pennsylvania", "colorado", "georgia", "virginia", "oregon", "new jersey", "florida",
    "north carolina", "arizona", "utah", "michigan", "minnesota", "maryland", "ohio",
}
CA_PROVINCES = {"ON", "QC", "BC", "AB", "MB", "NS"}

# City -> country. Keys are accent-free lower case; extra spellings point at the same country.
CITIES = {
    "GB": ["london", "ldn", "cambridge", "oxford", "edinburgh", "manchester", "bristol", "reading",
           "glasgow", "belfast", "leeds", "birmingham", "cheltenham", "slough", "milton keynes",
           "newcastle", "sheffield", "nottingham", "southampton", "york", "brighton", "guildford"],
    "IE": ["dublin", "cork", "galway", "limerick", "shannon"],
    "CH": ["zurich", "geneva", "geneve", "basel", "lausanne", "zug", "bern", "lugano",
           "ruschlikon", "winterthur", "baar", "schlieren"],
    "DE": ["berlin", "munich", "munchen", "hamburg", "frankfurt", "frankfurt am main", "cologne",
           "koln", "stuttgart", "dusseldorf", "dresden", "aachen", "karlsruhe", "nuremberg",
           "nurnberg", "darmstadt", "heidelberg", "tubingen", "ehningen", "boblingen", "walldorf",
           "leipzig", "bonn", "hannover", "hanover", "erlangen", "jena", "ulm", "freiburg",
           "potsdam", "mannheim", "garching", "saarbrucken", "frankenthal", "porz-wahn"],
    "FR": ["paris", "lyon", "grenoble", "toulouse", "nice", "sophia antipolis", "marseille",
           "rennes", "lille", "bordeaux", "nantes", "montpellier", "saclay", "palaiseau"],
    "NL": ["amsterdam", "rotterdam", "eindhoven", "utrecht", "the hague", "den haag", "delft",
           "noordwijk", "leiden", "groningen", "veldhoven"],
    "BE": ["brussels", "bruxelles", "ghent", "gent", "antwerp", "leuven", "mechelen"],
    "LU": ["luxembourg", "luxembourg city"],
    "ES": ["madrid", "barcelona", "malaga", "valencia", "seville", "sevilla", "bilbao",
           "villanueva de la canada"],
    "PT": ["lisbon", "lisboa", "porto", "braga"],
    "IT": ["milan", "milano", "rome", "roma", "turin", "torino", "pisa", "bologna", "naples",
           "napoli", "novara", "frascati", "genoa"],
    "AT": ["vienna", "wien", "graz", "linz", "innsbruck", "salzburg"],
    "DK": ["copenhagen", "kobenhavn", "aarhus"],
    "SE": ["stockholm", "gothenburg", "goteborg", "malmo", "lund", "uppsala", "linkoping"],
    "NO": ["oslo", "trondheim", "bergen"],
    "FI": ["helsinki", "espoo", "tampere", "oulu"],
    "IS": ["reykjavik"],
    "PL": ["warsaw", "warszawa", "krakow", "wroclaw", "gdansk", "poznan", "lodz", "katowice"],
    "CZ": ["prague", "praha", "brno"],
    "SK": ["bratislava"],
    "HU": ["budapest"],
    "RO": ["bucharest", "bucuresti", "cluj", "cluj-napoca", "iasi", "timisoara", "brasov"],
    "BG": ["sofia"],
    "GR": ["athens", "thessaloniki"],
    "HR": ["zagreb"],
    "SI": ["ljubljana"],
    "RS": ["belgrade", "novi sad"],
    "EE": ["tallinn", "tartu"],
    "LV": ["riga"],
    "LT": ["vilnius", "kaunas"],
    "UA": ["kyiv", "kiev", "lviv"],
    "TR": ["istanbul", "ankara"],
    "CY": ["nicosia", "limassol"],
    "MT": ["valletta"],
}

# Pretty names for cities whose source spelling varies.
CITY_DISPLAY = {
    "ldn": "London", "munchen": "Munich", "koln": "Cologne", "nurnberg": "Nuremberg",
    "geneve": "Geneva", "den haag": "The Hague", "bruxelles": "Brussels", "gent": "Ghent",
    "lisboa": "Lisbon", "milano": "Milan", "roma": "Rome", "torino": "Turin", "napoli": "Naples",
    "wien": "Vienna", "kobenhavn": "Copenhagen", "goteborg": "Gothenburg", "warszawa": "Warsaw",
    "praha": "Prague", "bucuresti": "Bucharest", "cluj-napoca": "Cluj", "kiev": "Kyiv",
    "frankfurt am main": "Frankfurt", "hanover": "Hannover", "sevilla": "Seville",
    "luxembourg city": "Luxembourg", "zurich": "Zurich", "malmo": "Malmo",
}

EUROPE_WORDS = {"europe", "emea", "eu", "european union", "europe remote", "remote europe"}
REMOTE_RE = re.compile(r"\bremote\b|\banywhere\b", re.I)


def _plain(text: str) -> str:
    """Lower case, accents removed, spacing tidied."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


_COUNTRY_ALIAS = {}
for _code, (_name, _flag, _aliases) in EUROPE.items():
    for _a in _aliases:
        _COUNTRY_ALIAS[_a] = _code
for _code, _aliases in NON_EUROPE.items():
    for _a in _aliases:
        _COUNTRY_ALIAS[_a] = _code
_CITY = {c: code for code, cities in CITIES.items() for c in cities}
_ISO2 = set(EUROPE) | set(NON_EUROPE)


@dataclass(frozen=True)
class Place:
    city: Optional[str]
    country: Optional[str]   # ISO2, or None when unknown
    europe_wide: bool = False  # "Remote - EMEA" and similar
    remote: bool = False

    @property
    def in_europe(self) -> bool:
        return self.country in EUROPE or (self.country is None and self.europe_wide)


def _parts(text: str) -> List[str]:
    return [p.strip() for p in re.split(r"[,()|/]| - | – ", text) if p and p.strip()]


def parse_location(text: str) -> Place:
    raw_parts = _parts(text or "")
    parts = [_plain(p) for p in raw_parts]
    remote = bool(REMOTE_RE.search(text or ""))

    city_key = next((p for p in parts if p in _CITY), None)
    city_country = _CITY.get(city_key) if city_key else None
    city = CITY_DISPLAY.get(city_key, city_key.title()) if city_key else None

    country = None
    for raw, p in zip(raw_parts, parts):
        if p in _COUNTRY_ALIAS and not (len(p) == 2 and raw.upper() in US_STATES):
            # "us" must be the country; two-letter aliases like "uk" are fine as written
            country = _COUNTRY_ALIAS[p]
            break
        if len(raw) == 2 and raw.isupper() and raw in _ISO2 and raw not in US_STATES \
                and raw not in CA_PROVINCES:
            country = raw
            break
    if country:
        return Place(city if city_country == country else None, country, False, remote)

    for raw, p in zip(raw_parts, parts):
        code = raw.upper() if len(raw) == 2 else None
        if code in CA_PROVINCES:
            return Place(None, "CA", False, remote)
        if (code in US_STATES and raw.isupper()) or p in US_STATE_NAMES:
            if city_country and code == city_country:
                return Place(city, city_country, False, remote)
            return Place(None, "US", False, remote)

    if city_country:
        return Place(city, city_country, False, remote)
    if any(p in EUROPE_WORDS for p in parts):
        return Place(None, None, True, remote)
    return Place(None, None, False, remote)


def split_locations(values: Iterable[str]) -> List[str]:
    """Split strings that hold several locations ("London; Paris", "Zurich or Remote")."""
    out = []
    for v in values:
        for piece in re.split(r";| \| | or ", v or ""):
            piece = piece.strip()
            if piece and piece not in out:
                out.append(piece)
    return out


def parse_locations(values: Iterable[str]) -> List[Place]:
    return [parse_location(v) for v in split_locations(values)]


def country_name(code: str) -> str:
    return EUROPE[code][0] if code in EUROPE else code


def country_flag(code: str) -> str:
    return EUROPE[code][1] if code in EUROPE else ""
