"""Gather the abstract studies into layered 3D point-cloud spheres."""

import argparse
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from render_abstract_planets import (
    ROOT, SCENES, SHARES, TAU, color_groups, font, rgb, space, splat,
)
from render_character_planets import fbm


OUT = ROOT / "球形天体效果图"
FFMPEG = Path("C:/Program Files/Derivative/TouchDesigner/bin/ffmpeg.exe")
BACKGROUND = "050710"


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x*x*(3-2*x)


def surface_field(index, p):
    x, y, z = p.T
    flow = fbm(p, 2.4, index*7+3)
    grain = fbm(p, 9, 13+index)
    curl = np.sin(5*x-3*z+6*flow)
    if index == 0:
        # The densest filaments loop around patches of thinner dust.
        spiral = np.sin(9*y - 3*x + 3.2*curl + 9*flow)
        feature = (.5+.5*spiral)**4
        shade = .57+ .44*feature+.30*grain
        pigment = .51*x+.45*y+.44*spiral+1.2*flow
    elif index == 1:
        # A coarse warped field makes the clouds gather into separate patches.
        puffs = .8*fbm(p + .17*np.c_[curl, flow, np.cos(5*y)], 5.6, 29) + .62*flow
        feature = smoothstep((puffs+.22)/.54)
        shade = .34+.74*feature+.25*grain
        pigment = .53*x-.25*y+.22*z+1.6*puffs
    elif index == 2:
        sheet = 10*y+4.3*x + 3.0*np.sin(3.2*x+2.1*z)+6.4*flow
        seam = np.sin(sheet)
        feature = (.5+.5*seam)**7
        shade = .48+.48*feature+.19*np.sin(2*sheet+.6)
        pigment = .46*x+.28*y+.29*seam+1.44*flow
    elif index == 3:
        current = .24*np.sin(4.2*x-2*z)+.21*x+.36*flow
        first = np.exp(-((y-current-.25)/.14)**2)
        second = np.exp(-((y+current+.20)/.16)**2)
        feature = np.clip(first+second, 0, 1)
        shade = .44+.48*feature+.27*grain
        pigment = .43*(first-second)+.39*x + .98*flow + .21*z
    else:
        current = np.sin(13*y + 6*x + 3.6*z + 10*flow)
        broken = smoothstep((fbm(p, 5.4, 2)+.37)/.61)
        feature = (.5+.5*current)**4*broken
        shade = .44+.47*feature + .44*grain
        pigment = .59*y+.29*x+1.49*flow + .32*current
    return shade, pigment


def spherical_cloud(index, rng, count):
    # Uniformly sample the sphere then thin low-density regions of each flow.
    size = count*3
    z = rng.uniform(-1, 1, size)
    lon = rng.uniform(0, TAU, size)
    radial = np.sqrt(1-z*z)
    direction = space(radial*np.cos(lon), radial*np.sin(lon), z)
    shade, pigment = surface_field(index, direction)
    importance = np.clip(shade, .17, 1.5)**1.72
    chosen = rng.choice(size, size=count, p=importance/importance.sum(), replace=False)
    direction, shade, pigment = direction[chosen], shade[chosen], pigment[chosen]
    volume = rng.random(count) < .18
    radius = np.where(volume, .60+.35*rng.beta(2.2, 1.05, count),
                      np.clip(.979+rng.normal(0,.017,count), .903, 1.011))
    return direction*radius[:,None], direction, shade, pigment


def spatial_key(p):
    coords = p[:, :2]
    xy = np.clip((coords+1.35)*(1023/2.7), 0, 1023).astype(np.int32)
    key = np.zeros(len(xy), dtype=np.int32)
    for bit in range(10):
        key |= ((xy[:,0] >> bit)&1) << (2*bit)
        key |= ((xy[:,1] >> bit)&1) << (2*bit+1)
    return key


