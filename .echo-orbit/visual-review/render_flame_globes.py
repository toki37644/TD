"""Render marbled 3D flame volumes for visual review."""

import argparse
import ctypes
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw

from render_abstract_planets import ROOT, SCENES, SHARES, font, rgb
from render_bundle_planets import FFMPEG, PLUMES, STYLE


OUT = ROOT / "火焰色束星球"
SIZE = 112
PHASES = (.22,1.51,2.28,-.62,1.77)
VIEWS = (.367,.369,.371,.367,.369)


def make_volume(index, size=SIZE):
    grid = np.linspace(-1.27,1.27,size,dtype=np.float32)
    z,y,x = np.meshgrid(grid,grid,grid,indexing="ij")
    _, axis, sweep, fold, _ = STYLE[index]
    axis *= .87
    u = x*np.cos(axis)+y*np.sin(axis)
    v = -x*np.sin(axis)+y*np.cos(axis)
    longitude = np.arctan2(u,z)
    latitude = np.arctan2(v,np.hypot(u,z))
    radius = np.sqrt(x*x+y*y+z*z)
    result = np.zeros((size,size,size,4),dtype=np.float32)
    palette = np.asarray([rgb(code) for code in SCENES[index][2]], dtype=np.float32)
    for band, (weight, spec, color) in enumerate(zip(SHARES,PLUMES[index],palette)):
        lat0, width0, phase, r0 = spec
        lane = longitude+phase+.18*np.sin(3*longitude+phase)
        turn = np.sin(2*lane+.64*np.sin(lane))
        mid = lat0+sweep*np.sin(lane)+fold*.86*turn
        mid += .105*np.sin(4*longitude+.88*phase+1.1*radius)
        width = width0*(.87+.37*np.sin(2*longitude+phase+.64*np.sin(lane))+.25*np.sin(4*longitude+2*phase))
        width = np.clip(width,.034,.37)
        axis_offset = (latitude-mid)/width
        volume_radius = r0-.10+.082*np.sin(2*lane+.5)+.078*np.cos(lane-phase)
        volume_radius += .057*np.tanh(axis_offset)*np.sin(lane+.32)
        depth = .086+.093*(.5+.5*np.sin(2*lane+phase))+.044*np.sin(3*longitude)
        separation = (radius-volume_radius)/depth
        distance = axis_offset**2+separation**2
        core = np.exp(-.66*distance)
        edge = np.exp(-((axis_offset-.49*np.sin(3*lane))**2*1.38+separation**2*.34))
        dye = core*(.66+.34*np.cos(lane-.56*phase)**2)+edge*.24
        dye *= .72+.28*(.5+.5*np.sin(3*lane+.82*radius+band))
        dye *= (weight/10)*5_600_000*(size/SIZE)**3/dye.sum(dtype=np.float64)
        result[...,:3] += dye[...,None]*color
        result[...,3] += dye
    return np.ascontiguousarray(result.astype(np.float16))


