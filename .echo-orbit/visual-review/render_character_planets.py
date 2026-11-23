"""Build a typographic look board from front-facing samples of five 3D spheres."""

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "字符星球效果图"
FONT_DIR = Path("C:/Windows/Fonts")
COLS, ROWS = 113, 68
CW, CH = 7, 11
BACKGROUND = np.array([3, 4, 8], dtype=np.float32)
SYMBOLS = ("·.:`", "'-+=*~", "lI1;^!/", "rxn+tzv<>", "scku70FJZ", "O0qywKDU", "MXR8W%&", "@#B$NWM")


def clamp(x):
    return np.clip(x, 0, 1)


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ramp(x, low, high):
    return ease((x - low) / (high - low))


@lru_cache(maxsize=None)
def colors(values):
    return np.array([tuple(bytes.fromhex(value)) for value in values], dtype=np.float32)


def gradient(value, swatches):
    table = colors(swatches)
    level = clamp(value) * (len(table) - 1)
    left = np.minimum(level.astype(int), len(table) - 2)
    t = (level - left)[..., None]
    return table[left] * (1 - t) + table[left + 1] * t


def blend(first, second, t):
    t = clamp(t)[..., None]
    return first * (1 - t) + second * t


RNG = np.random.default_rng(808)
NOISE = RNG.uniform(-1, 1, (64, 64, 64))


def noise(p, scale, seed):
    q = p * scale + seed * np.array([1.27, 1.86, 2.57])
    left = np.floor(q).astype(int)
    x, y, z = (left % 64).T
    j, k, m = ((left + 1) % 64).T
    a, b, c = ease(q - left).T
    lo = (NOISE[x, y, z] * (1-a) + NOISE[j, y, z] * a) * (1-b)
    lo += (NOISE[x, k, z] * (1-a) + NOISE[j, k, z] * a) * b
    hi = (NOISE[x, y, m] * (1-a) + NOISE[j, y, m] * a) * (1-b)
    hi += (NOISE[x, k, m] * (1-a) + NOISE[j, k, m] * a) * b
    return lo * (1-c) + hi * c


def fbm(p, scale, seed):
    return (
        .58 * noise(p, scale, seed)
        + .26 * noise(p, scale * 2.09, seed + 3)
        + .12 * noise(p, scale * 4.37, seed + 6)
        + .04 * noise(p, scale * 9.01, seed + 9)
    )


def rotate(p, tilt, yaw):
    x, y, z = p.T
    angle = np.deg2rad(tilt)
    c, s = np.cos(angle), np.sin(angle)
    x, y = c * x + s * y, -s * x + c * y
    angle = np.deg2rad(yaw)
    c, s = np.cos(angle), np.sin(angle)
    return np.column_stack((c*x + s*z, y, c*z - s*x))


def sun(p, light):
    x, y, z = p.T
    flow = fbm(p, 2.4, 1)
    warped = p + np.column_stack((flow * .34, noise(p, 2.3, 9) * .22, flow * -.21))
    folds = np.sin(16*y + 6*x + 14*fbm(warped, 3.4, 5) + 2*z)
    heat = .51 + .34*folds + .98*fbm(warped, 6.8, 1)
    spot = ramp(fbm(p, 4, 18), .22, .44)
    color_index = .44 + .37*folds + .65*flow + .19*(y+.2) - .36*spot
    col = gradient(color_index, ("8f55f7", "e84cc9", "ff3c69", "ff8944", "ffcb58", "fff9af"))
    rim = ramp(fbm(p, 2.5, 11) + .23*x - .16*light, .07, .35)
    col = blend(col, colors(("54f3db",))[0], .94*rim)
    return col, (.27 + .69*clamp(heat)) * (1-.74*spot) * (.38+.64*light)


CRATER_CENTERS = np.array([
    [-.63, .19, .75], [.17, .18, .97], [.48, -.44, .76], [-.31, -.43, .84],
    [.53, .56, .63], [-.07, .67, .74], [-.81, -.16, .57], [.81, .10, .58],
    [.14, -.64, .75], [-.54, .48, .69], [.71, -.22, .65],
    [-.46, -.68, .56], [-.15, -.08, .99], [.25, .44, .87],
])
CRATER_CENTERS /= np.linalg.norm(CRATER_CENTERS, axis=1, keepdims=True)
CRATER_RADII = (.19, .33, .14, .13, .20, .075, .095, .14, .081, .074, .072, .12, .081, .067)


def mercury(p, light):
    x, y, _ = p.T
    grit = fbm(p, 10, 7)
    large = fbm(p, 2.25, 22)
    relief = np.zeros_like(x)
    warm_stone = np.zeros_like(x)
    for center, radius in zip(CRATER_CENTERS, CRATER_RADII):
        delta = p - center
        d = np.sqrt(np.sum(delta * delta, axis=1)) / radius + grit * .18
        slope = np.clip((delta[:, 0]*.62 - delta[:, 1]*.79) / radius, -1, 1)
        relief += .54*np.exp(-((d-.91)/.17)**2)*slope - .21*ramp(-d, -1, -.65)
        warm_stone += .19*np.exp(-((d-.94)/.28)**2)
    v = .48 + 1.17*large + .44*x - .29*y + .38*grit + warm_stone
    col = gradient(v, ("7192ff", "4dcde9", "67e89f", "af99fc", "f17db8", "ffbd72"))
    return col, (.49 + .94*grit + relief) * (.24+.85*light)


