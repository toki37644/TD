"""Replace the body layer in a copy of the working TouchDesigner atlas."""

from pathlib import Path
import shutil
import subprocess
import sys

from prepare_install import BIN, HERE, dat

BASE=HERE/"Atlas-fluid-final.toe"
STAGE=HERE/"Atlas-beat-stage.toe"
SOURCE=HERE/"beat_atlas.frag"


BODY="""vec3 bodyLayer(vec3 background, vec2 world, vec2 cursor, vec4 body, int id,
               float visible, bool selected, float time) {
    if (visible<.002) return background;
    float transition=selected?uTransition.x:1.;
    float movement=smoothstep(0.,1.,transition);
    vec2 screen=(world-uCamera.xy)*uCamera.z;
    vec2 center=mix(uTransition.yz,(body.xy-uCamera.xy)*uCamera.z,movement);
    float radius=mix(uTransition.w,body.z*uCamera.z,movement);
    vec2 q=(screen-center)/max(radius,.016);
    float r=length(q);
    if (r>(id==0?2.25:1.42)) return background;
    float engagement=selected?uScene.y:0.;
    float bass=uAudio.x*engagement;
    float scatter=sin(3.14159265*transition);
    visible*=1.-.94*smoothstep(.18,.89,scatter);
    background+=visible*nearWake(q,body,id,time,.82*bass);
    if (id==0) {
        float fade=1.-smoothstep(1.35,2.25,r);
        background+=visible*.28*fade*(solarCorona(q,time+body.w)-BLACK);
    }
    vec3 surface=beatShell(q,id,cursor,time,body.w,uAudio,engagement,radius*675.);
    float peak=max(max(surface.r,surface.g),surface.b);
    return background*(1.-.78*visible*smoothstep(.04,.48,peak))+surface*visible;
}

"""


def shader_text():
    old=(HERE/"live_atlas.frag").read_text(encoding="utf-8")
    warp=old[old.index("vec2 flowEddy("):old.index("vec4 luminousDye(")]
    start=old.index("vec4 volumeSlice(")
    end=old.index("float lineSegment(",start)
    material=(HERE/"beat_shell.glsl").read_text(encoding="utf-8")
    shader=old[:start]+warp+material+"\n"+BODY+old[end:]
    return shader.replace("graded * envelope * feather","graded * envelope * feather * .67")


def main():
    shader=shader_text()
    SOURCE.write_text(shader,encoding="utf-8")
    if "--shader-only" in sys.argv:
        return
    if not BASE.with_suffix(".toe.dir").exists():
        subprocess.run([str(BIN/"toeexpand.exe"),BASE.name],cwd=HERE,check=True)
    tree=STAGE.with_suffix(".toe.dir")
    shutil.copytree(BASE.with_suffix(".toe.dir"),tree,dirs_exist_ok=True)
    shutil.copyfile(BASE.with_suffix(".toe.toc"),STAGE.with_suffix(".toe.toc"))
    project=tree/"project1"
    dat(project/"atlas_pixel.text",shader)
    dat(project/"clock.text",'''from pathlib import Path

def onStart():
    source=Path(project.folder)/"validate_beat_atlas.py"
    exec(compile(source.read_text(encoding="utf-8"),str(source),"exec"),globals())
''')
    subprocess.run([str(BIN/"toecollapse.exe"),STAGE.with_suffix(".toe.toc").name],cwd=HERE,check=True)


if __name__=="__main__":
    main()
