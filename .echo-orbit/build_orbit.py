"""Build the editable TouchDesigner show from the dedicated seed project."""

from pathlib import Path
from traceback import format_exc


WORK = Path(globals().get('ORBIT_HOME', project.folder)).resolve()
DEST = Path(globals().get('ORBIT_STAGE', WORK / 'SolarAtlas-review.toe'))
LOG = WORK / 'build.log'
CLIP_DIR = WORK.parent / '深空回声-音乐试听'
CLIP_NAMES = ('01-太阳系总览.mp3', '02-太阳.mp3', '03-水星.mp3',
              '04-金星.mp3', '05-地球.mp3', '06-火星.mp3')
SCENES = ('overview', 'sun', 'mercury', 'venus', 'earth', 'mars')
VECTORS = ('uCamera', 'uPointer', 'uAudio', 'uScene', 'uSun', 'uMercury', 'uVenus', 'uEarth', 'uMars')
INK = (.13, .14, .24)
BLUE = (.17, .25, .40)
RUSSET = (.38, .21, .14)
PURPLE = (.25, .15, .36)


def log(message):
    with LOG.open('a', encoding='utf-8') as file:
        file.write(str(message) + '\n')
    print(message)


def node(comp, factory, name, x, y, color):
    operator = comp.op(name)
    if operator is None:
        operator = comp.create(factory, name)
    operator.nodeX, operator.nodeY, operator.color = x, y, color
    return operator


def finish():
    try:
        comp = op('/project1')
        final = comp.op('out_image')
        final.cook(force=True)
        for name in ('solar_atlas', 'particles', 'clock', 'out_image'):
            errors = comp.op(name).errors()
            log(f'{name} errors: {errors}')
            if errors:
                raise RuntimeError(f'{name}: {errors}')
        assert (final.width, final.height) == (1200, 675)
        assert len(comp.vfs) == 6
        assert comp.op('viewport').par.top.eval() == final
        if not project.save(str(DEST)):
            raise RuntimeError('Project save returned False')
        log('SAVED ' + str(DEST))
    except Exception:
        log(format_exc())


def build():
    if Path(project.folder).resolve() != WORK or WORK.name != '.echo-orbit':
        raise RuntimeError('Use the dedicated .echo-orbit seed or staging project')
    LOG.write_text('', encoding='utf-8')
    comp = op('/project1')
    if comp is None:
        comp = op('/').create(containerCOMP, 'project1')
    panel = node(comp, containerCOMP, 'viewport', 850, 340, BLUE)
    panel.par.w, panel.par.h = 1200, 675
    panel.par.top = '/project1/out_image'
    panel.par.topfill = 'off'
    panel.viewer = panel.activeViewer = True

    clock = node(comp, executeDAT, 'clock', 465, -30, RUSSET)
    clock.par.framestart = False
    code = node(comp, textDAT, 'orbit_engine', 190, -30, RUSSET)
    code.text = (WORK / 'orbit_runtime.py').read_text(encoding='utf-8')

    raster_code = node(comp, textDAT, 'particle_callbacks', 0, 300, INK)
    raster_code.text = ('def onCook(scriptOp):\n'
                        '    pass\n')
    particles = node(comp, scriptTOP, 'particles', 215, 300, BLUE)
    particles.par.callbacks = raster_code.path

    shader_code = node(comp, textDAT, 'atlas_pixel', 220, 460, INK)
    shader_code.text = (WORK / 'solar_atlas.frag').read_text(encoding='utf-8')
    shader = node(comp, glslTOP, 'solar_atlas', 440, 340, BLUE)
    shader.par.outputresolution = 'custom'
    shader.par.resolutionw, shader.par.resolutionh = 1200, 675
    shader.par.pixeldat = shader_code.path
    shader.inputConnectors[0].connect(particles)
    shader.seq.vec.numBlocks = len(VECTORS)
    for i, name in enumerate(VECTORS):
        getattr(shader.par, f'vec{i}name').val = name
    final = node(comp, nullTOP, 'out_image', 660, 340, BLUE)
    final.inputConnectors[0].connect(shader)
    comp.par.top = final.path

    press = node(comp, panelexecuteDAT, 'left_click', -40, -30, RUSSET)
    press.par.panels = panel.path
    press.par.panelvalue = 'lselect'
    press.par.offtoon, press.par.ontooff, press.par.valuechange = True, False, False
    press.text = ('def onOffToOn(panelValue):\n'
                  '    op("/project1/orbit_engine").module.click()\n')
    key = node(comp, panelexecuteDAT, 'escape_to_overview', -40, -180, RUSSET)
    key.par.panels = panel.path
    key.par.panelvalue = 'key'
    key.par.offtoon, key.par.ontooff, key.par.valuechange = False, False, True
    key.text = ('def onValueChange(panelValue):\n'
                '    op("/project1/orbit_engine").module.go_back(panelValue.val)\n')

    mix = node(comp, mathCHOP, 'music_mix', 650, -400, PURPLE)
    mix.par.chopop = 'add'
    for i, (scene, filename) in enumerate(zip(SCENES, CLIP_NAMES)):
        internal = f'{scene}.mp3'
        if not comp.vfs.find(pattern=internal):
            comp.vfs.addFile(str(CLIP_DIR / filename), overrideName=internal)
        source = node(comp, audiofileinCHOP, 'audio_' + scene, 0, -370 - i * 115, PURPLE)
        source.par.file = f'vfs:{comp.path}:{internal}'
        source.par.playmode = 'sequential'
        source.par.repeat = 'on'
        source.par.play = (i == 0)
        gain = node(comp, mathCHOP, 'volume_' + scene, 270, -370 - i * 115, PURPLE)
        gain.inputConnectors[0].connect(source)
        gain.par.gain = 0.
        if getattr(gain.par, 'interppars', None) is not None:
            gain.par.interppars = True
        if gain not in mix.inputs:
            gain.outputConnectors[0].connect(mix)
    speakers = node(comp, audiodeviceoutCHOP, 'audio_device', 855, -400, PURPLE)
    speakers.inputConnectors[0].connect(mix)

    perform = op('/perform') or op('/').create(windowCOMP, 'perform')
    perform.par.winop = panel.path
    perform.par.title = 'Solar Atlas'
    perform.par.size = 'automatic'
    perform.par.dpiscaling = 'native'
    perform.par.closeescape = False
    if getattr(perform.par, 'borders', None) is not None:
        perform.par.borders = False
    perform.par.setperform.pulse()
    project.performOnStart = True
    project.realTime = True
    clock.text = ('def onFrameStart(frame):\n'
                  '    op("/project1/orbit_engine").module.tick()\n')
    clock.par.framestart = True
    log('Native graph configured, waiting for first frames')
    run('args[0]()', finish, delayFrames=15)


try:
    build()
except Exception:
    log(format_exc())
