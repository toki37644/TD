"""Repack the TouchDesigner-native staging project after updating its DATs."""
from pathlib import Path
import shutil
import subprocess
import sys


work = Path(__file__).resolve().parent
debug = '--trace' in sys.argv
verify = '--verify' in sys.argv
base = 'SolarAtlas-review.toe' if debug else 'SolarAtlas-caption-saved.toe'
name = 'SolarAtlas-release.toe'
if debug:
    name = 'SolarAtlas-caption-stage.toe'
elif verify:
    name = 'SolarAtlas-particles-qa.toe'
tree = work / (name + '.dir')
shutil.copytree(work / (base + '.dir'), tree, dirs_exist_ok=True)
shutil.copyfile(work / (base + '.toc'), work / (name + '.toc'))
network = tree / 'project1'


def replace_text(node, text):
    data = text.encode('utf-8')
    target = network / (node + '.text')
    original = target.read_bytes()
    assert int.from_bytes(original[23:27], 'big') == len(original) - 27, node
    target.write_bytes(original[:23] + len(data).to_bytes(4, 'big') + data)


def parameter(node, line):
    target = network / (node + '.parm')
    body = target.read_bytes()
    end = body.rfind(b'?')
    target.write_bytes(body[:end] + line.encode() + b'\n' + body[end:])


replace_text('atlas_pixel', (work / 'solar_atlas.frag').read_text(encoding='utf-8'))
replace_text('orbit_engine', (work / 'orbit_runtime.py').read_text(encoding='utf-8'))
replace_text('particle_callbacks', 'def onCook(scriptOp):\n    pass\n')

if debug:
    parameter('clock', 'start 67108864 on')
    replace_text('clock', '''from pathlib import Path
from time import perf_counter
from traceback import format_exc

where = Path(project.folder)
log = where / 'engine-trace.txt'
count = 0

def onStart():
    log.write_text('START\\n', encoding='utf-8')
    parent = op('/project1')
    keyboard = parent.create(keyboardinDAT, 'return_key')
    keyboard.nodeX, keyboard.nodeY = -160, -270
    callback = parent.create(textDAT, 'return_key_callbacks')
    callback.nodeX, callback.nodeY = 15, -270
    callback.text = """def onKey(dat, key, *payload):
    engine = op('/project1/orbit_engine').module
    if isinstance(key, str):
        if payload[-2]:
            engine.go_back(key)
    elif getattr(key, 'state', False):
        engine.go_back(getattr(key, 'webCode', '') or getattr(key, 'key', ''))

def onShortcut(dat, shortcutName, time):
    op('/project1/orbit_engine').module.go_back(shortcutName)
"""
    keyboard.par.callbacks = callback.path
    keyboard.par.shortcuts = 'esc escape'
    keyboard.par.perform = True
    keyboard.par.maxlines = 4
    video = parent.create(moviefileinTOP, 'nebula_footage')
    video.nodeX, video.nodeY = 215, 100
    video.color = (.18, .25, .37)
    parent.vfs.addFile(str(where/'stock'/'nebula-motion.mp4'), overrideName='nebula-motion.mp4')
    video.par.file = 'vfs:/project1:nebula-motion.mp4'
    video.par.playmode = 'sequential'
    video.par.play = True
    if 'cycle' in video.par.textendright.menuNames:
        video.par.textendright = 'cycle'
    shader = parent.op('solar_atlas')
    shader.inputConnectors[1].connect(video)
    names = parent.create(moviefileinTOP, 'planet_names')
    names.nodeX, names.nodeY = 215, -85
    names.color = (.18, .25, .37)
    parent.vfs.addFile(str(where/'stock'/'body-names.png'), overrideName='body-names.png')
    names.par.file = 'vfs:/project1:body-names.png'
    shader.inputConnectors[2].connect(names)
    chart = parent.create(moviefileinTOP, 'flat_chart')
    chart.nodeX, chart.nodeY = 215, -174
    chart.color = (.18, .25, .37)
    parent.vfs.addFile(str(where/'stock'/'star-chart.jpg'), overrideName='star-chart.jpg')
    chart.par.file = 'vfs:/project1:star-chart.jpg'
    shader.inputConnectors[3].connect(chart)
    shader.seq.vec.numBlocks = 11
    shader.par.vec9name = 'uLabel'
    shader.par.vec10name = 'uTransition'
    run('args[0]()', native_tests, delayFrames=45)

def native_tests():
    video = op('/project1/nebula_footage')
    if video.errors() or (video.width,video.height)!=(336,620):
        with log.open('a',encoding='utf-8') as file:
            print('VIDEO ERROR', video.errors(), video.width, video.height, file=file)
        return
    with log.open('a',encoding='utf-8') as file:
        print('VIDEO EMBEDDED',video.width,video.height,len(op('/project1').vfs),file=file)
    names = op('/project1/planet_names')
    if names.errors() or (names.width,names.height)!=(128,280):
        raise RuntimeError('Planet name atlas did not load')
    chart = op('/project1/flat_chart')
    if chart.errors() or (chart.width,chart.height)!=(960,1280):
        raise RuntimeError('The original chart did not load')
    project.save(str(where/'SolarAtlas-caption-saved.toe'))
    source = where / 'check_orbit.py'
    exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), globals())

def onFrameStart(frame):
    global count
    count += 1
    try:
        start = perf_counter()
        op('/project1/orbit_engine').module.tick()
        if count in (1, 2, 3, 10, 30, 45, 100, 200, 400, 600):
            with log.open('a', encoding='utf-8') as file:
                print(count, round((perf_counter()-start)*1000, 1), file=file)
    except Exception:
        with log.open('a', encoding='utf-8') as file:
            print(format_exc(), file=file)
        me.par.framestart = False
''')
elif verify:
    replace_text('clock', '''from pathlib import Path

def onStart():
    run('args[0]()', verify_render, delayFrames=45)

def verify_render():
    source = Path(project.folder) / 'check_orbit.py'
    exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), globals())

def onFrameStart(frame):
    op('/project1/orbit_engine').module.tick()
''')
else:
    # Release starts directly in the artwork and contains no staging callbacks.
    replace_text('clock', 'def onFrameStart(frame):\n    op("/project1/orbit_engine").module.tick()\n')
    clock_parameters = network / 'clock.parm'
    spec = clock_parameters.read_bytes()
    clock_parameters.write_bytes(b'\n'.join(line for line in spec.split(b'\n') if not line.rstrip().startswith(b'start ')))

collapse = r'C:\Program Files\Derivative\TouchDesigner\bin\toecollapse.exe'
subprocess.run([collapse, name + '.toc'], cwd=work, check=True)
assert (work / name).is_file()
print(work / name)
