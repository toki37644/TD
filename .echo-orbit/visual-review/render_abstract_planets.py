"""Offline particle studies with an exact 50/20/10/10/10 population split."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "抽象粒子星球效果图"
FONT = Path("C:/Windows/Fonts")
WIDTH, HEIGHT = 1120, 800
COUNT = 150_000
SHARES = (5, 2, 1, 1, 1)
TAU = 2 * np.pi


def rgb(value):
    return np.array(tuple(bytes.fromhex(value)), dtype=np.float32) / 255


def space(x, y, z):
    return np.column_stack((x, y, z))


def sun(r, n):
    strand = r.integers(0, 17, n)
    t = r.uniform(-np.pi, np.pi, n)
    depth = r.normal(0, 1, n)
    arm = (strand - 8) / 8
    center = .73 + .18*np.sin(t*2+arm*2.15) + .09*np.cos(3*t+arm)
    spin = t + .42*arm + .09*np.sin(5*t+arm*.4)
    loose = .013 + .026*(.5+.5*np.cos(2*t-arm))**2
    pitch = center + .31*arm + depth*loose + .042*np.sin(8*t + strand*.54)
    x = pitch*np.cos(spin) + .18*np.cos(2*t + arm)
    y = .80*pitch*np.sin(spin) - .22*x + .21*arm*np.cos(t+.3) + .10*np.sin(3*t+arm*2.1)
    z = .52*np.sin(t+arm*.46) + .18*depth + .31*arm
    color = .64*x-.18*y+.64*arm+.62*np.sin(t-.9)+r.normal(0,.10,n)
    light = (.34+.37*(.5+.5*np.cos(t+1.6))+.27*np.exp(-(depth/.76)**2))
    return space(x, y, z), color, light


def mercury(r, n):
    # Eight neighboring distributions, some dense and some barely connected.
    knots = np.array([
        [-.90,-.29,-.32], [-.61,-.12,.05], [-.34,.18,.38], [-.05,.18,.06],
        [.15,.49,-.22], [.39,.22,-.08], [.63,-.13,.22], [.82,-.37,.01],
    ])
    t = r.random(n) * 7
    row = t.astype(int)
    frac = t-row
    center = knots[row]*(1-frac[:,None])+knots[row+1]*frac[:,None]
    jitter = r.normal(0, 1, (n, 3))
    filament = r.integers(0, 7, n)
    close = r.random(n) < .71
    concentration = np.where(close, .041+.14*np.sin(np.pi*frac)**2, .15+.09*np.sin(np.pi*frac))
    x, y, z = (center + jitter*concentration[:,None]).T
    band = .13*np.cos(t*2.1 + filament*.8)
    x -= .20*y
    y += band + .055*np.sin(x*9+filament*.55) + .12*np.sin(z*5)
    z += .12 * np.cos(t*2.1 - filament*.9)
    color = .85*np.sin(.79*t-1.3)+.85*z+.38*y + r.normal(0,.11,n)
    light = (.40+.29*close+.28*np.cos(t*1.9)**4) * (1-.22*np.minimum(1,abs(jitter[:,1])/3))
    return space(x, y, z), color, light


def venus(r, n):
    u = r.beta(1.25, 1.09, n)
    width = r.uniform(-1, 1, n)
    layer = r.integers(0, 4, n)
    depth = r.normal(0, 1, n)
    phase = TAU*(u*.90+.14) + .41*width + .10*layer
    bend = .85-.58*u + .10*np.sin(6.1*u) + .27*width*np.sin(np.pi*u)**.6
    x = bend*np.cos(phase) + .56*u + .22*width*np.sin(4*u)
    y = 1.02*bend*np.sin(phase) - .41*u + .23*np.sin(width*4+u*6)*np.sin(np.pi*u)
    y += (.004+.019*abs(width))*depth + .045*np.sin(layer*2+5*u)
    z = .46*width + .28*np.cos(phase*1.3 + width) + .04*layer + .018*depth
    color = .23*x + .51*y + .8*width + .41*np.sin(phase-.3) + .28*np.sin(10*u+layer)
    light = .39+.38*(.5+.5*np.sin(9.5*u+2.2*width+layer*.43))**4
    light += .18*np.exp(-((abs(width)-.91)/.084)**2)
    return space(x, y, z), color, light


def earth(r, n):
    t = r.beta(1.32, 1.45, n)
    broad = r.normal(0, 1, n)
    sign = np.where(r.integers(0, 2, n), 1., -1.)
    thread = r.integers(0, 25, n)/24-.5
    circ = TAU*(.62*t + .11)
    taper = np.sin(np.pi*t)**.86
    x = (t-.5)*2.6 + .14*taper*sign*np.sin(circ)
    y = .24*x + sign*(.48*np.sin(circ+.27)+.13*np.sin(2*circ-.3))*taper
    y += np.where(sign>0, .33*t**2 - .12*(1-t)**3, -.40*t**2+.27*(1-t)**3)
    z = sign*.43*np.cos(circ+.5)*taper + .18*thread
    y += taper*(.39*thread+.032*np.sin(18*t+thread*9)) + (.014+.056*(1-t))*broad
    x += .16*thread*sign + .026*r.normal(0,1,n)
    color = .72*sign*np.cos(circ-.60)+.39*np.sin(2*circ)+.39*thread+.36*y+.11*broad
    light = .34+.37*(.5+.5*np.sin(11*t+sign+.38))+.2*(1-abs(thread)*2)
    return space(x, y, z), color, light


def mars(r, n):
    t = r.beta(1.37, 1.66, n)
    stream = r.integers(0, 21, n)/20
    radius = .21+.88*t
    arm = (stream-.5)*1.37 + .19*np.sin(8*t+stream*9)
    phase = 2.85*t + .19 + arm
    ash = r.normal(0, 1, n)
    dull = r.random(n) < .22
    width = np.where(dull, .062+.32*t**1.8, .013+.061*t**1.5)
    x = -.56 + radius*np.sin(phase)*.87 + 1.32*t + width*ash
    y = .31+radius*np.cos(phase)*.55 + .35*t + .28*np.sin(5.8*t) + .078*np.sin(stream*13)
    gaps = np.rint(stream*5)/5 - .5
    y += width*r.normal(0, 1, n) + gaps*.27*t
    z = .73*(stream-.5)+.37*np.sin(4*t) + .049*ash
    color = .86*stream + .64*np.sin(5*t+.66) + .59*z + .13*ash
    light = (.49+.29*np.cos(t*6+.36)**2 + .16*np.sin(stream*32)**4)*np.where(dull,.45,1)
    return space(x, y, z), color, light


# Entries are ordered by population. Color order below specifies their placement
# in the continuous spatial field, with the secondaries breaking around the core.
SCENES = (
    ("太阳", "沿弧线向内聚合", ("ffab40", "fe5b43", "fff1a1", "a76cf4", "5be9dc"), (4,3,1,0,2), sun, 43),
    ("水星", "团簇错叠", ("7a92f8", "cad9ff", "52dcc8", "b18bf1", "f9af87"), (2,1,0,3,4), mercury, 59),
    ("金星", "薄层翻卷", ("f071bc", "995ff3", "ff9b80", "f7c9ff", "5cdeee"), (4,1,0,2,3), venus, 73),
    ("地球", "两股粒子流交织", ("33d2ab", "5f7cfa", "c8ed71", "84f0ee", "ae75ec"), (4,1,0,3,2), earth, 87),
    ("火星", "粒子沿弧线逐渐散开", ("f06c56", "d64582", "ffb470", "9254de", "67dcdc"), (4,3,1,0,2), mars, 101),
)


def color_groups(field, order):
    rank = np.argsort(field, kind="stable")
    groups = np.empty(len(field), dtype=int)
    start = 0
    for index in order:
        end = start + len(field)*SHARES[index]//sum(SHARES)
        groups[rank[start:end]] = index
        start = end
    assert np.bincount(groups, minlength=5).tolist() == [len(field)*weight//10 for weight in SHARES]
    return groups


def splat(buffer, x, y, particles, width=WIDTH, height=HEIGHT):
    for xoff, yoff, weight in (
        (0, 0, (1 - x%1)*(1 - y%1)), (1, 0, (x%1)*(1 - y%1)),
        (0, 1, (1 - x%1)*(y%1)), (1, 1, (x%1)*(y%1)),
    ):
        idx = (y.astype(int)+yoff)*width+x.astype(int)+xoff
        for channel in range(3):
            channel_buffer = np.bincount(idx, particles[:,channel]*weight, minlength=width*height)
            buffer[:,channel] += channel_buffer


def render(scene):
    name, form, swatches, order, generator, seed = scene
    rng = np.random.default_rng(seed)
    p, field, light = generator(rng, COUNT)
    group = color_groups(field, order)
    c = np.array([rgb(code) for code in swatches])[group]
    x, y, z = p.T
    projection = 1 + .13*z
    xy = np.column_stack((x*projection, y*projection))
    low, high = np.quantile(xy, [.005, .995], axis=0)
    mid = (low+high)/2
    scale = min(850/(high[0]-low[0]), 630/(high[1]-low[1]))
    px = np.clip(WIDTH*.5+(xy[:,0]-mid[0])*scale, 1, WIDTH-3)
    py = np.clip(HEIGHT*.51-(xy[:,1]-mid[1])*scale, 1, HEIGHT-3)
    glitter = rng.random(COUNT)
    depth = np.clip(.78 + .21*z, .46, 1)
    strength = light*depth*(.12+.72*glitter**3.4+1.60*glitter**31)
    buffer = np.zeros((WIDTH*HEIGHT, 3), np.float32)
    splat(buffer, px, py, c*strength[:,None])
    raw = buffer.reshape(HEIGHT, WIDTH, 3)
    # Keep a sharp point pass and use a separate bloom for overlapping grains.
    exposed = 1-np.exp(-raw)
    plate = Image.fromarray(np.uint8(255*np.clip(exposed, 0, 1)))
    near = np.asarray(plate.filter(ImageFilter.GaussianBlur(3.6)), dtype=np.float32)/255
    far = np.asarray(plate.filter(ImageFilter.GaussianBlur(22)), dtype=np.float32)/255
    energy = 1.52*raw + 1.02*near + .43*far
    top = np.max(energy, axis=-1, keepdims=True)
    # Compress highlights equally by channel so that overlap does not turn white.
    hdr = np.maximum(0, energy/(.62+top))**.78
    base = rgb("050710")
    result = base + (1-base)*hdr
    return Image.fromarray(np.uint8(255*np.clip(result, 0, 1)))


def font(filename, size):
    return ImageFont.truetype(FONT / filename, size)


def board(plates):
    width, height = 2196, 1444
    output = Image.new("RGB", (width,height), "#0a0c14")
    draw = ImageDraw.Draw(output)
    title = font("msyhbd.ttc", 54)
    namefont = font("msyhbd.ttc", 33)
    label = font("msyh.ttc", 25)
    hexfont = font("consola.ttf", 21)
    draw.text((54, 23), "天体粒子群", font=title, fill="#f1f2fb")
    draw.text((1708, 57), "五色粒子数量比   5∶2∶1∶1∶1", font=label, fill="#acb2c5")
    draw.line((53, 109, 2141, 109), fill="#2d3243", width=2)
    for i, (scene, image) in enumerate(zip(SCENES, plates)):
        name, form, swatches, _, _, _ = scene
        x, y = 53 + i%3*704, 138 + i//3*643
        draw.text((x, y), name, font=namefont, fill="#f1f2fb")
        draw.text((x+91, y+6), form, font=label, fill="#"+swatches[0])
        plate = image.resize((680,486), Image.Resampling.LANCZOS)
        output.paste(plate, (x,y+57))
        left = x
        for value, share in zip(swatches, SHARES):
            span = 68*share
            draw.rectangle((left, y+557, left+span-1,y+576),fill="#"+value)
            left += span
        for j, value in enumerate(swatches):
            draw.text((x+j*136,y+589), "#"+value.upper(), font=hexfont,
                      fill="#dee2f3" if j==0 else "#9ea5ba")
    x, y = 1461, 781
    draw.text((x,y), "局部放大",font=namefont,fill="#f1f2fb")
    draw.text((x+160,y+6), "金星",font=label,fill="#acb2c5")
    crop = plates[2].crop((330,260,745,556)).resize((680,486),Image.Resampling.BICUBIC)
    output.paste(crop, (x,y+57))
    output.save(OUT / "五颗天体·粒子与配色.png")


def main():
    OUT.mkdir(exist_ok=True)
    plates = []
    for scene in SCENES:
        plate = render(scene)
        plate.save(OUT / (scene[0]+".png"))
        plates.append(plate)
    board(plates)


if __name__ == "__main__":
    main()
