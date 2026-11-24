"""Stage and build the rotating overview and native-feedback close-ups."""

from datetime import datetime
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
TD_BIN = Path('C:/Program Files/TouchDesigner/bin')
if not (TD_BIN / 'toeexpand.exe').is_file():
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

WHEEL_CALLBACK = '''def onValueChange(panelValue, oldValue=None):
    op('/project1/orbit_engine').module.scroll(panelValue.val)
'''

LABEL_ATLAS = r'''
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$mask = [Drawing.Bitmap]::new(256,720)
$canvas = [Drawing.Graphics]::FromImage($mask)
$canvas.Clear([Drawing.Color]::Black)
$canvas.TextRenderingHint = 'AntiAliasGridFit'
$face = [Drawing.Font]::new('Segoe UI', 20, [Drawing.FontStyle]::Regular, [Drawing.GraphicsUnit]::Pixel)
$chinese = [Drawing.Font]::new('Microsoft YaHei UI', 39, [Drawing.FontStyle]::Regular, [Drawing.GraphicsUnit]::Pixel)
$english = [Drawing.Font]::new('Segoe UI', 23, [Drawing.FontStyle]::Regular, [Drawing.GraphicsUnit]::Pixel)
$align = [Drawing.StringFormat]::new()
$align.Alignment = 'Center'
$align.LineAlignment = 'Center'
$words = 'Sun', 'Mercury', 'Venus', 'Earth', 'Mars'
$names = '太阳', '水星', '金星', '地球', '火星'
for ($i = 0; $i -lt $words.Count; $i++) {
    $y = $i*144
    $canvas.DrawString($words[$i].ToUpperInvariant(), $face, [Drawing.Brushes]::White,
                       [Drawing.RectangleF]::new(0,$y,256,56), $align)
    $canvas.DrawString($names[$i], $chinese, [Drawing.Brushes]::White,
                       [Drawing.RectangleF]::new(0,($y+56),256,56), $align)
    $canvas.DrawString($words[$i], $english, [Drawing.Brushes]::White,
                       [Drawing.RectangleF]::new(0,($y+112),256,32), $align)
}
$path = Join-Path (Get-Location).Path 'body-names-bilingual.png'
$mask.Save($path, [Drawing.Imaging.ImageFormat]::Png)
$align.Dispose()
$face.Dispose()
$chinese.Dispose()
$english.Dispose()
$canvas.Dispose()
$mask.Dispose()
'''

GLINTS = '''    if (scene >= 0 && uCamera.w > .02) {
        float pulse = uAudio.x*.31+uAudio.w*.43;
        vec3 sparks = cool*motes.r*.41 + warm*motes.g*.43 + whiteLight(scene)*motes.b*.16;
        color += sparks*uCamera.w*(.86+pulse);
    }
'''

NEBULA_COMPOSITE = '''vec3 nebulaLayer(vec2 screen, vec2 pointer, int scene) {
    vec3 background = vec3(.0015,.0016,.0032);
    if (scene < 0 || uCamera.w < .002) return background;
    return background + texture(sTD2DInputs[1], vUV.st).rgb * smoothstep(.07,.94,uCamera.w);
}
'''


def revision_shader():
    source = (HERE / 'live_atlas.frag').read_text(encoding='utf-8')
    start = source.index('vec4 volumeSlice(')
    end = source.index('float lineSegment(', start)
    material = (HERE / 'atlas_feedback.glsl').read_text(encoding='utf-8')
    source = source[:start] + material + '\n' + source[end:]
    start = source.index('vec3 nebulaLayer(')
    end = source.index('vec3 whiteLight(', start)
    source = source[:start] + NEBULA_COMPOSITE + source[end:]
    marker = '    if (scene>=0 && uTransition.x<.999)'
    return source.replace(marker, GLINTS + marker, 1)