class Planet:
    def __init__(self, index, count):
        _, _, swatches, order, generator, seed = SCENES[index]
        rng = np.random.default_rng(seed)
        p, color, strength = generator(rng, count)
        p[:, :2] *= (1+.13*p[:, 2:3])
        low, high = np.quantile(p[:, :2], [.005,.995], axis=0)
        p[:, :2] -= (low+high)/2
        p[:, :2] *= min(2.74/(high[0]-low[0]),2.17/(high[1]-low[1]))
        self.source = p.astype(np.float32)
        self.source_light = strength*np.clip(.78+.21*p[:,2], .46, 1)
        src_color = color_groups(color, order)
        dest, n, strength, color = spherical_cloud(index, rng, count)
        dst_color = color_groups(color, order)
        # Match the same five colors before and after. Nearby particles tend to
        # travel together even when the final globe wraps across the back.
        match = np.empty(count, dtype=int)
        src_key, dst_key = spatial_key(p), spatial_key(dest)
        for group in range(len(SHARES)):
            s = np.flatnonzero(src_color==group)
            d = np.flatnonzero(dst_color==group)
            match[s[np.argsort(src_key[s], kind="stable")]] = d[np.argsort(dst_key[d], kind="stable")]
        self.target = dest[match].astype(np.float32)
        self.normal = n[match].astype(np.float32)
        self.shade = strength[match].astype(np.float32)
        self.color = np.array([rgb(value) for value in swatches])[src_color]
        self.glint = rng.random(count).astype(np.float32)
        self.offset = .19*np.tanh(p[:,2]) + .15*(self.glint-.5)
        self.spin = (-1 if index % 2 else 1)*(.44+.19*np.sin(.8*index))

    def image(self, width, height, time=1, yaw=0):
        c, s = np.cos(yaw), np.sin(yaw)
        x, y, z = self.target.T
        target = space(c*x+s*z, y, -s*x+c*z)
        x, y, z = self.normal.T
        nz = -s*x+c*z
        nx = c*x+s*z
        diffuse = np.clip(-.56*nx+.48*y+.68*nz, 0, 1)
        visibility = .089+.911*smoothstep((nz+.22)/.30)
        limb = np.exp(-((nz-.15)/.24)**2)
        gloss = .23+.78*diffuse**.64+.31*limb
        surface = self.shade*visibility*gloss
        progress = smoothstep(time + np.sin(np.pi*time)*self.offset)
        arc = np.sin(np.pi*progress)*.64
        # A brief sideways sweep gives the gather a curved trajectory.
        p = self.source*(1-progress[:,None])+target*progress[:,None]
        px, py, pz = p.T
        spin = self.spin*arc
        scalex = np.cos(spin)*px - np.sin(spin)*py
        scaley = np.sin(spin)*px + np.cos(spin)*py
        strength = (1-progress)*self.source_light + progress*surface
        scale = min(width/3.25,height/2.56)
        sx = np.clip(width*.5+scale*scalex, 1, width-3)
        sy = np.clip(height*.5-scale*scaley, 1, height-3)
        strength *= .73+.20*np.clip(.5+pz,0,1)
        sample_gain = (width*height/len(sx))/(1040*740/150_000)
        strength *= sample_gain*(.10+.85*self.glint**3.5+1.9*self.glint**26)
        canvas = np.zeros((width*height,3), dtype=np.float32)
        splat(canvas, sx, sy, self.color*strength[:,None], width, height)
        raw = canvas.reshape(height,width,3)
        dot_image = Image.fromarray(np.uint8(255*(1-np.exp(-raw))))
        bloom = np.asarray(dot_image.filter(ImageFilter.GaussianBlur(max(1.3, width*.0045))), dtype=np.float32)/255
        haze = np.asarray(dot_image.filter(ImageFilter.GaussianBlur(width*.016)), dtype=np.float32)/255
        energy = 1.33*raw + 1.16*bloom + .57*haze
        hdr = (energy/(.62+np.max(energy,axis=-1,keepdims=True)))**.78
        base = rgb(BACKGROUND)
        return Image.fromarray(np.uint8(255*(base+(1-base)*hdr)))


def render_plates():
    width, height = 2160, 1376
    board = Image.new("RGB", (width,height), "#0a0c14")
    draw = ImageDraw.Draw(board)
    header = font("msyhbd.ttc", 53)
    name_font = font("msyhbd.ttc", 31)
    small = font("msyh.ttc", 22)
    draw.text((51,23), "粒子聚合成球", font=header, fill="#e9edf6")
    caption = "每颗五色   ·   粒子数量比  5∶2∶1∶1∶1"
    draw.text((2109-draw.textlength(caption,font=small),49),caption,font=small,fill="#aeb5ca")
    draw.line((51,110,2109,110), fill="#313747", width=2)
    plates = []
    for idx, scene in enumerate(SCENES):
        name, pattern, swatches, *_ = scene
        # An oblique angle shows the texture wrapping around the sphere.
        planet = Planet(idx, 150_000)
        image = planet.image(1040,740,yaw=.10 + .06*idx)
        image.save(OUT/(name+".png"))
        plates.append(image)
        left, top = 51+idx%3*694, 133+idx//3*607
        draw.text((left,top), name, font=name_font, fill="#eef2fc")
        draw.text((left+90,top+7), pattern,font=small,fill="#"+swatches[0])
        board.paste(image.resize((670,476), Image.Resampling.LANCZOS), (left,top+54))
        start=left
        for color, weight in zip(swatches, SHARES):
            span = 67*weight
            draw.rectangle((start,top+544,start+span-1,top+557),fill="#"+color)
            start += span
    left, top = 1439, 740
    draw.text((left,top), "球面局部", font=name_font, fill="#eef2fc")
    draw.text((left+150,top+7), "金星",font=small,fill="#aeb5ca")
    crop = plates[2].crop((360,126,755,407)).resize((670,476),Image.Resampling.BICUBIC)
    board.paste(crop, (left,top+54))
    board.save(OUT/"五颗天体·聚合成球.png")


def render_video():
    fps, duration = 24, 4.75
    width, height = 1560, 1040
    tile_width, tile_height = 504, 444
    planets = [Planet(i, 42_000) for i in range(len(SCENES))]
    output = OUT/"五颗天体·聚合过程.webm"
    command = [
        str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps),
        "-i", "-", "-an", "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p",
        "-crf", "16", "-b:v", "0", "-deadline", "good", "-cpu-used", "5",
        "-row-mt", "1", str(output),
    ]
    template = Image.new("RGB", (width,height), "#"+BACKGROUND)
    labels = ImageDraw.Draw(template)
    typeface = font("msyh.ttc", 25)
    positions = [(16,41),(528,41),(1040,41),(272,536),(784,536)]
    for (left,top), scene in zip(positions, SCENES):
        labels.text((left+tile_width/2,top+tile_height+2),scene[0],font=typeface,
                    anchor="mt",fill="#"+scene[2][0])
    with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
        for i in range(round(fps*duration)):
            t = i/fps
            progress = float(np.clip((t-.54)/2.55,0,1))
            rotation = float(smoothstep((t-2.68)/2.04))
            frame = template.copy()
            for index, (planet, pos) in enumerate(zip(planets, positions)):
                tile = planet.image(
                    tile_width, tile_height, time=progress,
                    yaw=(.1+.06*index)*progress + (.34-.04*index)*rotation,
                )
                frame.paste(tile,pos)
            encoder.stdin.write(frame.tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("Video encoding failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", choices=("plates","video"))
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    if args.output == "plates":
        render_plates()
    else:
        render_video()


if __name__ == "__main__":
    main()
