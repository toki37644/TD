"""Stage and build the rotating overview and native-feedback close-ups."""

from datetime import datetime
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
TD_BIN = Path('C:/Program Files/Derivative/TouchDesigner/bin')

STARTUP = '''from pathlib import Path
from traceback import format_exc

def onStart():
    source = Path(project.folder).parent.parent / 'live-fluids' / 'build_interactive_revision.py'
    try:
        namespace = dict(globals(), __file__=str(source), __name__='touchdesigner_build')
        exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), namespace)
        namespace['install_native']()
    except Exception:
        Path(project.folder, 'build-error.txt').write_text(format_exc(), encoding='utf-8')
'''

RELEASE_CLOCK = '''def onStart():
    root.time.play = True

def onFrameStart(frame):
    op('/project1/orbit_engine').module.tick()
'''

GLINTS = '''    if (scene >= 0 && uCamera.w > .02) {
        vec2 grainStep = vec2(.0039,.0057);
        vec3 soft = texture(sTD2DInputs[0], uv+vec2(grainStep.x,0.)).rgb;
        soft += texture(sTD2DInputs[0], uv-vec2(grainStep.x,0.)).rgb;
        soft += texture(sTD2DInputs[0], uv+vec2(0.,grainStep.y)).rgb;
        soft += texture(sTD2DInputs[0], uv-vec2(0.,grainStep.y)).rgb;
        float pulse = uAudio.x*.31+uAudio.w*.43;
        color += (cool*(soft.r*.17) + warm*(soft.g*.22) + whiteLight(scene)*(soft.b*.16))
                 * uCamera.w * (.83+pulse);
        color += (cool*motes.r*.22 + warm*motes.g*.22) * uCamera.w;
    }
'''


def revision_shader():
    source = (HERE / 'live_atlas.frag').read_text(encoding='utf-8')
    start = source.index('vec4 volumeSlice(')
    end = source.index('float lineSegment(', start)
    material = (HERE / 'atlas_feedback.glsl').read_text(encoding='utf-8')
    source = source[:start] + material + '\n' + source[end:]
    source = source.replace('graded * envelope * feather', 'graded * envelope * feather * 1.19')
    marker = '    if (scene>=0 && uTransition.x<.999)'
    return source.replace(marker, GLINTS + marker, 1)


def install_native():
    scene = op('/project1')
    shader = scene.op('solar_atlas')
    clock = scene.op('clock')
    folder = Path(project.folder)
    clock.par.framestart = False
    scene.op('orbit_engine').text = (HERE.parent/'orbit_runtime.py').read_text(encoding='utf-8')
    scene.op('atlas_pixel').text = revision_shader()

    builder_path = HERE/'build_tutorial_venus.py'
    builder_scope = dict(globals())
    exec(compile(builder_path.read_text(encoding='utf-8'), str(builder_path), 'exec'), builder_scope)
    earlier_material = scene.op('feedback_material')
    if earlier_material is not None:
        earlier_material.destroy()
    material = scene.create(baseCOMP, 'feedback_material')
    material.nodeX, material.nodeY = 210, -305
    material.color = (.27,.23,.41)
    page = material.appendCustomPage('Audio')
    page.appendFloat('Drive', label='Low Frequency and Attack')[0].val = .16
    page.appendFloat('Detail', label='Mid Frequencies')[0].val = .50
    final = builder_scope['build_feedback_material'](
        material, "float(parent().par.Drive)", "float(parent().par.Detail)", (960,540))
    output = material.create(outTOP, 'out1')
    output.nodeX, output.nodeY = 3580, 160
    output.inputConnectors[0].connect(final)
    material.par.opviewer = output.path

    for asset in list(scene.vfs):
        if asset.name == 'body-volumes.png':
            asset.destroy()
    obsolete_volume = scene.op('body_volumes')
    if obsolete_volume is not None:
        obsolete_volume.destroy()
    material.outputConnectors[0].connect(shader.inputConnectors[3])
    assert shader.inputConnectors[3].connections, 'Feedback material is disconnected'
    final_top = scene.op('out_image')
    final_top.cook(force=True)
    assert (final_top.width, final_top.height) == (1200,675)
    assert not shader.errors(), shader.errors()
    assert not final.errors(), final.errors()
    assert not output.errors(), output.errors()
    clock.text = RELEASE_CLOCK
    clock.par.framestart = True
    root.time.play = True
    project.performOnStart = True
    release = folder / f'Interactive-release-{datetime.now():%Y%m%d-%H%M%S}.toe'
    assert project.save(str(release))
    (folder/'build-ok.txt').write_text(str(release)+'\n', encoding='utf-8')
    run('args[0](args[1])', verify_native, HERE/'verify_atlas_revision.py', delayFrames=48)


def verify_native(verification):
    namespace = dict(globals(), __file__=str(verification))
    exec(compile(verification.read_text(encoding='utf-8-sig'), str(verification), 'exec'), namespace)


def stage():
    folder = HERE.parent / '.venus-build' / 'interactive'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'Interactive-stage.toe'
    from prepare_install import dat
    with TemporaryDirectory(dir=folder) as temporary:
        pack = Path(temporary).resolve()
        assert pack.parent == folder.resolve()
        source = pack / target.name
        shutil.copyfile(WORKSPACE/'深空回声-彩雾交互版.toe', source)
        subprocess.run([str(TD_BIN/'toeexpand.exe'), source.name], cwd=pack)
        clock = source.with_suffix('.toe.dir') / 'project1' / 'clock.text'
        toc = source.with_suffix('.toe.toc')
        if not clock.is_file() or not toc.is_file():
            raise RuntimeError('TouchDesigner expansion did not produce a network')
        dat(clock, STARTUP)
        params = clock.with_suffix('.parm')
        body = params.read_text(encoding='ascii')
        if 'start 67108864 on' not in {line.rstrip() for line in body.splitlines()}:
            body = body.replace('framestart 67108864 on', 'start 67108864 on')
            params.write_text(body, encoding='ascii')
        subprocess.run([str(TD_BIN/'toecollapse.exe'), toc.name], cwd=pack, check=True)
        shutil.copyfile(source, target)
    print(target)


if __name__ == '__main__':
    stage()
