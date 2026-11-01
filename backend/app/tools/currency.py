import re
import httpx

from ..config import settings

# ISO 3166-1 alpha-2 country code to ISO 4217 currency code
COUNTRY_CODE_TO_CURRENCY: dict[str, str] = {
    # India
    "IN": "INR",
    # United States
    "US": "USD",
    # United Kingdom
    "GB": "GBP",
    "UK": "GBP",
    # Eurozone
    "DE": "EUR", "FR": "EUR", "IT": "EUR", "ES": "EUR", "NL": "EUR",
    "BE": "EUR", "AT": "EUR", "IE": "EUR", "PT": "EUR", "GR": "EUR",
    "FI": "EUR", "SK": "EUR", "SI": "EUR", "LU": "EUR", "CY": "EUR",
    "MT": "EUR", "EE": "EUR", "LV": "EUR", "LT": "EUR", "HR": "EUR",
    # Other Americas
    "CA": "CAD", "MX": "MXN", "BR": "BRL", "AR": "ARS", "CL": "CLP", "CO": "COP",
    # Asia & Oceania
    "JP": "JPY", "AU": "AUD", "NZ": "NZD", "CN": "CNY", "HK": "HKD",
    "SG": "SGD", "KR": "KRW", "TH": "THB", "MY": "MYR", "ID": "IDR",
    "PH": "PHP", "VN": "VND", "TW": "TWD", "PK": "PKR", "BD": "BDT",
    "LK": "LKR", "NP": "NPR",
    # Middle East
    "AE": "AED", "SA": "SAR", "QA": "QAR", "IL": "ILS", "OM": "OMR", "KW": "KWD", "BH": "BHD",
    # Europe non-Euro
    "CH": "CHF", "SE": "SEK", "NO": "NOK", "DK": "DKK", "PL": "PLN",
    "CZ": "CZK", "HU": "HUF", "RO": "RON", "BG": "BGN", "TR": "TRY",
    # Africa
    "ZA": "ZAR", "EG": "EGP", "NG": "NGN", "KE": "KES", "MA": "MAD",
}

# Airport IATA code to currency code
IATA_TO_CURRENCY: dict[str, str] = {
    # India
    "BLR": "INR", "DEL": "INR", "BOM": "INR", "MAA": "INR", "HYD": "INR",
    "CCU": "INR", "AMD": "INR", "COK": "INR", "PNQ": "INR", "GOI": "INR",
    "GOX": "INR", "JAI": "INR", "LKO": "INR", "TRV": "INR", "IXC": "INR",
    "GAU": "INR", "PAT": "INR", "BBI": "INR", "SXR": "INR", "IXB": "INR",
    # UK
    "LHR": "GBP", "LGW": "GBP", "STN": "GBP", "LCY": "GBP", "LTN": "GBP",
    "MAN": "GBP", "EDI": "GBP", "BHX": "GBP", "GLA": "GBP", "BRS": "GBP",
    # USA
    "JFK": "USD", "EWR": "USD", "LGA": "USD", "LAX": "USD", "SFO": "USD",
    "ORD": "USD", "DFW": "USD", "MIA": "USD", "SEA": "USD", "BOS": "USD",
    "ATL": "USD", "DEN": "USD", "IAD": "USD", "DCA": "USD",
    # Eurozone
    "AMS": "EUR", "CDG": "EUR", "ORY": "EUR", "FRA": "EUR", "MUC": "EUR",
    "BER": "EUR", "MAD": "EUR", "BCN": "EUR", "FCO": "EUR", "MXP": "EUR",
    "VIE": "EUR", "BRU": "EUR", "DUB": "EUR", "LIS": "EUR", "ATH": "EUR", "HEL": "EUR",
    # Japan
    "HND": "JPY", "NRT": "JPY", "KIX": "JPY", "ITM": "JPY", "CTS": "JPY", "FUK": "JPY",
    # Canada
    "YYZ": "CAD", "YVR": "CAD", "YUL": "CAD", "YYC": "CAD",
    # Australia & NZ
    "SYD": "AUD", "MEL": "AUD", "BNE": "AUD", "PER": "AUD", "ADL": "AUD",
    "AKL": "NZD", "WLG": "NZD", "CHC": "NZD",
    # Middle East
    "DXB": "AED", "AUH": "AED", "DOH": "QAR", "RUH": "SAR", "JED": "SAR", "TLV": "ILS",
    # Others
    "SIN": "SGD", "BKK": "THB", "DMK": "THB", "KUL": "MYR", "ICN": "KRW", "GMP": "KRW",
    "HKG": "HKD", "PVG": "CNY", "PEK": "CNY", "PKX": "CNY", "CAN": "CNY",
    "ZRH": "CHF", "GVA": "CHF",
}

