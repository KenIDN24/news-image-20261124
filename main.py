# news-image-20261124: a one-page newspaper front page summing up
# Tuesday 24 November 2026. Pure Python 3 stdlib: draws the whole
# page procedurally (my own 5x7 bitmap font stored as integer bit
# masks, flat vector shapes) and writes a deterministic PNG to
# /output/entry.png (or $MAKEFUN_OUTPUT_DIR). No network, no clock,
# no randomness: two runs are byte-identical.

import hashlib
import os
import struct
import zlib

W, H = 1024, 1024

PAPER = (247, 242, 231)
INK = (26, 26, 26)
GREY = (107, 101, 88)
RULE = (201, 191, 166)
RED = (176, 32, 32)
BLUE = (30, 62, 118)
TEAL = (15, 110, 108)
ORANGE = (214, 88, 18)
GOLD = (150, 116, 0)
PANEL = (234, 227, 210)
SMOKE = (154, 147, 138)
SKY = (214, 224, 228)
BLDG = (74, 72, 68)
FLAME = (232, 110, 20)


class Page:
    """A plain RGB canvas with tiny vector drawing helpers."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def put(self, x, y, col):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(col)

    def rect(self, x, y, w, h, col):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        row = bytes(col) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + (x1 - x0) * 3] = row

    def hline(self, x, y, w, col, t=1):
        self.rect(x, y, w, t, col)

    def vline(self, x, y, h, col, t=1):
        self.rect(x, y, t, h, col)

    def line(self, x0, y0, x1, y1, col):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.put(x0, y0, col)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, col):
        for yy in range(cy - r, cy + r + 1):
            half = int((r * r - (yy - cy) ** 2) ** 0.5)
            self.rect(cx - half, yy, half * 2 + 1, 1, col)

    def triangle(self, ax, ay, bx, by, cx, cy, col):
        # Scanline fill: walk the edges and fill each row.
        ys = sorted(((ay, ax), (by, bx), (cy, cx)))
        (y0, xa), (y1, xb), (y2, xc) = ys
        if y0 == y2:
            return
        for y in range(y0, y2 + 1):
            xs = []
            for (ya, x1), (yb, x2) in (((y0, xa), (y1, xb)),
                                       ((y1, xb), (y2, xc)),
                                       ((y0, xa), (y2, xc))):
                if ya == yb:
                    continue
                if min(ya, yb) <= y <= max(ya, yb):
                    xs.append(x1 + (x2 - x1) * (y - ya) / (yb - ya))
            if len(xs) >= 2:
                self.rect(int(min(xs)), y, int(max(xs)) - int(min(xs)) + 1,
                          1, col)


def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(page, path):
    raw = bytearray()
    stride = page.w * 3
    for y in range(page.h):
        raw.append(0)
        raw += page.px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", page.w, page.h, 8, 2, 0, 0, 0)
    blob = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(blob)
    return blob

# My own 5x7 bitmap font. Each glyph is 7 rows; each row is a 5-bit
# mask, bit 4 = leftmost cell. Designed from scratch for this page:
# capitals are full height, lower case sits on rows 2-6 with
# descenders on the last row, digits are full height.
FONT = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "a": (0x00, 0x00, 0x0E, 0x01, 0x0F, 0x11, 0x0F),
    "b": (0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x1E),
    "c": (0x00, 0x00, 0x0E, 0x10, 0x10, 0x10, 0x0E),
    "d": (0x01, 0x01, 0x0F, 0x11, 0x11, 0x11, 0x0F),
    "e": (0x00, 0x00, 0x0E, 0x11, 0x1F, 0x10, 0x0E),
    "f": (0x06, 0x08, 0x08, 0x1E, 0x08, 0x08, 0x08),
    "g": (0x00, 0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01),
    "h": (0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x11),
    "i": (0x04, 0x00, 0x0C, 0x04, 0x04, 0x04, 0x0E),
    "j": (0x02, 0x00, 0x06, 0x02, 0x02, 0x12, 0x0C),
    "k": (0x10, 0x10, 0x12, 0x14, 0x18, 0x14, 0x12),
    "l": (0x0C, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "m": (0x00, 0x00, 0x1A, 0x15, 0x15, 0x15, 0x15),
    "n": (0x00, 0x00, 0x1E, 0x11, 0x11, 0x11, 0x11),
    "o": (0x00, 0x00, 0x0E, 0x11, 0x11, 0x11, 0x0E),
    "p": (0x00, 0x00, 0x1E, 0x11, 0x11, 0x1E, 0x10),
    "q": (0x00, 0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01),
    "r": (0x00, 0x00, 0x16, 0x19, 0x10, 0x10, 0x10),
    "s": (0x00, 0x00, 0x0F, 0x10, 0x0E, 0x01, 0x1E),
    "t": (0x04, 0x04, 0x1F, 0x04, 0x04, 0x04, 0x03),
    "u": (0x00, 0x00, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "v": (0x00, 0x00, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "w": (0x00, 0x00, 0x11, 0x11, 0x15, 0x15, 0x0A),
    "x": (0x00, 0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11),
    "y": (0x00, 0x00, 0x11, 0x11, 0x0F, 0x01, 0x0E),
    "z": (0x00, 0x00, 0x1F, 0x02, 0x04, 0x08, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ",": (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    ":": (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    ";": (0, 0x0C, 0x0C, 0, 0x0C, 0x04, 0x08),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04),
    "-": (0, 0, 0, 0x1F, 0, 0, 0),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    '"': (0x0A, 0x0A, 0x0A, 0, 0, 0, 0),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "/": (0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10),
    "%": (0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13),
    "+": (0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "*": (0, 0x04, 0x15, 0x0E, 0x15, 0x04, 0),
    "#": (0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A),
    "=": (0, 0, 0x1F, 0, 0x1F, 0, 0),
    "[": (0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E),
    "]": (0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E),
}


def glyph_w(scale):
    return 6 * scale


def text_w(s, scale):
    return len(s) * glyph_w(scale) - scale


def draw_char(pg, x, y, ch, scale, col):
    rows = FONT.get(ch)
    if rows is None:
        return
    for r in range(7):
        bits = rows[r]
        if not bits:
            continue
        for c in range(5):
            if bits & (0x10 >> c):
                pg.rect(x + c * scale, y + r * scale, scale, scale, col)


def draw_text(pg, x, y, s, scale, col):
    cx = x
    for ch in s:
        draw_char(pg, cx, y, ch, scale, col)
        cx += glyph_w(scale)
    return cx


def wrap(s, width, scale):
    """Greedy word wrap; returns a list of lines fitting width px."""
    words = s.split(" ")
    lines = []
    cur = ""
    for wd in words:
        trial = wd if not cur else cur + " " + wd
        if text_w(trial, scale) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_para(pg, x, y, s, width, scale, col, leading=None):
    if leading is None:
        leading = 7 * scale + 3
    for ln in wrap(s, width, scale):
        draw_text(pg, x, y, ln, scale, col)
        y += leading
    return y


# ---- The day's stories (all reported on Tuesday 24 November 2026;
# see SOURCES.md for the outlets). Figures are as reported. ----

LEAD_KICKER = "INDONESIA"
LEAD_HEAD = ["FACTORY FIRE TOLL", "RISES TO 24"]
LEAD_BODY = (
    "Rescuers kept digging through the ruins of a candy factory in "
    "Cikande, Banten, as the death toll rose to at least 24, with "
    "dozens still missing after Saturday's blaze. Officials said "
    "the search would go on through the night."
)
LEAD_STAT = "24 DEAD - DOZENS MISSING - CIKANDE, BANTEN"

MARKETS_KICKER = "MARKETS"
MARKETS_HEAD = ["NVIDIA SOARS 31% AS", "HUANG RETURNS"]
MARKETS_BODY = (
    "Nvidia shares jumped 31%, their best day since 2003, adding "
    "$952bn in value after the board reinstated Jensen Huang as "
    "chief executive, 11 days after he quit. The Nasdaq rose 6%."
)

CLIMATE_KICKER = "CLIMATE"
CLIMATE_HEAD = ["COP31 ENDS WITH", "NO DEAL"]
CLIMATE_BODY = (
    "Climate talks in Antalya collapsed with no deal on fossil "
    "fuels after the longest COP ever. The draft pact dropped "
    "every mention of coal, oil and gas; talks may be suspended "
    "until next year."
)

WAR_KICKER = "WAR IN EUROPE"
WAR_HEAD = ["KYIV REGION HIT IN", "OVERNIGHT STRIKES"]
WAR_BODY = (
    "Russian drones and missiles struck the Kyiv region, killing "
    "several people and hitting a home in the village of Dymer. "
    "Kyiv claims it sank a Russian warship off the coast of Libya."
)

JUSTICE_KICKER = "JUSTICE"
JUSTICE_HEAD = ["UK NAMES ROHINGYA", "GENOCIDE"]
JUSTICE_BODY = (
    "Britain formally recognised the Rohingya genocide and "
    "sanctioned five Myanmar generals after the world court ruled "
    "Myanmar guilty. London also pledged 5m pounds in aid."
)

BRIEF = [
    ("INDIA-NEPAL", "Modi and Shah sign eight deals; Delhi offers Rs 15,000 crore."),
    ("SEOUL", "South Korea names a new foreign minister and spy chief."),
    ("CHINA", "Beijing sets 2030 targets for elderly care and childcare."),
    ("MARKETS", "Sensex falls 1,484; the Dow jumps 1,448 as tech rallies."),
    ("CHESS", "Gukesh opens his world title defence against Sindarov."),
    ("SKY", "A supermoon meets the Pleiades, the Seven Sisters, tonight."),
    ("TECH", "Waymo pulls driverless taxis from all US freeways."),
    ("WASHINGTON", "Trump says he pressed Nvidia to bring Huang back."),
]

SPORT = "SPORT: INDIA v NEW ZEALAND DRAW FIRST TEST - NZ 239-5 IN WELLINGTON"

MX = 36          # left margin
CW = 952         # content width (36..988)
COLW = 466       # half-column width
GAP = 20


def rule(pg, y, col=RULE, t=1):
    pg.hline(MX, y, CW, col, t)


def kicker(pg, x, y, text, col):
    draw_text(pg, x, y, text, 2, col)
    return y + 7 * 2 + 4


def headline(pg, x, y, lines, scale, col=INK):
    for ln in lines:
        draw_text(pg, x, y, ln, scale, col)
        y += 7 * scale + 3
    return y


def story(pg, x, y, width, kick, kcol, head, body, hscale=3):
    y = kicker(pg, x, y, kick, kcol)
    y = headline(pg, x, y, head, hscale)
    y = draw_para(pg, x, y + 4, body, width, 2, INK)
    return y


def factory_picture(pg, x, y, w, h):
    """A candy factory at dusk: sheds, chimneys, smoke, one flame."""
    pg.rect(x, y, w, h, SKY)
    pg.rect(x, y + h - 46, w, 46, (196, 188, 170))
    # main shed
    pg.rect(x + 28, y + h - 132, 150, 86, BLDG)
    pg.rect(x + 28, y + h - 132, 150, 10, (52, 50, 46))
    # second shed
    pg.rect(x + 178, y + h - 108, 96, 62, (94, 91, 86))
    # windows, dark
    for wx in (x + 44, x + 84, x + 124):
        pg.rect(wx, y + h - 104, 22, 26, (30, 30, 34))
    pg.rect(x + 196, y + h - 88, 18, 20, (30, 30, 34))
    pg.rect(x + 236, y + h - 88, 18, 20, (30, 30, 34))
    # chimneys
    pg.rect(x + 52, y + 42, 18, 92, (60, 58, 54))
    pg.rect(x + 108, y + 58, 18, 76, (60, 58, 54))
    # smoke puffs drifting up and right (kept inside the frame)
    for cx, cy, r in ((x + 66, y + 36, 13), (x + 82, y + 22, 16),
                      (x + 104, y + 14, 12), (x + 122, y + 52, 11),
                      (x + 138, y + 38, 14), (x + 158, y + 26, 11)):
        pg.disc(cx, cy, r, SMOKE)
    # flame at the foot of the main shed
    pg.triangle(x + 190, y + h - 46, x + 214, y + h - 46,
                x + 202, y + h - 92, FLAME)
    pg.triangle(x + 196, y + h - 46, x + 210, y + h - 46,
                x + 203, y + h - 74, (255, 190, 40))
    # frame
    pg.rect(x, y, w, 2, INK)
    pg.rect(x, y + h - 2, w, 2, INK)
    pg.rect(x, y, 2, h, INK)
    pg.rect(x + w - 2, y, 2, h, INK)


def build_page():
    pg = Page(W, H, PAPER)

    # ---- Masthead ----
    title = "THE WORLD TODAY"
    draw_text(pg, (W - text_w(title, 6)) // 2, 18, title, 6, INK)
    pg.hline(MX, 76, CW, INK, 2)
    date = "TUESDAY, 24 NOVEMBER 2026"
    draw_text(pg, (W - text_w(date, 2)) // 2, 86, date, 2, INK)
    tag = "ONE DAY'S NEWS FROM AROUND THE WORLD"
    draw_text(pg, (W - text_w(tag, 2)) // 2, 108, tag, 2, GREY)
    pg.hline(MX, 128, CW, INK, 4)
    pg.hline(MX, 135, CW, INK, 1)

    # ---- Row A: lead story + factory picture ----
    y = 148
    kicker(pg, MX, y, LEAD_KICKER, RED)
    y = headline(pg, MX, y + 18, LEAD_HEAD, 4)
    y = draw_para(pg, MX, y + 6, LEAD_BODY, 632, 2, INK)
    draw_text(pg, MX, y + 10, LEAD_STAT, 2, RED)
    pic_x = 684
    pic_y = 148
    pic_h = 266
    factory_picture(pg, pic_x, pic_y, 304, pic_h)
    cap = ["A CANDY FACTORY", "IN CIKANDE, BANTEN"]
    cy = pic_y + pic_h + 10
    for ln in cap:
        draw_text(pg, pic_x, cy, ln, 2, GREY)
        cy += 17

    # ---- Row B: markets + climate ----
    rule(pg, 440)
    y = 452
    story(pg, MX, y, COLW, MARKETS_KICKER, BLUE, MARKETS_HEAD,
          MARKETS_BODY)
    story(pg, MX + COLW + GAP, y, COLW, CLIMATE_KICKER, TEAL,
          CLIMATE_HEAD, CLIMATE_BODY)

    # ---- Row C: war + justice ----
    rule(pg, 616)
    y = 628
    story(pg, MX, y, COLW, WAR_KICKER, RED, WAR_HEAD, WAR_BODY)
    story(pg, MX + COLW + GAP, y, COLW, JUSTICE_KICKER, GOLD,
          JUSTICE_HEAD, JUSTICE_BODY)

    # ---- Row D: in brief (one line per item, full width) ----
    rule(pg, 808)
    draw_text(pg, MX, 820, "IN BRIEF", 3, INK)
    pg.hline(MX, 846, CW, INK, 1)
    yy = 858
    for lead, text in BRIEF:
        draw_text(pg, MX, yy, lead + ":", 2, RED)
        lx = MX + text_w(lead + ": ", 2)
        draw_text(pg, lx, yy, text, 2, INK)
        yy += 16

    # ---- Sport strip ----
    rule(pg, 992)
    draw_text(pg, (W - text_w(SPORT, 2)) // 2, 1002, SPORT, 2, INK)
    return pg


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    pg = build_page()
    path = os.path.join(out_dir, "entry.png")
    blob = write_png(pg, path)
    print("wrote %s %d bytes sha256 %s"
          % (path, len(blob), hashlib.sha256(blob).hexdigest()))


if __name__ == "__main__":
    main()
