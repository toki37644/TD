"""Run in a dedicated new TouchDesigner project using the Python Textport."""
from pathlib import Path
import traceback

WORK = Path.home() / 'Documents' / 'ChatGPT' / '空' / '.echo-work'
DEST = Path(globals().get('ECHO_OUTPUT', WORK.parent / '深空回声-演出版.toe'))
LOG = WORK / 'build.log'


def log(message):
    with LOG.open('a', encoding='utf-8') as file:
        file.write(str(message) + '\n')
    print(message)


def make(comp, kind, name, x, y, color):
    node = comp.op(name)
    if node is None:
        node = comp.create(kind, name)
    node.nodeX, node.nodeY, node.color = x, y, color
    return node


def build():
    LOG.write_text('', encoding='utf-8')
    source = next((WORK / f for f in ('deep_echo.frag','scene.frag') if (WORK/f).exists()),None)
    if source is None or not (WORK/'hud.png').exists():
        raise FileNotFoundError('Need the final shader and .echo-work/hud.png before running.')
    comp = op('/project1')
    if comp is None:
        comp = op('/').create(containerCOMP, 'project1')
    log('Build into '+comp.path+' in '+project.name)
    # This flag marks only operator networks created by this builder.
    had_previous_build = comp.fetch('echo_builder_started', False)
    if not had_previous_build:
        if comp.children:
            log('Starter children preserved: '+', '.join(node.name for node in comp.children))
        comp.store('echo_builder_started', True)
    jade = (.12,.33,.34)
    ink = (.13,.22,.32)
    brass = (.36,.25,.12)
    purple = (.29,.20,.31)
    panel = make(comp, containerCOMP, 'viewport', 790, 280, jade)
    panel.par.w, panel.par.h = 1200,675
    panel.par.top = '/project1/final_image'
    panel.par.topfill = 'off'
    panel.viewer = True
    panel.activeViewer = True

    shadertext = make(comp, textDAT, 'nebula_pixel', 0, 280, ink)
    shadertext.text = source.read_text(encoding='utf-8-sig')
    shader = make(comp, glslTOP, 'starfield', 210, 280, jade)
    shader.par.pixeldat = shadertext.path
    shader.par.outputresolution = 'custom'
    shader.par.resolutionw, shader.par.resolutionh = 1200,675
    shader.seq.vec.numBlocks = 5
    for i, name in enumerate(('uClockPointer','uPulse','uFlags','uRoute','uMusic')):
        getattr(shader.par,'vec%dname'%i).val = name

    asset = make(comp, moviefileinTOP, 'hud_loading_source', 0, 110, ink)
    asset.par.file = str(WORK/'hud.png')
    hud = make(comp, nullTOP, 'hud_embedded', 210, 110, ink)
    hud.lock = False
    hud.inputConnectors[0].connect(asset)
    merged = make(comp, overTOP, 'instrument_overlay', 410, 280, jade)
    merged.inputConnectors[0].connect(hud)
    merged.inputConnectors[1].connect(shader)
    final = make(comp, nullTOP, 'final_image', 605, 280, jade)
    final.inputConnectors[0].connect(merged)
    if getattr(comp.par, 'top', None) is not None:
        comp.par.top = 'final_image'

    engine = make(comp, textDAT, 'runtime', 210,-125, brass)
    engine.text = (WORK/'runtime_td.py').read_text(encoding='utf-8-sig')
    key = make(comp, keyboardinCHOP, 'reset_key', 0,-265, brass)
    key.par.keys = 'r'
    key.par.active = 'on'
    key.par.panels = panel.path
    keys = make(comp, panelexecuteDAT, 'button_edges', 0,-125, brass)
    keys.par.panels = panel.path
    keys.par.panelvalue = 'lselect'
    keys.par.offtoon, keys.par.ontooff, keys.par.valuechange = True,True,False
    keys.text = ("def onOffToOn(panelValue):\n    op('/project1/runtime').module.button_event(True)\n"
                 "def onOnToOff(panelValue):\n    op('/project1/runtime').module.button_event(False)\n")
    tick = make(comp, executeDAT, 'frame_clock', 415,-125, brass)
    tick.par.framestart = True
    tick.text = ("def onFrameStart(frame):\n    op('/project1/runtime').module.frame()\n")

    mix = make(comp, mathCHOP, 'motif_mix', 610,-410,purple)
    mix.par.chopop = 'add'
    for i,(name,freq) in enumerate((('C4',261.626),('E4',329.628),('G4',391.995))):
        y = -415 - i*125
        osc = make(comp,audiooscillatorCHOP,'tone_'+name,0,y,purple)
        osc.par.frequency, osc.par.wavetype, osc.par.rate = freq,'sin',44100
        gain = make(comp,mathCHOP,'envelope_'+name,240,y,purple)
        gain.inputConnectors[0].connect(osc)
        gain.par.gain.expr = "op('starfield').par.vec4value%s * 0.19" % 'xyz'[i]
        if getattr(gain.par,'interppars',None) is not None:
            gain.par.interppars = True
        if gain not in mix.inputs:
            gain.outputConnectors[0].connect(mix)
    speakers = make(comp,audiodeviceoutCHOP,'speaker_output',800,-410,purple)
    speakers.inputConnectors[0].connect(mix)

    play = op('/perform') or op('/').create(windowCOMP,'perform')
    play.par.winop = panel.path
    play.par.title = '深空回声  /  行星观测'
    play.par.size = 'automatic'
    play.par.dpiscaling = 'native'
    play.par.setperform.pulse()
    project.performOnStart = True
    project.realTime = True
    engine.module.reset()
    log('Built all native operators. Finalize HUD when decoded.')
    # Delayed Python callable is supported by all recent 2023+ TouchDesigner builds.
    run("args[0](0)", finish, delayFrames=8)


def finish(attempt=0):
    try:
        comp = op('/project1')
        asset = comp.op('hud_loading_source')
        hud = comp.op('hud_embedded')
        asset.cook(force=True)
        hud.cook(force=True)
        data = hud.numpyArray()
        if data is None or data.shape[:2] != (675,1200) or data[:,:,3].max() < .45:
            if attempt < 30:
                run("args[0](args[1])",finish,attempt+1,delayFrames=6)
                return
            raise ValueError('HUD decode failed. Shape '+str(None if data is None else data.shape))
        hud.lock = True
        asset.destroy()
        final = comp.op('final_image')
        final.cook(force=True)
        shader = comp.op('starfield')
        log('Shader: '+str(shader.errors())+' / '+str(shader.warnings()))
        if shader.errors():
            raise RuntimeError('Shader compilation failed: '+str(shader.errors()))
        log('Final: '+str((final.width,final.height))+'; locked HUD '+str(hud.lock))
        if (final.width,final.height) != (1200,675):
            raise RuntimeError('Final output dimensions mismatch')
        comp.op('runtime').module.reset()
        if not project.save(str(DEST)):
            raise RuntimeError('Project save returned False')
        log('SAVED '+str(DEST))
    except Exception:
        log(traceback.format_exc())


try:
    build()
except Exception:
    log(traceback.format_exc())
