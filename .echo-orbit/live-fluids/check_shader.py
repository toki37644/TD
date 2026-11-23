"""Compile the TouchDesigner fragment and check the view states offscreen."""

from pathlib import Path
import ctypes
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw


HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from orbit_runtime import CameraState, ParticleField, SCENES, Spectrum

scope={}
source=(HERE.parent.parent/".echo-work"/"shader_qa.py").read_text(encoding="utf-8")
exec(source.split("pr=CreateProgram()",1)[0],scope)
scope["register"](scope["g"],"gl",
                  "GenTextures vip;ActiveTexture vu;BindTexture vuu;TexParameteri vuui;"
                  "TexImage2D vuiiiiiiup;Uniform1iv viip")

program=scope["CreateProgram"]()
vertex="""#version 300 es
out vec2 vUV;
void main(){
    vUV=vec2((gl_VertexID<<1)&2,gl_VertexID&2);
    gl_Position=vec4(vUV*2.-1.,0.,1.);
}"""
prefix="""#version 300 es
precision highp float;
precision highp int;
in vec2 vUV;
uniform sampler2D sTD2DInputs[4];
#define TDOutputSwizzle(v) v
"""
shader_path=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/"live_atlas.frag"
fragment=prefix+shader_path.read_text(encoding="utf-8")
for kind,shader in ((0x8B31,vertex),(0x8B30,fragment)):
    scope["AttachShader"](program,scope["shader"](kind,shader))
scope["LinkProgram"](program)
linked=ctypes.c_int()
scope["GetProgramiv"](program,0x8B82,ctypes.byref(linked))
if not linked.value:
    log=ctypes.create_string_buffer(8192)
    scope["GetProgramInfoLog"](program,len(log),None,log)
    raise RuntimeError(log.value.decode(errors="replace"))
scope["UseProgram"](program)
tex=(ctypes.c_uint*4)()
scope["GenTextures"](4,tex)
scope["Uniform1iv"](scope["GetUniformLocation"](program,b"sTD2DInputs[0]"),
                    4,(ctypes.c_int*4)(0,1,2,3))
names=("uCamera","uPointer","uAudio","uScene","uSun","uMercury","uVenus","uEarth","uMars","uLabel","uTransition")
uniforms=[scope["GetUniformLocation"](program,name.encode()) for name in names]


def upload(index, texture):
    scope["ActiveTexture"](0x84C0+index)
    scope["BindTexture"](0x0DE1,tex[index])
    scope["TexParameteri"](0x0DE1,0x2801,0x2601)
    scope["TexParameteri"](0x0DE1,0x2800,0x2601)
    a=np.ascontiguousarray(texture)
    scope["TexImage2D"](0x0DE1,0,0x1908,a.shape[1],a.shape[0],0,0x1908,0x1401,a.ctypes.data)


def upload_image(index,path):
    if path.exists():
        upload(index,np.asarray(Image.open(path).convert("RGBA"))[::-1])
    else:
        upload(index,np.zeros((10,10,4),np.uint8))


upload_image(1,HERE/"nebula-test.png")
upload_image(2,HERE.parent/"stock"/"body-names.png")
upload_image(3,HERE/"body-volumes.png")
field=ParticleField()
out=HERE/("offscreen" if len(sys.argv)==1 else shader_path.stem+"-preview")
out.mkdir(exist_ok=True)


def render(state, width=1200, height=675):
    upload(0,field.render(state))
    for uniform,value in zip(uniforms,state.uniforms()):
        scope["Uniform4f"](uniform,*value)
    scope["Viewport"](0,0,width,height)
    scope["DrawArrays"](4,0,3)
    picture=np.empty((height,width,4),np.uint8)
    scope["ReadPixels"](0,0,width,height,0x1908,0x1401,picture.ctypes.data)
    assert picture[:,:,:3].max()>50
    return Image.fromarray(picture[::-1,:,:3].copy())


def capture(name,state):
    render(state).save(out/(name+".png"))