def venus(p, light):
    x, y, z = p.T
    broad = fbm(p, 2.25, 38)
    warp = np.column_stack((x, y + .49*broad + .19*np.sin(3*x-2*z), z))
    swirls = np.sin(9.5*warp[:, 1] + 10*fbm(warp, 4, 13) - 5*z)
    thin = np.sin(16*warp[:, 1] + 16*fbm(warp, 6, 29))
    fog = .49 + .31*swirls + .135*thin + .7*fbm(warp, 8.3, 25)
    v = .46+.34*swirls+.50*broad+.23*x+.07*thin
    col = gradient(v, ("48e9fa", "5f7bfb", "995df4", "f765c2", "ff899d", "ffcf70", "ffed9e"))
    backlit = ramp(fbm(warp, 3.1, 6) + .31*swirls, .16, .52)
    col = blend(col, colors(("8effbe",))[0], .63*backlit)
    return col, (.24+.82*clamp(fog)) * (.4+.7*light)


def continental_mask(lon, lat, outline):
    # Signed point-to-edge distance lets the same noise add small coastal inlets.
    inside = np.zeros(len(lon), bool)
    nearest = np.full(len(lon), 360.)
    previous = outline[-1]
    for current in outline:
        x, y = previous
        dx, dy = current[0]-x, current[1]-y
        if dy:
            inside ^= ((y > lat) != (current[1] > lat)) & (lon < x + dx*(lat-y)/dy)
        t = clamp(((lon-x)*dx + (lat-y)*dy)/(dx*dx+dy*dy))
        nearest = np.minimum(nearest, (lon-x-t*dx)**2 + (lat-y-t*dy)**2)
        previous = current
    return np.sqrt(nearest) * np.where(inside, 1, -1)


AMERICAS = (
    ((-166, 66), (-153, 72), (-119, 71), (-96, 76), (-69, 76), (-59, 61), (-65, 50),
     (-80, 35), (-80, 25), (-89, 22), (-87, 15), (-77, 8), (-85, 10), (-99, 21),
     (-106, 23), (-116, 31), (-126, 49), (-132, 58), (-151, 59), (-166, 58)),
    ((-82, 10), (-72, 13), (-60, 8), (-50, 4), (-35, -5), (-39, -18), (-51, -28),
     (-57, -37), (-68, -55), (-77, -53), (-71, -41), (-73, -27), (-81, -9)),
    ((-73, 81), (-49, 84), (-25, 78), (-20, 70), (-42, 59), (-52, 61), (-56, 74)),
)


def earth(p, light):
    x, y, z = p.T
    lon = np.rad2deg(np.arctan2(x, z)) - 83
    lat = np.rad2deg(np.arcsin(np.clip(y, -1, 1)))
    terrain = fbm(p, 7, 35)
    coast = np.maximum.reduce([continental_mask(lon, lat, outline) for outline in AMERICAS])
    coast += terrain * 9 + noise(p, 30, 6) * 1.4
    land = ramp(coast, -1.7, 2.3)
    shelf = np.exp(-((coast+2)/5)**2)
    oceans = gradient(.36+.76*fbm(p, 2.9, 7)+ .22*x + .24*y,
                      ("6953e5", "4878fa", "40b4ff", "4de9e4"))
    leaf = gradient(.53+.83*fbm(p, 5.3, 43)-.22*y,
                    ("64df91", "94eb8b", "c8e985", "fbd779", "fa9877"))
    col = blend(oceans, colors(("63efcd",))[0], shelf*.7)
    col = blend(col, leaf, land)
    winds = np.column_stack((x*1.2, y*3.1 + fbm(p, 3.6, 4)*2.5, z))
    cloud = ramp(fbm(winds, 5.0, 9), .05, .39)
    cloud_color = gradient(.54+.78*fbm(p, 3.25, 45)+.31*y,
                           ("8778fb", "bb81f5", "ffa3dd", "d4e9ff"))
    col = blend(col, cloud_color, cloud*.91)
    tone = .31 + .08*fbm(p, 13, 6) + .51*land + .58*cloud + .24*shelf
    return col, clamp(tone)*(.24+.82*light)


def mars(p, light):
    x, y, z = p.T
    field = fbm(p, 2.6, 32)
    valley = y + .25*np.sin(3.3*x - .75) - .23 + .39*field
    chasm = np.exp(-(valley / .093)**2)
    bands = np.sin(15*y + 8*z + 13*field + 4*noise(p, 5, 12))
    iron = .53+.91*field+.24*bands-.36*chasm+.22*y
    col = gradient(iron, ("6d84ec", "9d64f4", "dc57a7", "fc4263", "ff834b", "ffbb60", "ffe380"))
    ice = ramp(-y+fbm(p, 7, 3)*.30, .61, .85)
    col = blend(col, colors(("6bf3d4",))[0], .96*ice)
    return col, (.56+.27*bands+.51*fbm(p, 14, 7)-.32*chasm+.31*ice) * (.33+.79*light)

