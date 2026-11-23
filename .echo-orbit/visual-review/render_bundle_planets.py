"""Render five 3D globes composed of colored particle bundles."""

from pathlib import Path
import argparse
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from render_abstract_planets import ROOT, SCENES, SHARES, font, rgb, space, splat


OUT = ROOT / "色束粒子星球"
FFMPEG = Path("C:/Program Files/Derivative/TouchDesigner/bin/ffmpeg.exe")
BLACK = "#030408"
# Each color has its own latitude, width, wavelength phase and radial depth.
PLUMES = (
    ((.12,.29,.15,.94),(-.51,.18,.62,.92),(.62,.17,1.03,.87),(-.75,.19,2.62,.86),(.32,.13,3.10,.98)),
    ((-.09,.31,1.10,.94),(.61,.20,2.80,.87),(-.55,.17,.94,.92),(.29,.16,.70,.99),(.66,.17,4.21,.86)),
    ((.17,.30,2.95,.94),(-.43,.23,1.74,.93),(.60,.16,2.62,.88),(-.66,.18,3.22,.90),(.14,.18,.71,.99)),
    ((-.07,.35,1.19,.91),(.62,.18,1.14,.87),(.19,.17,2.71,.98),(-.61,.16,3.70,.91),(.51,.15,.35,.97)),
    ((.19,.30,1.13,.94),(-.51,.21,2.75,.91),(.63,.16,1.62,.89),(-.69,.16,4.31,.87),(.22,.14,3.92,.98)),
)
STYLE = (
    ("弯束回旋", -.48,.34,.19,1.18),
    ("松紧错落", .26,.25,.29,1.42),
    ("宽束翻卷", -.72,.30,.22,.95),
    ("双向交织", .52,.25,.19,1.00),
    ("斜向喷流", -.24,.30,.25,1.37),
)