# Major cities / keywords to currency
CITY_TO_CURRENCY: dict[str, str] = {
    # India
    "bangalore": "INR", "bengaluru": "INR", "delhi": "INR", "new delhi": "INR",
    "mumbai": "INR", "bombay": "INR", "chennai": "INR", "madras": "INR",
    "hyderabad": "INR", "kolkata": "INR", "calcutta": "INR", "ahmedabad": "INR",
    "pune": "INR", "kochi": "INR", "cochin": "INR", "goa": "INR", "jaipur": "INR",
    "lucknow": "INR", "chandigarh": "INR", "trivandrum": "INR", "thiruvananthapuram": "INR",
    "india": "INR",
    # UK
    "london": "GBP", "manchester": "GBP", "edinburgh": "GBP", "birmingham": "GBP",
    "glasgow": "GBP", "bristol": "GBP", "liverpool": "GBP", "oxford": "GBP",
    "cambridge": "GBP", "united kingdom": "GBP", "uk": "GBP", "england": "GBP", "scotland": "GBP",
    # Eurozone
    "amsterdam": "EUR", "paris": "EUR", "berlin": "EUR", "munich": "EUR",
    "frankfurt": "EUR", "madrid": "EUR", "barcelona": "EUR", "rome": "EUR",
    "milan": "EUR", "vienna": "EUR", "brussels": "EUR", "dublin": "EUR",
    "lisbon": "EUR", "athens": "EUR", "helsinki": "EUR", "germany": "EUR",
    "france": "EUR", "italy": "EUR", "spain": "EUR", "netherlands": "EUR",
    "ireland": "EUR", "portugal": "EUR", "austria": "EUR", "greece": "EUR",
    # USA
    "new york": "USD", "nyc": "USD", "los angeles": "USD", "san francisco": "USD",
    "chicago": "USD", "miami": "USD", "seattle": "USD", "boston": "USD",
    "austin": "USD", "houston": "USD", "dallas": "USD", "united states": "USD", "usa": "USD",
    # Japan
    "tokyo": "JPY", "osaka": "JPY", "kyoto": "JPY", "yokohama": "JPY", "sapporo": "JPY", "japan": "JPY",
    # Canada
    "toronto": "CAD", "vancouver": "CAD", "montreal": "CAD", "calgary": "CAD", "ottawa": "CAD", "canada": "CAD",
    # Australia & NZ
    "sydney": "AUD", "melbourne": "AUD", "brisbane": "AUD", "perth": "AUD", "australia": "AUD",
    "auckland": "NZD", "wellington": "NZD", "new zealand": "NZD",
    # Middle East
    "dubai": "AED", "abu dhabi": "AED", "uae": "AED", "doha": "QAR", "qatar": "QAR",
    "riyadh": "SAR", "jeddah": "SAR", "saudi arabia": "SAR",
    # Others
    "singapore": "SGD", "bangkok": "THB", "thailand": "THB",
    "kuala lumpur": "MYR", "malaysia": "MYR", "seoul": "KRW", "south korea": "KRW",
    "hong kong": "HKD", "shanghai": "CNY", "beijing": "CNY", "china": "CNY",
    "zurich": "CHF", "geneva": "CHF", "switzerland": "CHF",
}

# Reliable fallback rates vs USD in case external FX service is offline or currency not in ECB
APPROX_USD_RATES: dict[str, float] = {
    "USD": 1.0,
    "INR": 86.0,
    "EUR": 0.92,
    "GBP": 0.78,
    "JPY": 152.0,
    "CAD": 1.38,
    "AUD": 1.52,
    "CHF": 0.88,
    "AED": 3.67,
    "SAR": 3.75,
    "QAR": 3.64,
    "SGD": 1.34,
    "CNY": 7.23,
    "THB": 34.5,
    "KRW": 1380.0,
    "BRL": 5.75,
    "NZD": 1.68,
    "SEK": 10.6,
    "NOK": 10.9,
    "DKK": 6.86,
    "PLN": 4.0,
    "TRY": 34.5,
    "ZAR": 17.6,
}


def resolve_currency_for_origin(
    origin: str | None = None,
    iata: str | None = None,
    country_code: str | None = None,
) -> str | None:
    """Determine the ISO 4217 currency code for a traveler's origin location."""
    if country_code:
        cc = country_code.strip().upper()
        if cc in COUNTRY_CODE_TO_CURRENCY:
            return COUNTRY_CODE_TO_CURRENCY[cc]

    if iata:
        code = iata.strip().upper()
        if code in IATA_TO_CURRENCY:
            return IATA_TO_CURRENCY[code]

    if origin:
        orig = origin.strip().lower()
        if orig in CITY_TO_CURRENCY:
            return CITY_TO_CURRENCY[orig]
        for name, curr in CITY_TO_CURRENCY.items():
            if re.search(rf"\b{re.escape(name)}\b", orig):
                return curr

    return None


async def get_rate(base: str, quote: str) -> float:
    """Latest FX rate from Frankfurter (ECB data, free, no key) with robust fallback."""
    b, q = (base or "USD").strip().upper(), (quote or "USD").strip().upper()
    if b == q:
        return 1.0

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as c:
            r = await c.get("https://api.frankfurter.dev/v1/latest", params={"base": b, "symbols": q})
            if r.status_code == 200:
                data = r.json()
                if "rates" in data and q in data["rates"]:
                    return float(data["rates"][q])
    except Exception:
        pass

    # Fallback to approximate rates if Frankfurter is down or currency not supported
    if b in APPROX_USD_RATES and q in APPROX_USD_RATES:
        return APPROX_USD_RATES[q] / APPROX_USD_RATES[b]

    return 1.0