SCENES = (
    ("太阳", "日面", "ffcf82", (1, 0), sun, (.73, .33)),
    ("水星", "陨坑", "8fe6e3", (7, -7), mercury, (.38, .54)),
    ("金星", "层云", "f092ca", (-15, 9), venus, (.50, .39)),
    ("地球", "海陆", "8cdbad", (-8, 0), earth, (.45, .33)),
    ("火星", "峡谷", "ff8b76", (14, -20), mars, (.67, .42)),
)


def masks():
    font = ImageFont.truetype(FONT_DIR / "consola.ttf", 11)
    ret = np.zeros((len(SYMBOLS)*9, CH, CW), dtype=np.float32)
    for row, options in enumerate(SYMBOLS):
        for n in range(9):
            ch = options[n % len(options)]
            im = Image.new("L", (CW, CH))
            ImageDraw.Draw(im).text((0, -1), ch, font=font, fill=255, stroke_width=0)
            ret[row*9+n] = np.asarray(im) / 255
    return ret


MASKS = masks()
GRID_X, GRID_Y = np.meshgrid(np.arange(COLS), np.arange(ROWS))
PX = ((GRID_X.ravel() + .5)*CW - COLS*CW/2) / 308
PY = (ROWS*CH/2 - (GRID_Y.ravel()+.5)*CH) / 308
D2 = PX**2 + PY**2
Z = np.sqrt(np.maximum(0, 1 - D2))
POINTS = np.column_stack((PX, PY, Z))
VARIATION = RNG.uniform(0, 1, PX.shape)
GLYPH_CHOICE = RNG.integers(0, 9, PX.shape)


def frame(index):
    _, _, _, view, material, _ = SCENES[index]
    nx, ny, nz = POINTS.T
    light = clamp(.24 - .46*nx + .42*ny + .70*nz)
    p = rotate(POINTS, *view)
    hue, material_light = material(p, light)
    atmosphere = .08 * np.exp(-((Z-.08)/.27)**2) * light
    tone = clamp((clamp(material_light)+atmosphere)*1.13)
    dither = (VARIATION-.5) * .092
    level = np.floor(clamp(tone + dither) * 7.99).astype(int)
    glyph = MASKS[level*9 + GLYPH_CHOICE].copy()
    # The sphere remains assembled entirely from the cells of a fixed character grid.
    edge = 1 - ramp(D2, .982, 1.006)
    shade = (.18+.82*tone**.44) * edge
    glyph = glyph**.74 * shade[:, None, None]
    # Let bright glyphs carry a little pale detail while holding hue in midtones.
    hue = blend(hue, colors(("fff6ed",))[0], .16*ramp(tone, .66, 1))
    tiles = glyph[..., None]*hue[:, None, None, :] + (1-glyph[...,None])*BACKGROUND
    pixels = tiles.reshape(ROWS, COLS, CH, CW, 3).transpose(0, 2, 1, 3, 4)
    return Image.fromarray(np.uint8(pixels.reshape(ROWS*CH, COLS*CW, 3)))


def board(plates):
    board_width, board_height = 2312, 1090
    bg = "#0a0b12"
    image = Image.new("RGB", (board_width, board_height), bg)
    draw = ImageDraw.Draw(image)
    heading = ImageFont.truetype(FONT_DIR / "msyhbd.ttc", 55)
    label = ImageFont.truetype(FONT_DIR / "msyhbd.ttc", 35)
    small = ImageFont.truetype(FONT_DIR / "msyh.ttc", 24)
    draw.text((58, 31), "字符星球", fill="#f1f0f6", font=heading)
    draw.text((1940, 69), "深空回声 / 视觉样张", fill="#9094a8", font=small)
    draw.line((60, 120, 2252, 120), fill="#2a2939", width=2)
    draw.text((59, 644), "字符局部放大", fill="#b8b8ca", font=small)
    for index, plate in enumerate(plates):
        name, feature, accent, _, _, crop_position = SCENES[index]
        x = 60 + index*442
        draw.text((x, 151), name, fill="#f1f0f6", font=label)
        draw.text((x+93, 160), feature, fill="#"+accent, font=small)
        square = plate.crop((21, 0, 769, 748))
        image.paste(square.resize((424, 424), Image.Resampling.LANCZOS), (x, 208))
        u, v = crop_position
        # Use the same marks at twice their native size in the lower row.
        left = int(plate.width*u) - 106
        top = int(plate.height*v) - 82
        zoom = plate.crop((left, top, left+212, top+164))
        image.paste(zoom.resize((424, 328), Image.Resampling.NEAREST), (x, 705))
    image.save(OUTPUT / "五颗天体·字符与彩色.png", optimize=True)


def main():
    OUTPUT.mkdir(exist_ok=True)
    plates = [frame(i) for i in range(len(SCENES))]
    for scene, plate in zip(SCENES, plates):
        plate.save(OUTPUT / (scene[0]+".png"))
    board(plates)


if __name__ == "__main__":
    main()
