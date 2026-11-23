"""Render the dark presentation treatment and one color-volume release study."""

import argparse
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from render_abstract_planets import ROOT, SCENES, SHARES, font, splat
from render_bundle_planets import Bundles, FFMPEG
from render_flame_globes import PHASES, VIEWS, Renderer


OUT = ROOT / "星际探索·彩雾呈现预览"
FRAGMENT = Path(__file__).with_name("luminous_nebula.frag")
SOLAR_PALETTE = ("ff4d0a","ffc225","85d449","159e9c","1b518f")


def ease(a):
    b = np.clip(a,0,1)
    return b*b*(3-2*b)


class ReleasedDust:
    def __init__(self, index):
        self.index = index
        bundle = Bundles(index,45_000)
        points, powers = bundle.points(.8)
        self.source = np.concatenate(points)
        self.strength = np.concatenate(powers)
        self.color = np.repeat(bundle.palette,bundle.size,axis=0)
        rng = np.random.default_rng(1058)
        self.seed = rng.random(len(self.source)).astype(np.float32)
        self.jitter = rng.normal(0,1,self.source.shape).astype(np.float32)
        self.ignition = rng.uniform(.08,.54,len(self.seed)).astype(np.float32)

    def rasterize(self, width, height, tick, stage):
        # Delay differs by strand; released particles follow the expanding volume.
        blend = ease((stage-self.ignition)/.56)
        x,y,z = self.source.T
        spin = (.55*z+.37*np.sin(6*y)+.30)*blend
        px = (x*np.cos(spin)-y*np.sin(spin))*(1-.15*stage)
        py = (y*np.cos(spin)+x*np.sin(spin))*(1+.28*stage)
        px += stage*(.29*np.sin(2.4*py+.71*tick)+.21*py+.064*np.sin(7*py))
        px += blend*self.jitter[:,0]*(.11+.26*self.seed)
        py += blend*(.092+.20*self.jitter[:,1])+.065*stage
        sx = width*.5 + height*VIEWS[self.index]*px
        sy = height*.5 - height*VIEWS[self.index]*py
        valid = (sx>1)&(sx<width-2)&(sy>1)&(sy<height-2)&(blend>.004)
        sparkle = .095 + .68*self.seed**8.5 + 4.25*self.seed**36
        pulse = (.67+.33*np.sin(16*self.seed+tick*4+z))**1.7
        power = blend*self.strength*sparkle*pulse*(.50+.5*np.maximum(0,z))
        raster = np.zeros((width*height,3),np.float32)
        splat(raster,sx[valid],sy[valid],self.color[valid]*power[valid,None],width,height)
        raw = raster.reshape(height,width,3)
        return 1-np.exp(-1.77*raw)


def grade(image, dust=None):
    image = np.asarray(image,dtype=np.float32)/255
    light = np.clip(image-.19,0,1)**1.12
    source = Image.fromarray(np.uint8(255*light))
    near = np.asarray(source.filter(ImageFilter.GaussianBlur(6.8)),dtype=np.float32)/255
    far = np.asarray(source.filter(ImageFilter.GaussianBlur(27)),dtype=np.float32)/255
    image += (1-image)*(.42*near+.36*far)
    if dust is not None:
        image += (1-image)*dust
    return Image.fromarray(np.uint8(255*np.clip(image,0,1)))


def stills(renderer, solar_only=False):
    w,h = 2128,1376
    board = Image.new("RGB",(w,h),"#090c13")
    draw = ImageDraw.Draw(board)
    large = font("msyhbd.ttc",49)
    label = font("msyhbd.ttc",31)
    small = font("msyh.ttc",21)
    draw.text((50,23),"深空回声",font=large,fill="#edf0fb")
    note = "黑底呈现样张"
    draw.text((2077-draw.textlength(note,font=small),55),note,font=small,fill="#a6b0c8")
    draw.line((50,104,2077,104),fill="#2d3446",width=2)
    for i,(name,_,palette,*_) in enumerate(SCENES):
        if i==0:
            palette=SOLAR_PALETTE
        destination=OUT/(name+".png")
        if solar_only and i:
            with Image.open(destination) as previous:
                frame=previous.copy()
        else:
            frame=grade(renderer.image(i,900,668,True,.8,palette=palette))
            frame.save(destination)
        x,y = 50+684*(i%3),127+600*(i//3)
        draw.text((x,y),name,font=label,fill="#f2f4fc")
        board.paste(frame.resize((660,490),Image.Resampling.LANCZOS),(x,y+52))
        edge = x
        for amount,color in zip(SHARES,palette):
            draw.rectangle((edge,y+556,edge+66*amount-1,y+566),fill="#"+color)
            edge += 66*amount
    scene=2
    x,y = 1418,727
    draw.text((x,y),"金星散开后",font=label,fill="#f2f4fc")
    nebula_path=OUT/"金星·星云.png"
    if solar_only:
        with Image.open(nebula_path) as previous:
            nebula=previous.copy()
    else:
        time, stage = 3.9,.88
        dust = ReleasedDust(scene).rasterize(900,668,time,stage)
        nebula = grade(renderer.image(scene,900,668,True,time,stage),dust)
        nebula.save(nebula_path)
    board.paste(nebula.resize((660,490),Image.Resampling.LANCZOS),(x,y+52))
    board.save(OUT/"五颗天体·黑底呈现.png")


def motion(renderer):
    width,height = 784,528
    fps, frames = 22,118
    index = 2
    dust = ReleasedDust(index)
    target = OUT/"金星·呈现动效.webm"
    command = [
        str(FFMPEG),"-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
        "-s",f"{width}x{height}","-r",str(fps),"-i","-","-an","-c:v","libvpx-vp9",
        "-pix_fmt","yuv420p","-crf","17","-b:v","0","-cpu-used","5","-row-mt","1",str(target),
    ]
    with subprocess.Popen(command,stdin=subprocess.PIPE) as encoder:
        for n in range(frames):
            time=n/fps+.8
            stage=float(ease((n/fps-1.15)/3.45))
            frame = renderer.image(index,width,height,True,time,stage)
            emission = dust.rasterize(width,height,time,stage) if stage>.07 else None
            encoder.stdin.write(grade(frame,emission).tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("Video encoding failed")


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=("stills","solar","motion"))
    mode=parser.parse_args().mode
    OUT.mkdir(exist_ok=True)
    renderer=Renderer(FRAGMENT)
    if mode=="motion":
        motion(renderer)
    else:
        stills(renderer,solar_only=(mode=="solar"))