def install_native():
    scene = op('/project1')
    shader = scene.op('solar_atlas')
    clock = scene.op('clock')
    folder = Path(project.folder)
    clock.par.framestart = False
    scene.op('orbit_engine').text = (HERE.parent/'orbit_runtime.py').read_text(encoding='utf-8')
    shader.seq.vec.numBlocks = 12
    shader.par.vec11name = 'uView'
    scene.op('atlas_pixel').text = revision_shader()

    for index, name, filename in ((3, 'feedback_material', 'build_tutorial_venus.py'),
                                  (4, 'closeup_feedback', 'rebuild_tutorial_graph.py')):
        previous = scene.op(name)
        if previous is not None:
            previous.destroy()
        material = scene.create(baseCOMP, name)
        material.nodeX, material.nodeY = 210, -305 - 135 * (index - 3)
        material.color = (.27,.23,.41)
        page = material.appendCustomPage('Motion')
        builder_path = HERE / filename
        scope = dict(globals(), __file__=str(builder_path))
        exec(compile(builder_path.read_text(encoding='utf-8'), str(builder_path), 'exec'), scope)
        if index == 3:
            page.appendFloat('Drive', label='Low Frequency and Attack')[0].val = .16
            page.appendFloat('Detail', label='Mid Frequencies')[0].val = .50
            final = scope['build_feedback_material'](
                material, 'float(parent().par.Drive)', 'float(parent().par.Detail)', (1280, 720))
        else:
            page.appendFloat('Harmonicgain', label='Audio Harmonic Gain')[0].val = .50
            final = scope['build_graph'](material, 'float(parent().par.Harmonicgain)', scope['FRAME_SIZE'])
        output = material.create(outTOP, 'out1')
        output.nodeX, output.nodeY = final.nodeX + 205, 160
        output.inputConnectors[0].connect(final)
        material.par.opviewer = output.path
        material.outputConnectors[0].connect(shader.inputConnectors[index])
        assert shader.inputConnectors[index].connections, name
        final.cook(force=True)
        assert not final.errors(), final.errors()
        assert not output.errors(), output.errors()
        issues = [(node.name, node.errors()) for node in material.children if node.errors()]
        assert not issues, issues

    for asset in list(scene.vfs):
        if asset.name == 'body-volumes.png':
            asset.destroy()
    obsolete_volume = scene.op('body_volumes')
    if obsolete_volume is not None:
        obsolete_volume.destroy()
    engine = scene.op('orbit_engine').module
    width, height = engine.FRAME_SIZE
    shader.par.resolutionw, shader.par.resolutionh = width, height
    panel = scene.op('viewport')
    panel.par.w, panel.par.h = width, height
    panel.par.mousewheel = True
    wheel = scene.op('wheel_zoom')
    if wheel is None:
        wheel = scene.create(panelexecuteDAT, 'wheel_zoom')
    wheel.nodeX, wheel.nodeY = -185, -138
    wheel.par.panels = panel.path
    wheel.par.panelvalue = 'wheel'
    wheel.par.offtoon, wheel.par.ontooff, wheel.par.valuechange = False, False, True
    wheel.text = WHEEL_CALLBACK
    names = 'body-names-bilingual.png'
    for asset in list(scene.vfs):
        if asset.name in ('body-names.png', 'body-names-en.png', names, 'nebula-motion.mp4', 'spinning-galaxy.mp4'):
            asset.destroy()
    scene.vfs.addFile(str(folder / names), overrideName=names)
    scene.op('planet_names').par.file = f'vfs:/project1:{names}'
    for name in ('nebula_footage', 'nebula_field', 'nebula_pixel'):
        previous = scene.op(name)
        if previous is not None:
            previous.destroy()
    pixel = scene.create(textDAT, 'nebula_pixel')
    pixel.nodeX, pixel.nodeY = 10, 110
    pixel.text = (HERE / 'atlas_nebula.glsl').read_text(encoding='utf-8')
    nebula = scene.create(glslTOP, 'nebula_field')
    nebula.nodeX, nebula.nodeY = 215, 110
    nebula.par.pixeldat = pixel.path
    nebula.par.outputresolution = 'custom'
    nebula.par.resolutionw, nebula.par.resolutionh = width, height
    nebula.seq.vec.numBlocks = 3
    for i, name in enumerate(('uPointer', 'uAudio', 'uScene')):
        getattr(nebula.par, f'vec{i}name').val = name
    nebula.par.vec2valuex = -1.
    shader.inputConnectors[1].connect(nebula)
    nebula.cook(force=True)
    assert (nebula.width, nebula.height) == engine.FRAME_SIZE and not nebula.errors(), nebula.errors()
    final_top = scene.op('out_image')
    final_top.cook(force=True)
    assert (final_top.width, final_top.height) == engine.FRAME_SIZE
    assert not shader.errors(), shader.errors()
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
    folder = HERE.parent / '.venus-build' / 'wheel-revision'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'Interactive-stage.toe'
    from prepare_install import dat
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', LABEL_ATLAS],
                   cwd=folder, check=True)
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
