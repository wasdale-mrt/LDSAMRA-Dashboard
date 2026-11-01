"""
Turn an Ordnance Survey grid reference into latitude and longitude (WGS84).

Accepts what the Grid ref column holds:
  - OS grid refs with letters: NY215072, NY 2150 0720, SD413993 (4 to 10 figures)
  - eastings and northings: 321500, 507200
  - latitude and longitude: 54.454, -3.211

Returns (lat, lon) or None. Never guesses: anything it cannot read is None,
and the build script lists it.
Pure Python, no internet. Same formulas as the report builder's map.
"""

import math
import re

# 100 km squares used in Cumbria and around, plus the rest of the grid letters.
def _square_offsets(letters):
    letters = letters.upper()
    if len(letters) != 2:
        return None
    alphabet = "ABCDEFGHJKLMNOPQRSTUVWXYZ"  # no I
    try:
        l1 = alphabet.index(letters[0])
        l2 = alphabet.index(letters[1])
    except ValueError:
        return None
    e100 = ((l1 - 2) % 5) * 5 + (l2 % 5)
    n100 = (19 - (l1 // 5) * 5) - (l2 // 5)
    if not (0 <= e100 <= 7 and 0 <= n100 <= 12):
        return None
    return e100, n100


def grid_to_en(ref):
    """'NY215072' -> (321500, 507200), placed at the centre of the square."""
    s = re.sub(r"\s+", "", str(ref)).upper()
    m = re.fullmatch(r"([A-Z]{2})(\d{4,10})", s)
    if not m or len(m.group(2)) % 2:
        return None
    off = _square_offsets(m.group(1))
    if not off:
        return None
    digits = m.group(2)
    half = len(digits) // 2
    scale = 10 ** (5 - half)
    e = int(digits[:half]) * scale + scale / 2
    n = int(digits[half:]) * scale + scale / 2
    return off[0] * 100000 + e, off[1] * 100000 + n


def en_to_osgb36(E, N):
    """National Grid eastings/northings -> OSGB36 lat/lon (degrees)."""
    a, b = 6377563.396, 6356256.909
    F0 = 0.9996012717
    lat0, lon0 = math.radians(49), math.radians(-2)
    N0, E0 = -100000, 400000
    e2 = 1 - (b * b) / (a * a)
    n = (a - b) / (a + b)
    lat, M = lat0, 0
    while True:
        lat = (N - N0 - M) / (a * F0) + lat
        Ma = (1 + n + 5 / 4 * n ** 2 + 5 / 4 * n ** 3) * (lat - lat0)
        Mb = (3 * n + 3 * n ** 2 + 21 / 8 * n ** 3) * math.sin(lat - lat0) * math.cos(lat + lat0)
        Mc = (15 / 8 * n ** 2 + 15 / 8 * n ** 3) * math.sin(2 * (lat - lat0)) * math.cos(2 * (lat + lat0))
        Md = 35 / 24 * n ** 3 * math.sin(3 * (lat - lat0)) * math.cos(3 * (lat + lat0))
        M = b * F0 * (Ma - Mb + Mc - Md)
        if abs(N - N0 - M) < 0.00001:
            break
    sinl, cosl, tanl = math.sin(lat), math.cos(lat), math.tan(lat)
    nu = a * F0 / math.sqrt(1 - e2 * sinl ** 2)
    rho = a * F0 * (1 - e2) / (1 - e2 * sinl ** 2) ** 1.5
    eta2 = nu / rho - 1
    VII = tanl / (2 * rho * nu)
    VIII = tanl / (24 * rho * nu ** 3) * (5 + 3 * tanl ** 2 + eta2 - 9 * tanl ** 2 * eta2)
    IX = tanl / (720 * rho * nu ** 5) * (61 + 90 * tanl ** 2 + 45 * tanl ** 4)
    X = 1 / (cosl * nu)
    XI = 1 / (cosl * 6 * nu ** 3) * (nu / rho + 2 * tanl ** 2)
    XII = 1 / (cosl * 120 * nu ** 5) * (5 + 28 * tanl ** 2 + 24 * tanl ** 4)
    XIIA = 1 / (cosl * 5040 * nu ** 7) * (61 + 662 * tanl ** 2 + 1320 * tanl ** 4 + 720 * tanl ** 6)
    dE = E - E0
    lat = lat - VII * dE ** 2 + VIII * dE ** 4 - IX * dE ** 6
    lon = lon0 + X * dE - XI * dE ** 3 + XII * dE ** 5 - XIIA * dE ** 7
    return math.degrees(lat), math.degrees(lon)


def osgb36_to_wgs84(lat, lon):
    """Helmert shift, about 100 m. Good to a few metres, plenty for a map dot."""
    a1, b1 = 6377563.396, 6356256.909
    a2, b2 = 6378137.000, 6356752.3142
    lat, lon = math.radians(lat), math.radians(lon)
    e1 = 1 - b1 ** 2 / a1 ** 2
    nu = a1 / math.sqrt(1 - e1 * math.sin(lat) ** 2)
    x = nu * math.cos(lat) * math.cos(lon)
    y = nu * math.cos(lat) * math.sin(lon)
    z = (1 - e1) * nu * math.sin(lat)
    tx, ty, tz = 446.448, -125.157, 542.060
    s = -20.4894e-6
    rx, ry, rz = (math.radians(v / 3600) for v in (0.1502, 0.2470, 0.8421))
    x2 = tx + (1 + s) * x - rz * y + ry * z
    y2 = ty + rz * x + (1 + s) * y - rx * z
    z2 = tz - ry * x + rx * y + (1 + s) * z
    e2 = 1 - b2 ** 2 / a2 ** 2
    p = math.sqrt(x2 ** 2 + y2 ** 2)
    lat2 = math.atan2(z2, p * (1 - e2))
    for _ in range(10):
        nu2 = a2 / math.sqrt(1 - e2 * math.sin(lat2) ** 2)
        lat2 = math.atan2(z2 + e2 * nu2 * math.sin(lat2), p)
    return math.degrees(lat2), math.degrees(math.atan2(y2, x2))


def parse_point(text):
    """Grid ref cell -> (lat, lon) in WGS84, or None if it cannot be read."""
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    en = grid_to_en(s)
    if en is None:
        nums = re.findall(r"-?\d+(?:\.\d+)?", s)
        if len(nums) == 2:
            a, b = float(nums[0]), float(nums[1])
            if abs(a) <= 90 and abs(b) <= 180 and ("." in nums[0] or "." in nums[1]):
                return round(a, 5), round(b, 5)
            if 0 <= a < 700000 and 0 <= b < 1300000 and a > 1000 and b > 1000:
                en = (a, b)
    if en is None:
        return None
    lat, lon = osgb36_to_wgs84(*en_to_osgb36(*en))
    return round(lat, 5), round(lon, 5)


if __name__ == "__main__":
    # Scafell Pike summit, NY 21543 07216 -> about 54.4542, -3.2116
    print(parse_point("NY2154307216"))
