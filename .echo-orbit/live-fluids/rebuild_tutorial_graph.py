"""Build the diagram shown in mrxccc's Music Planet tutorial in an isolated .toe."""

from datetime import datetime
from functools import partial
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from traceback import format_exc


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
BUILD = HERE.parent / '.venus-build' / 'tutorial-graph'
TD_BIN = Path('C:/Program Files/Derivative/TouchDesigner/bin')
FRAME_SIZE = (1280, 720)

# Lookup TOP indexes the red, green, blue, and alpha curves separately.
# The color curves reconstruct the warm/cyan result shown at 00:13 and 21:04.
RAMP = (
    (0., .000, .000, .000),
    (.034, .006, .042, .077),
    (.070, .014, .19, .32),
    (.108, .028, .59, .70),
    (.145, .13, .82, .96),
    (.184, .66, .65, 1.00),
    (.223, .99, .25, .98),
    (.265, .99, .045, .91),
    (.340, .985, .096, .86),
    (.420, .985, .24, .89),
    (.520, .985, .61, .87),
    (.620, .985, .78, .76),
    (.730, .985, .79, .59),
    (.820, .985, .81, .23),
    (.930, .985, .83, .14),
    (1.00, .985, .84, .15),
)

STARTUP = '''from pathlib import Path
from traceback import format_exc

def onStart():
    folder = Path(project.folder)
    source = folder.parent.parent / 'live-fluids' / 'rebuild_tutorial_graph.py'
    try:
        scope = dict(globals(), __file__=str(source), __name__='touchdesigner_build')
        exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), scope)
        scope['install_native']()
    except Exception:
        (folder / 'build-error.txt').write_text(format_exc(), encoding='utf-8')
'''