class Bundles:
    def __init__(self, index, count):
        _, _, hexes, _, _, seed = SCENES[index]
        self.index = index
        rng = np.random.default_rng(seed+305)
        self.palette = np.array([rgb(h) for h in hexes])
        self.size = [count*share//10 for share in SHARES]
        assert sum(self.size) == count
        self.parts = []
        for k, n in enumerate(self.size):
            lon = rng.uniform(-np.pi, np.pi, n).astype(np.float32)
            cross = rng.normal(0, 1, n).astype(np.float32)
            depth = rng.normal(0, 1, n).astype(np.float32)
            scatter = rng.random(n).astype(np.float32)
            sparkle = rng.random(n).astype(np.float32)
            # Sparse outer dust follows the same path and pigment as its bundle.
            airy = scatter > .897
            cross *= np.where(airy, 2.08, .79)
            depth *= np.where(airy, 1.85, .66)
            self.parts.append((lon,cross,depth,airy,sparkle))

    def points(self, t):
        _, axis, sweep, fold, harmonic = STYLE[self.index]
        points, powers = [], []
        for k, (part, spec) in enumerate(zip(self.parts, PLUMES[self.index])):
            lon0, thickness, depth, airy, sparkle = part
            lat0, width, phase, radius0 = spec
            variation = .09*np.sin(2*lon0+phase-t*.58)
            u = lon0 + t*(.15+.031*k) + variation
            advection = .21*t + .24*np.sin(t*.8)
            beam = u + phase + advection
            crest = np.sin(beam*2 + .7*np.sin(beam+phase))
            # Large bends define the bundle, with small vortices along the boundary.
            center = lat0 + sweep*np.sin(beam) + fold*.62*crest
            center += .081*np.sin(4*u+phase + .6*np.sin(2*u+advection))
            fat = .84 + .33*np.sin(2*u+phase+.8) + .24*np.cos(u-2*phase)
            comb = np.sin(9*u+phase+1.7*thickness) * np.sin(4*u-phase)
            lat = center + width*(thickness*fat + .14*comb)
            # Folding across a pole keeps joining branches smooth and three-dimensional.
            helix = .13*np.sin(2*u+.61*phase) + .062*thickness*np.sin(3*u+phase+1)
            lon = u + harmonic*helix + k*.19
            fluctuation = .035*np.cos(3*u-2*lat+phase) + .038*crest
            rad = radius0 + fluctuation + (.085 + .026*np.cos(2*u))*depth - .023*thickness**2
            edge_width = np.where(airy, .18, .063)
            rad = np.maximum(rad, .23)
            outer = np.maximum(0,rad-.97)
            rad += edge_width*np.tanh(outer/edge_width)-outer
            x = rad*np.sin(lon)*np.cos(lat)
            y = rad*np.sin(lat)
            z = rad*np.cos(lon)*np.cos(lat)
            pitch = .17 + .14*np.sin(self.index+.37)
            y, z = y*np.cos(pitch)-z*np.sin(pitch), y*np.sin(pitch)+z*np.cos(pitch)
            x, y = x*np.cos(axis)-y*np.sin(axis), x*np.sin(axis)+y*np.cos(axis)
            rimlight = np.clip(.65 - .40*x + .40*y, .38, 1.15)
            # Light the foreground cores while still letting rear plumes show in the gaps.
            distance = np.clip((z+.52)/1.52, 0, 1)
            visibility = .09+.91*distance**1.12
            hotspot = .65 + .44*(.5+.5*np.sin(2.2*u+phase-.27*t))**2
            core = np.exp(-.61*thickness**2-.44*depth**2)
            power = rimlight*visibility*hotspot*(.20+.77*core + 1.25*sparkle**18)
            power *= np.where(airy, .39+.46*sparkle**15, 1)
            points.append(space(x,y,z))
            powers.append(power)
        return points, powers

    def image(self, width, height, t=0):
        points, powers = self.points(t)
        scale = min(width/2.90,height/2.32)
        projection = [1+.075*p[:,2] for p in points]
        xs = [np.clip(width*.5+scale*p[:,0]*d,1,width-3) for p,d in zip(points,projection)]
        ys = [np.clip(height*.51-scale*p[:,1]*d,1,height-3) for p,d in zip(points,projection)]
        gain = 1.12*(width*height/sum(self.size))/(1056*800/250_000)
        raster = np.zeros((width*height,3),dtype=np.float32)
        x,y = np.concatenate(xs),np.concatenate(ys)
        colors = np.concatenate([c*power[:,None]*gain for c,power in zip(self.palette,powers)])
        splat(raster,x,y,colors,width,height)
        raw = raster.reshape(height,width,3)
        veil = Image.fromarray(np.uint8(255*raw/(.72+np.max(raw,axis=-1,keepdims=True))))
        soft = np.asarray(veil.filter(ImageFilter.GaussianBlur(max(2.1,width*.006))),dtype=np.float32)/255
        aura = np.asarray(veil.filter(ImageFilter.GaussianBlur(width*.017)),dtype=np.float32)/255
        energy = .70*raw + 2.0*soft + .75*aura
        maximum = np.max(energy,axis=-1,keepdims=True)
        exposure = 1-np.exp(-1.40*maximum)
        tint = np.divide(energy, maximum, where=maximum>0, out=np.zeros_like(energy))
        # Leave the glowing color intact while keeping visible fine-point detail.
        background = rgb(BLACK[1:])
        graded = background + tint**.82 * exposure**.84 * (1-background)
        return Image.fromarray(np.uint8(255*np.clip(graded,0,1)))


def plates():
    width, height = 2160, 1428
    canvas = Image.new("RGB",(width,height),"#0a0c13")
    draw = ImageDraw.Draw(canvas)
    large = font("msyhbd.ttc",50)
    medium = font("msyhbd.ttc",30)
    small = font("msyh.ttc",23)
    draw.text((52,27),"色束组成的星球",font=large,fill="#e9ecf6")
    ratio = "每颗五色   ·   粒子数量比  5∶2∶1∶1∶1"
    draw.text((2108-draw.textlength(ratio,font=small),55),ratio,font=small,fill="#a1acc1")
    draw.line((52,110,2108,110),fill="#292d3e",width=2)
    images = []
    for i, scene in enumerate(SCENES):
        name, _, palette, *_ = scene
        image = Bundles(i,250_000).image(1056,800)
        image.save(OUT/(name+".png"))
        images.append(image)
        x, y = 52+i%3*694, 140+i//3*625
        draw.text((x,y),name,font=medium,fill="#f0f2fa")
        draw.text((x+86,y+5),STYLE[i][0],font=small,fill="#"+palette[0])
        canvas.paste(image.resize((668,506),Image.Resampling.LANCZOS),(x,y+53))
        boundary = 0
        for proportion,color in zip(SHARES,palette):
            left = x + round(668*boundary/10)
            boundary += proportion
            right = x + round(668*boundary/10)
            draw.rectangle((left,y+574,right-1,y+585),fill="#"+color)
    x, y = 1440, 765
    draw.text((x,y),"色束边缘",font=medium,fill="#f0f2fa")
    draw.text((x+143,y+5),"金星局部",font=small,fill="#a1acc1")
    crop = images[2].crop((170,156,636,509)).resize((668,506),Image.Resampling.LANCZOS)
    canvas.paste(crop,(x,y+53))
    canvas.save(OUT/"五颗天体·色束粒子.png")


def motion():
    fps, frames = 24, 108
    width,height = 1560,1040
    tile_width,tile_height = 508,473
    planets = [Bundles(i,74_000) for i in range(len(SCENES))]
    target = OUT/"五颗天体·色束流动.webm"
    command = [
        str(FFMPEG),"-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
        "-s",f"{width}x{height}","-r",str(fps),"-i","-","-an","-c:v","libvpx-vp9",
        "-pix_fmt","yuv420p","-crf","17","-b:v","0","-cpu-used","5","-row-mt","1",str(target),
    ]
    template = Image.new("RGB",(width,height),BLACK)
    positions = [(10,18),(526,18),(1042,18),(268,545),(784,545)]
    with subprocess.Popen(command,stdin=subprocess.PIPE) as encoder:
        for i in range(frames):
            image = template.copy()
            for loc, planet in zip(positions,planets):
                image.paste(planet.image(tile_width,tile_height,t=i/fps),loc)
            encoder.stdin.write(image.tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("Video encoding failed")


if __name__=="__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("mode", choices=("plates","motion"))
    parameters = cli.parse_args()
    OUT.mkdir(exist_ok=True)
    (plates if parameters.mode=="plates" else motion)()
