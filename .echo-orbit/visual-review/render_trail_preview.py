"""Preview a single-hue volumetric wake driven by each body's recent path."""

import argparse
import subprocess

import numpy as np
from PIL import Image, ImageDraw

from render_abstract_planets import ROOT, SCENES, font
from render_bundle_planets import FFMPEG
from render_flame_globes import Renderer
from render_nebula_preview import FRAGMENT, SOLAR_PALETTE, grade


OUT = ROOT / "单色拖影预览"
TRAILS = (
    ("橙红","ff410b",.05,-.12,1.78,.81),
    ("电蓝","4267ff",.87,.26,1.66,.85),
    ("玫红","ff26a9",1.69,-.40,1.68,.68),
    ("翠青","00f6b1",2.23,.41,1.56,.81),
    ("绯红","ff1c4a",3.18,-.29,1.73,.80),
)
LIFETIME = (2.15,1.78,2.09,2.22,1.92)
THICKNESS = (1.0,.84,.91,1.08,.96)
LAP = 5.2


def history(index, time):
    _, _, phase, tilt, horizontal, vertical = TRAILS[index]
    age = np.linspace(0,LIFETIME[index],36,dtype=np.float32)
    portion = age/LIFETIME[index]
    theta = (time-age)*(2*np.pi/LAP)+phase
    x = horizontal*np.cos(theta)+.19*np.sin(2*theta+.3*index)
    y = vertical*np.sin(theta)+.13*np.cos(3*theta-.3*index)
    c,s = np.cos(tilt),np.sin(tilt)
    x,y = c*x-s*y,s*x+c*y
    # Older silhouettes rise and roll as they diffuse into the wake.
    x += portion**1.70*.31*np.sin(6.1*portion+.65*theta+.59*index)
    y += portion**1.40*(.26+.25*np.sin(5.1*portion-.95*theta))
    breadth = THICKNESS[index]*(.66-.44*portion)*(.92+.23*np.sin(7.8*portion+theta))
    brightness = .44*(1-portion)**1.04*(.85+.15*np.sin(13.8*portion+1.3*theta))
    return np.ascontiguousarray(np.column_stack((x,y,breadth,brightness)),dtype=np.float32)


def render(renderer,index,width,height,time):
    ribbon = TRAILS[index][1],history(index,time)
    palette = SOLAR_PALETTE if index==0 else None
    return grade(renderer.image(index,width,height,True,time,palette=palette,trail=ribbon))


def stills(renderer):
    canvas = Image.new("RGB",(2016,1196),"#090c13")
    draw = ImageDraw.Draw(canvas)
    title = font("msyhbd.ttc",49)
    small = font("msyh.ttc",22)
    label = font("msyhbd.ttc",30)
    draw.text((48,25),"单色拖影",font=title,fill="#ebedf6")
    draw.line((48,103,1968,103),fill="#30374b",width=2)
    positions = ((48,130),(696,130),(1344,130),(372,650),(1020,650))
    previews = (1.75,1.09,.91,.93,3.79)
    for index, ((left,top),(name,*_), (label_color,value,*_)) in enumerate(zip(positions,SCENES,TRAILS)):
        frame = render(renderer,index,816,612,previews[index])
        frame.save(OUT/(name+".png"))
        draw.text((left,top),name,font=label,fill="#edf0fa")
        draw.ellipse((left+86,top+11,left+102,top+27),fill="#"+value)
        draw.text((left+115,top+5),label_color,font=small,fill="#b0b9d0")
        canvas.paste(frame.resize((624,468),Image.Resampling.LANCZOS),(left,top+49))
    canvas.save(OUT/"五颗天体·单色拖影.png")


def motion(renderer):
    tile_width,tile_height = 384,288
    width,height = 1152,576
    pos = ((0,0),(384,0),(768,0),(192,288),(576,288))
    fps,frames = 20,104
    target=OUT/"五颗天体·单色拖影.webm"
    command = [
        str(FFMPEG),"-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
        "-s",f"{width}x{height}","-r",str(fps),"-i","-","-an","-c:v","libvpx-vp9",
        "-pix_fmt","yuv420p","-crf","17","-b:v","0","-cpu-used","5","-row-mt","1",str(target),
    ]
    with subprocess.Popen(command,stdin=subprocess.PIPE) as encoder:
        for number in range(frames):
            montage = Image.new("RGB",(width,height),(1,1,3))
            tick=number/fps+.8
            for i,loc in enumerate(pos):
                montage.paste(render(renderer,i,tile_width,tile_height,tick),loc)
            encoder.stdin.write(montage.tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("Video encoding failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode",choices=("stills","motion"))
    mode=parser.parse_args().mode
    OUT.mkdir(exist_ok=True)
    (stills if mode=="stills" else motion)(Renderer(FRAGMENT))