def install_native():
    scene = op('/project1')
    clock = scene.op('clock')
    for child in scene.children:
        if child.valid and child != clock:
            child.destroy()
    for asset in list(scene.vfs):
        asset.destroy()
    namespace = dict(globals())
    helper = HERE / 'build_tutorial_venus.py'
    exec(compile(helper.read_text(encoding='utf-8'), str(helper), 'exec'), namespace)
    make = partial(namespace['make_node'], scene)
    width, height = FRAME_SIZE
    size = dict(outputresolution='custom', resolutionw=width, resolutionh=height)
    simplex = dict(seed=1, harmon=2, spread=2, amp=.5, offset=.5, mono=True)

    # 01:01–05:25. Roughen the circle's outline, then feed the animated source
    # into the same stock Feedback Edge COMP used in the video.
    circle = make(circleTOP, 'circle1', 0, 175, **size, radiusx=.2, radiusy=.2,
                  fillcolorr=.28565, fillcolorg=.17836, fillcolorb=.91, bgalpha=0)
    grain = make(noiseTOP, 'noise1', 0, 15, **size, **simplex, period=.01, gain=.19)
    seed = make(displaceTOP, 'displace1', 190, 175, circle, grain,
                displaceweight1=-.02, displaceweight2=-.02)
    noise = make(noiseTOP, 'noise2', 365, -10, seed, seed=1, period=2., harmon=0,
                 exp=1.41, amp=1.08, offset=.5, mono=True, rgb='noise', alpha='one',
                 tz=('expr', 'absTime.seconds * .5'))
    mask = make(levelTOP, 'level1', 540, -10, noise)
    base = make(compositeTOP, 'comp1', 725, 175, seed, mask, operand='outsideluminance')
    component = Path(app.samplesFolder) / 'Palette' / 'ImageFilters' / 'feedbackEdge.tox'
    package = scene.loadTox(str(component))
    edge_feedback = namespace['place'](scene.copy(package.op('feedbackEdge')), 915, 175)
    package.destroy()
    edge_feedback.inputConnectors[0].connect(base)
    edge_feedback.par.Drywet = .946
    transform = make(transformTOP, 'transform1', 1110, 175, edge_feedback)
    source = make(nullTOP, 'null1', 1285, 175, transform)

    # 05:25–09:24. The final comp3 is Maximum, with the original source as
    # a fresh input and the attenuated advected image as the other input.
    feedback = make(feedbackTOP, 'feedback1', 1480, 390, source)
    keyboard = make(keyboardinCHOP, 'keyboardin1', 1480, 580, keys='1')
    feedback.par.reset.expr = "op('keyboardin1')[0]"
    field = make(noiseTOP, 'noise3', 1690, 260, feedback, period=.35, harmon=7,
                 seed=1, spread=2, amp=.5, offset=.5, mono=True,
                 gain=('expr', "float(op('null5')[0])"))
    slope = dict(red='hluminance', green='neutral', blue='vluminance', alpha='one',
                 method='prevnext', strength=1)
    first = make(slopeTOP, 'slope1', 1690, 90, feedback, **slope, zeropoint=.3)
    second = make(slopeTOP, 'slope2', 1690, -80, feedback, **slope, zeropoint=.5)
    average = make(compositeTOP, 'comp2', 1900, 255, field, first, second, operand='average')
    moved = make(displaceTOP, 'displace2', 2100, 390, feedback, average,
                 displaceweight1=.01, displaceweight2=.01)
    attenuated = make(levelTOP, 'level2', 2290, 390, moved, opacity=.90)
    mixed = make(compositeTOP, 'comp3', 2480, 175, attenuated, source, operand='maximum')
    feedback.par.top = mixed.path

    # 09:34–15:23. Grade the Lookup, add each edge pass, then use the noise
    # branch as the second input to Outside Luminance.
    swatches = make(tableDAT, 'ramp_keys', 2305, -370)
    for position, red, green, blue in RAMP:
        swatches.appendRow([position, red, green, blue, min(1., 10. * position)])
    ramp = make(rampTOP, 'ramp1', 2480, -370, dat=swatches.path, type='horizontal',
                outputresolution='custom', resolutionw=1024, resolutionh=1)
    look = make(lookupTOP, 'lookup1', 2690, 175, mixed, ramp, channel='independent')
    hsv = make(hsvadjustTOP, 'hsvadj1', 2870, 175, look)
    grade = make(levelTOP, 'level3', 3050, 175, hsv, gamma1=.7)
    color = make(nullTOP, 'null2', 3230, 175, grade)
    edge_one = make(edgeTOP, 'edge1', 3420, 410, color, select='luminance',
                    edgecolorr=.15, edgecolorg=.82, edgecolorb=1.)
    level_four = make(levelTOP, 'level4', 3600, 410, edge_one, opacity=.70)
    comp_four = make(compositeTOP, 'comp4', 3790, 175, level_four, color, operand='add')
    edge_two = make(edgeTOP, 'edge2', 3980, 410, comp_four, select='luminance',
                    edgecolorr=0., edgecolorg=.73, edgecolorb=1.)
    level_five = make(levelTOP, 'level5', 4160, 410, edge_two, opacity=.43)
    comp_five = make(compositeTOP, 'comp5', 4350, 175, level_five, comp_four, operand='add')
    outside_noise = make(noiseTOP, 'noise4', 4530, -70, comp_five, **simplex, period=1., gain=.7)
    level_six = make(levelTOP, 'level6', 4720, -70, outside_noise, opacity=.10)
    comp_six = make(compositeTOP, 'comp6', 4910, 175, comp_five, level_six,
                    operand='outsideluminance')
    finish = make(levelTOP, 'level7', 5100, 175, comp_six, contrast=1.11)
    presentation = make(transformTOP, 'transform2', 5280, 175, finish, compover=True,
                        bgcolora=1)
    out = make(nullTOP, 'null3', 5470, 175, presentation)

    # The selected track belongs to 深空回声. The CHOP routing follows 17:06–18:52.
    scene.vfs.addFile(str(WORKSPACE / '深空回声-音乐试听' / '04-金星.mp3'), overrideName='venus.mp3')
    audio = make(audiofileinCHOP, 'audiofilein1', 365, -565,
                 file='vfs:/project1:venus.mp3', playmode='sequential', repeat=True, mono=True)
    make(audiodeviceoutCHOP, 'audiodevout1', 540, -790, audio)
    analysis = make(analyzeCHOP, 'analyze1', 565, -565, audio, function='rmspower')
    first_range = make(mathCHOP, 'math1', 775, -480, analysis, torange1=.15, torange2=.5)
    second_range = make(mathCHOP, 'math2', 775, -650, analysis, torange1=.5, torange2=2.)
    make(nullCHOP, 'null4', 975, -480, first_range)
    make(nullCHOP, 'null5', 975, -650, second_range)

    notes = make(textDAT, 'tutorial_notes', 4910, -405)
    notes.text = '''mrxccc · TouchDesigner 音乐星球节奏互动
https://www.bilibili.com/video/BV1pkRiYpEZh/

01:01–03:59 | Circle、Displace1、Noise2、Comp1 Outside Luminance
04:38–09:24 | Feedback Edge、两级位移、Level2 衰减、Comp3 Maximum 回灌
09:34–15:23 | RGBA Lookup、双 Edge Add、Comp6 Outside Luminance、Null3
17:06–18:52 | Audio File In、Analyze、两路 Math、Null5 提供 Noise3 谐波增益

选用《深空回声》金星音轨 Petrichor by Scott Buckley（CC BY 4.0）。
Ramp 键值按片头和片尾的画面复调。边缘叠加强度按公开成品的亮度调整。
Null4 保留在音频分支，视频中未能确认其最终绑定目标。
按 1 重置 Feedback1。F1 打开演出预览。'''

    out.viewer = True
    scene.par.top = out.path
    panel = make(containerCOMP, 'viewport', 5470, -95, w=width, h=height, top=out.path, topfill='off')
    op('/perform').par.winop = panel.path
    op('/perform').par.title = '音乐星球 · 教程节点复刻'
    op('/perform').par.closeescape = True
    project.performOnStart = False
    root.time.play = True
    clock.par.start = clock.par.framestart = clock.par.frameend = False
    clock.text = ''
    for pane in ui.panes:
        if pane.type == PaneType.NETWORKEDITOR:
            pane.owner = scene
            pane.home()

    out.cook(force=True)
    assert (out.width, out.height) == FRAME_SIZE
    assert feedback.par.top.eval() == mixed and list(mixed.inputs) == [attenuated, source]
    assert list(average.inputs) == [field, first, second]
    assert list(comp_six.inputs) == [comp_five, level_six]
    issues = [(node.name, node.errors()) for node in scene.children if node.errors()]
    assert not issues, issues
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    release = BUILD / f'Graph-{stamp}.toe'
    assert project.save(str(release))
    (BUILD / 'latest.txt').write_text(str(release), encoding='utf-8')
    run('args[0](args[1])', record, release, delayFrames=4)