overview=CameraState(0)
overview.advance(4.,(.08,.08),False)
capture("overview",overview)
for i,name in enumerate(SCENES[1:]):
    state=CameraState(0)
    state.advance(4.,(.5,.5),False)
    pointer=state.center_uv(i)
    for frame in range(1,70):
        state.advance(4+frame/60,pointer,True)
    assert state.focus==i and not state.entered
    state.click(pointer)
    assert state.entered
    if i==2:
        for frame in range(70,112):
            state.advance(4+frame/60,(.39,.62),True)
        capture("venus_dissolve",state)
    for frame in range(112,235):
        state.advance(4+frame/60,(.44,.58),True)
    state.energy[:]=(.35,.28,.21,.11)
    assert state.shown==i and state.arrival==1
    capture(name,state)
    state.click((.053,.918))
    assert not state.entered
print("GLSL compiled and rendered; all five hover, click and button-return routes passed")


def make_demo():
    workspace=HERE.parent.parent
    destination=workspace/"音乐星球Demo"
    destination.mkdir(exist_ok=True)
    font_file=Path("C:/Windows/Fonts/msyhbd.ttc")
    from PIL import ImageFont
    title=ImageFont.truetype(font_file,49)
    label=ImageFont.truetype(font_file,30)
    board=Image.new("RGB",(2108,1084),"#080b13")
    draw=ImageDraw.Draw(board)
    draw.text((44,23),"音乐星球 Demo",font=title,fill="#eef1fa")
    draw.line((44,106,2064,106),fill="#283141",width=2)
    placements=((44,129),(726,129),(1408,129),(44,597),(726,597),(1408,597))
    titles=("太阳","水星","金星","地球","火星","金星局部")
    keys=(*SCENES[1:],"venus")
    for i,(place,key,name) in enumerate(zip(placements,keys,titles)):
        x,y=place
        draw.text((x,y),name,font=label,fill="#eef1fa")
        with Image.open(out/(key+".png")) as art:
            crop=(293,101,907,476) if i==5 else (207,95,993,575)
            tile=art.crop(crop).resize((656,401),Image.Resampling.LANCZOS)
        board.paste(tile,(x,y+48))
    board.save(destination/"五颗天体·节奏球体.png")

    encoder=Path("C:/Program Files/Derivative/TouchDesigner/bin/ffmpeg.exe")
    audio=workspace/"深空回声-音乐试听"/"04-金星.mp3"
    fps,frames=24,128
    width,height=816,460
    offset=1.2
    duration=frames/fps
    decoding=[str(encoder),"-loglevel","error","-ss",str(offset),"-i",str(audio),
              "-t",str(duration),"-f","f32le","-ac","1","-ar","44100","pipe:1"]
    wave=np.frombuffer(subprocess.check_output(decoding),dtype="<f4")
    analyzer=Spectrum()
    app=CameraState(0.)
    app.advance(4.,(.5,.5),False)
    hover=app.center_uv(2)
    for i in range(1,81):
        app.advance(4+i/60,hover,True)
    app.click(hover)
    for i in range(81,225):
        app.advance(4+i/60,(.45,.61),True)
    start=app.last
    target=destination/"金星·节拍演示.webm"
    command=[str(encoder),"-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
             "-s",f"{width}x{height}","-r",str(fps),"-i","-","-ss",str(offset),"-i",str(audio),
             "-t",str(duration),"-map","0:v","-map","1:a","-c:v","libvpx-vp9","-pix_fmt","yuv420p",
             "-crf","16","-b:v","0","-cpu-used","5","-row-mt","1","-c:a","libopus","-b:a","112k",str(target)]
    with subprocess.Popen(command,stdin=subprocess.PIPE) as movie:
        for i in range(frames):
            lo,hi=round(44100*i/fps),round(44100*(i+1)/fps)
            band=analyzer.read(wave[lo:hi])
            app.energy[:]=.51*app.energy+.49*band
            cursor_shift=.021*np.sin(i/fps*1.20)
            app.advance(start+(i+1)/fps,(.49+cursor_shift,.56),True)
            movie.stdin.write(render(app,width,height).tobytes())
        movie.stdin.close()
        if movie.wait():
            raise RuntimeError("Video encoding failed")


if "--demo" in sys.argv:
    make_demo()