class Renderer:
    def __init__(self, fragment_path=None):
        legacy = (ROOT/".echo-work"/"shader_qa.py").read_text(encoding="utf-8")
        gl = {}
        exec(legacy.split("pr=CreateProgram()",1)[0],gl)
        gl["register"](
            gl["g"],"gl",
            "GenTextures vip;BindTexture vuu;TexParameteri vuui;TexImage3D vuiiiiiiuup;Uniform4fv viip",
        )
        self.gl = gl
        vertex = """#version 300 es
out vec2 uv;
void main() {
    uv=vec2((gl_VertexID<<1)&2,gl_VertexID&2);
    gl_Position=vec4(uv*2.-1.,0.,1.);
}"""
        if fragment_path is None:
            fragment_path = OUT.parent/".echo-orbit"/"visual-review"/"flame_globe.frag"
        fragment = fragment_path.read_text(encoding="utf-8")
        self.program = gl["CreateProgram"]()
        gl["AttachShader"](self.program,gl["shader"](0x8B31,vertex))
        gl["AttachShader"](self.program,gl["shader"](0x8B30,fragment))
        gl["LinkProgram"](self.program)
        linked = ctypes.c_int()
        gl["GetProgramiv"](self.program,0x8B82,ctypes.byref(linked))
        if not linked.value:
            log = ctypes.create_string_buffer(8192)
            gl["GetProgramInfoLog"](self.program,len(log),None,log)
            raise RuntimeError(log.value.decode(errors="replace"))
        gl["UseProgram"](self.program)
        names = (
            "uFrame","uView","uPrimary","uAccent","uStage","uSolarGreen","uSolarCyan","uSolarBlue",
            "uTrail","uHistory[0]",
        )
        self.uniform = {name:gl["GetUniformLocation"](self.program,name.encode()) for name in names}
        self.textures = (ctypes.c_uint*len(SCENES))()
        gl["GenTextures"](len(SCENES),self.textures)
        for i,tex in enumerate(self.textures):
            gl["BindTexture"](0x806F,tex)
            for param,value in ((0x2801,0x2601),(0x2800,0x2601),(0x2802,0x812F),(0x2803,0x812F),(0x8072,0x812F)):
                gl["TexParameteri"](0x806F,param,value)
            volume = make_volume(i)
            gl["TexImage3D"](0x806F,0,0x881A,SIZE,SIZE,SIZE,0,0x1908,0x140B,volume.ctypes.data)

    def image(self, scene, width, height, dark, tick, stage=0, palette=None, trail=None):
        gl = self.gl
        gl["BindTexture"](0x806F,self.textures[scene])
        if palette is None:
            palette = SCENES[scene][2]
        view = (VIEWS[scene],dark,.455 if scene==0 else .5,PHASES[scene])
        trail_params = (0,0,0,0)
        if trail is not None:
            hue,history = trail
            view = (.177,dark,.50,PHASES[scene])
            trail_params = (*rgb(hue),1)
            gl["Uniform4fv"](self.uniform["uHistory[0]"],len(history),history.ctypes.data)
        params = {
            "uFrame":(width,height,tick,scene),
            "uView":view,
            "uPrimary":(*rgb(palette[0]),1),
            "uAccent":(*rgb(palette[1]),1),
            "uStage":(stage,0,0,0),
            "uSolarGreen":(*rgb(palette[2]),1),
            "uSolarCyan":(*rgb(palette[3]),1),
            "uSolarBlue":(*rgb(palette[4]),1),
            "uTrail":trail_params,
        }
        for name,values in params.items():
            gl["Uniform4f"](self.uniform[name],*values)
        gl["Viewport"](0,0,width,height)
        gl["DrawArrays"](4,0,3)
        buffer = np.empty((height,width,4),np.uint8)
        gl["ReadPixels"](0,0,width,height,0x1908,0x1401,buffer.ctypes.data)
        return Image.fromarray(buffer[::-1,:,:3].copy())


def stills(renderer):
    cream = "#f7f4ef"
    board = Image.new("RGB",(2076,1370),cream)
    draw = ImageDraw.Draw(board)
    title = font("msyhbd.ttc",48)
    small = font("msyh.ttc",22)
    label = font("msyhbd.ttc",31)
    draw.text((48,27),"火焰色束",font=title,fill="#282021")
    caption = "五色比例  5 ∶ 2 ∶ 1 ∶ 1 ∶ 1"
    draw.text((2027-draw.textlength(caption,font=small),52),caption,font=small,fill="#635b5b")
    draw.line((48,108,2028,108),fill="#d9d0c9",width=2)
    images = []
    for i, (name,_,palette,*_) in enumerate(SCENES):
        image = renderer.image(i,848,638,False,.77)
        image.save(OUT/(name+".png"))
        images.append(image)
        x,y = 48+i%3*668,133+i//3*598
        draw.text((x,y),name,font=label,fill="#282021")
        board.paste(image.resize((644,485),Image.Resampling.LANCZOS),(x,y+52))
        endpoint = 0
        for part,color in zip(SHARES,palette):
            left = x+round(644*endpoint/10)
            endpoint += part
            right = x+round(644*endpoint/10)
            draw.rectangle((left,y+548,right-1,y+557),fill="#"+color)
    x,y = 1384,731
    draw.text((x,y),"球面局部",font=label,fill="#282021")
    draw.text((x+146,y+5),"地球",font=small,fill="#635b5b")
    detail = images[3].crop((206,118,624,433)).resize((644,485),Image.Resampling.LANCZOS)
    board.paste(detail,(x,y+52))
    board.save(OUT/"五颗天体·火焰色束.png")


def motion(renderer):
    tile_width, height = 420, 400
    width = 2*tile_width
    fps, duration = 20, 4
    output = OUT/"火焰色束·厚薄变化.webm"
    command = [
        str(FFMPEG),"-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{width}x{height}",
        "-r",str(fps),"-i","-","-an","-c:v","libvpx-vp9","-pix_fmt","yuv420p","-crf","17",
        "-b:v","0","-cpu-used","5","-row-mt","1",str(output),
    ]
    with subprocess.Popen(command,stdin=subprocess.PIPE) as encoder:
        for frame in range(fps*duration):
            t = .77+frame/fps
            pair = [np.asarray(renderer.image(i,tile_width,height,True,t)) for i in (0,3)]
            encoder.stdin.write(np.concatenate(pair,axis=1).tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("Video encoding failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode",choices=("stills","motion"))
    mode = parser.parse_args().mode
    OUT.mkdir(exist_ok=True)
    start = time.perf_counter()
    (stills if mode=="stills" else motion)(Renderer())
    print(f"{mode}: {time.perf_counter()-start:.1f}s")