def record(release, step=0):
    try:
        scene = op('/project1')
        audio = scene.op('audiofilein1')
        out = scene.op('null3')
        if step == 0:
            project.realTime = False
            scene.op('audiodevout1').par.active = False
            movie = scene.create(moviefileoutTOP, 'qa_movie')
            movie.inputConnectors[0].connect(out)
            movie.par.file = str(release.with_suffix('.mov'))
            movie.par.videocodec = 'mjpa'
            movie.par.moviepixelformat = 'yuv422'
            movie.par.quality = 92
            movie.par.audiochop = audio.path
            movie.par.audiocodec = 'pcm16'
            movie.par.fps = 60
            movie.par.uniquesuff = False
        movie = scene.op('qa_movie')
        if step == 120:
            audio.par.cuepulse.pulse()
            movie.par.record = True
        if step < 120:
            out.cook(force=True)
        elif step < 720:
            movie.cook(force=True)
        if step in (135, 215, 330, 455, 575, 710):
            folder = BUILD / release.stem
            folder.mkdir(exist_ok=True)
            for name in ('null1', 'comp3', 'lookup1', 'comp5', 'null3'):
                scene.op(name).save(str(folder / f'{step}-{name}.png'))
            if step == 215:
                for name in ('noise2', 'comp1', 'displace2', 'level2'):
                    scene.op(name).save(str(folder / f'{step}-{name}.png'))
            with (folder / 'signal.txt').open('a', encoding='utf-8') as log:
                print(step, float(scene.op('analyze1')[0]), scene.op('noise3').par.gain.eval(), file=log)
        if step == 720:
            movie.par.record = False
            movie.cook(force=True)
            assert not movie.errors(), movie.errors()
            assert release.with_suffix('.mov').stat().st_size > 1000000
            (BUILD / 'recorded.txt').write_text(str(release), encoding='utf-8')
            run('project.quit(force=True)', delayFrames=5)
            return
        run('args[0](args[1],args[2])', record, release, step + 1, delayFrames=1)
    except Exception:
        (BUILD / 'capture-error.txt').write_text(format_exc(), encoding='utf-8')


def stage():
    from prepare_install import dat

    BUILD.mkdir(parents=True, exist_ok=True)
    name = 'Tutorial-stage.toe'
    with TemporaryDirectory(dir=BUILD) as temp:
        pack = Path(temp)
        seed = pack / name
        shutil.copyfile(WORKSPACE / '深空回声-彩雾交互版.toe', seed)
        subprocess.run([str(TD_BIN / 'toeexpand.exe'), name], cwd=pack)
        dat(seed.with_suffix('.toe.dir') / 'project1' / 'clock.text', STARTUP)
        params = seed.with_suffix('.toe.dir') / 'project1' / 'clock.parm'
        body = params.read_text(encoding='ascii')
        if 'start 67108864 on' not in {line.rstrip() for line in body.splitlines()}:
            body = body.replace('framestart 67108864 on', 'start 67108864 on')
            params.write_text(body, encoding='ascii')
        subprocess.run([str(TD_BIN / 'toecollapse.exe'), seed.with_suffix('.toe.toc').name],
                       cwd=pack, check=True)
        shutil.copyfile(seed, BUILD / name)
    print(BUILD / name)


if __name__ == '__main__':
    stage()
