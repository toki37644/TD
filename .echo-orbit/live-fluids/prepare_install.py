"""Stage a copy of the previous native project for the TouchDesigner installer."""

from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ORBIT = HERE.parent
BIN = Path("C:/Program Files/Derivative/TouchDesigner/bin")
SEED = HERE/"Atlas-seed.toe"
STAGE = HERE/"Atlas-fluid-stage.toe"
NAMES = ("uCamera","uPointer","uAudio","uScene","uSun","uMercury","uVenus","uEarth",
         "uMars","uLabel","uTransition")


def section(source, start, end, replacement):
    first = source.index(start)
    last = source.index(end,first)
    return source[:first]+replacement+source[last:]


def generate_shader():
    shader = (ORBIT/"solar_atlas.frag").read_text(encoding="utf-8")
    preview = (ORBIT/"visual-review"/"luminous_nebula.frag").read_text(encoding="utf-8")
    body = (HERE/"body.glsl").read_text(encoding="utf-8")
    sun = preview[preview.index("vec3 thermalColor("):preview.index("vec3 withTrail(")]
    for name,value in {
        "uPrimary": "vec3(1.,.302,.039)",
        "uAccent": "vec3(1.,.761,.145)",
        "uSolarGreen": "vec3(.522,.831,.286)",
        "uSolarCyan": "vec3(.082,.620,.612)",
        "uSolarBlue": "vec3(.106,.318,.561)",
    }.items():
        sun = sun.replace(name+".rgb",value)
    sun = sun.replace("    rayFalloff*=1.-uTrail.a*smoothstep(1.12,2.05,r);\n","")
    sun = "const vec3 BLACK = vec3(.004,.006,.012);\n"+sun
    shader = section(shader,"vec3 coloredLight(","float lineSegment(",sun+body+"\n")
    shader = shader.replace("out vec4 fragColor;", "uniform vec4 uTransition;\n\nout vec4 fragColor;")
    shader = section(shader,"    vec2 spread = 1.7","    vec3 cool =", "")
    shader = shader.replace(", time, visiblePoints)",", time)")
    shader = shader.replace(" • "," ")
    shader = shader.replace("coherent","settled")
    shader = shader.replace("(.273, .445, .627, .817)","(.154, .318, .388, .653)")
    shader = shader.replace("""    float trackRadius = length(orbitUV);
    float trackAngle = atan(orbitUV.y, orbitUV.x);
""","")
    shader = shader.replace("""        float trace = orbitTrace(trackRadius, orbitR[i], pixels, .90);""","""        float height = orbitUV.y/orbitR[i];
        float sine = 2.*height/(.68+sqrt(max(.003,.4624+.88*height)));
        vec2 actualTrack=vec2(orbitUV.x,orbitR[i]*sine);
        float trackRadius=length(actualTrack);
        float trackAngle=atan(actualTrack.y,actualTrack.x);
        float trace = orbitTrace(trackRadius, orbitR[i], pixels, .90);""")
    shader = shader.replace("atlasDial(relativeSun, disk / vec2(1.0, .38), time)",
                            "atlasDial(relativeSun, turn(-.032)*relativeSun, time)")
    shader = shader.replace("float gradeAmount = .31;","float gradeAmount = .81;")
    shader = shader.replace("    vec3 graded = mix(footage, light * tint, gradeAmount);",
        """    vec3 theme = wakeTint(scene);
    vec3 deep = mix(coolTint(scene),theme,.47);
    vec3 lit = mix(theme, normalize(theme+.36), smoothstep(.48,.92,light)*.55);
    vec3 graded = mix(footage, mix(deep,lit,smoothstep(.05,.54,light))*light*1.62, gradeAmount);""")
    # The tint function is used by both the scene backdrop and the compact wake.
    shader = shader.replace("vec3 nebulaLayer(", "vec3 wakeTint(int id);\n\nvec3 nebulaLayer(")
    shader = shader.replace("    color += motes.b * vec3(.89, .91, 1.0) * (1.22 * skyLight);",
        """    color += motes.b * vec3(.89, .91, 1.0) * (1.22 * skyLight);
    if (scene>=0 && uTransition.x<.999) {
        vec3 eventHue=wakeTint(scene);
        color += sin(3.14159265*uTransition.x) * (motes.r*.43+motes.g*.67+motes.b*.29)*eventHue;
    }""")
    return shader


def dat(target, content):
    data = content.encode("utf-8")
    before = target.read_bytes()
    assert len(before)-27 == int.from_bytes(before[23:27],"big")
    target.write_bytes(before[:23]+len(data).to_bytes(4,"big")+data)


def main():
    stage_tree = STAGE.with_suffix(".toe.dir")
    shutil.copytree(SEED.with_suffix(".toe.dir"),stage_tree,dirs_exist_ok=True)
    shutil.copyfile(SEED.with_suffix(".toe.toc"),STAGE.with_suffix(".toe.toc"))
    project = stage_tree/"project1"
    content = """from pathlib import Path

def onStart():
    source = Path(project.folder) / 'install_fluid_atlas.py'
    exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), globals())
"""
    dat(project/"clock.text",content)
    params = project/"clock.parm"
    text = params.read_text(encoding="ascii")
    text = text.replace("framestart 67108864 on","start 67108864 on")
    params.write_text(text,encoding="ascii")
    (HERE/"live_atlas.frag").write_text(generate_shader(),encoding="utf-8")
    subprocess.run([str(BIN/"toecollapse.exe"),STAGE.with_suffix(".toe.toc").name],cwd=HERE,check=True)
    print(STAGE)


if __name__=="__main__":
    main()
