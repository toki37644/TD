"""Record the released interaction route with a cursor and Chinese captions."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
import shutil
import subprocess
from tempfile import TemporaryDirectory
from time import monotonic
from traceback import format_exc
import wave


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
BUILD = HERE.parent / '.venus-build' / 'full-demo'
FPS = 60
BACK = (.092, .926)
REST = (.48, .67)


@dataclass(frozen=True)
class Cue:
    seconds: float
    title: str
    description: str
    point: tuple | None = None
    travel: float = .60
    body: int | None = None
    action: str = ''
    at: float = 0.
    wheel: int = 0
    check: tuple = ()


def tour(body, name, sound, picture, destination, back):
    return (
        Cue(2.15, f'悬停{name}', '停稳后居中放大，显示英文名', body=body, check=('hover', body)),
        Cue(2.10, f'点击{name}', f'粒子聚散进入近景，切换至 {sound}', REST, 0., action='enter', check=('detail', body)),
        Cue(3.45, f'{name}近景', picture, destination, 2.6),
        Cue(2.15, '返回总览', '点击左上角箭头' if back == 'arrow' else '按 Esc 返回，切回总览音乐',
            BACK if back == 'arrow' else destination, action=back, at=.65, check=('overview',)),
    )


CUES = (
    Cue(3.25, '深空回声', 'TouchDesigner 完整交互演示'),
    Cue(2.55, '总览 · 向左探索', '指针靠近左边缘，镜头向左平移', (.036,.65), check=('pan', 0, -1)),
    Cue(2.85, '总览 · 向右探索', '移到右边缘，镜头平滑换向', (.965,.65), check=('pan', 0, 1)),
    Cue(2.85, '总览 · 向上探索', '靠近上边缘，镜头向上平移', (.49,.963), check=('pan', 1, 1)),
    Cue(2.85, '总览 · 向下探索', '靠近下边缘，镜头向下平移', (.49,.037), check=('pan', 1, -1)),
    Cue(1.30, '回到星图中央', '太阳、水星、金星、地球、火星沿横轴排列', REST),
    Cue(2.80, '悬停太阳', '约 1 秒滑向中央，球体放大约 14%', body=0, check=('hover', 0)),
    Cue(2.60, '移开指针', '镜头平滑复位，英文名散开', REST, check=('released',)),
    Cue(2.45, '悬停金星', '英文名浮现，点击前可停在总览', body=2, check=('hover', 2)),
    Cue(2.10, '点击金星', '粒子聚散、双语名称 · Petrichor', REST, 0., action='enter', check=('detail', 2)),
    Cue(2.65, '水平移动指针', '无需按键，球体随指针左右转动', (.81,.50), 1.95, check=('yaw',)),
    Cue(2.55, '垂直移动指针', '上下移动，查看球体不同角度', (.81,.82), 1.95, check=('pitch',)),
    Cue(4.15, '滚轮向上 · 放大', '连滚几格，查看球面上的流动色带', (.61,.57), wheel=9, check=('zoom-in',)),
    Cue(3.65, '滚轮向下 · 缩回', '回到按总览比例确定的近景大小', (.61,.57), wheel=-10, check=('zoom-out',)),
    Cue(2.55, '星尘跟随指针', '移动鼠标，星尘留下轨迹', (.28,.40), 1.8),
    Cue(2.25, '点击拨开星尘', '点击触发扩散，专属音乐持续驱动粒子', (.39,.49), action='burst', at=.35, check=('burst',)),
    Cue(2.20, '箭头返回总览', '点击左上角，切回总览音乐', BACK, action='arrow', at=.65, check=('overview',)),
    *tour(0, '太阳', 'Aphelion', '放射日冕与橙红云流', (.80,.70), 'arrow'),
    *tour(1, '水星', 'Machina', '冷蓝窄尾流与细密星尘', (.26,.72), 'escape'),
    *tour(3, '地球', 'Childhood', '青蓝双层云带从球体后方流过', (.76,.69), 'arrow'),
    *tour(4, '火星', 'Resonance', '红色星尘沿两道云流分叉', (.25,.36), 'escape'),
    Cue(2.50, '回到太阳系总览', '深空回声', REST, check=('overview',)),
)


class DemoRoute:
    def __init__(self, runtime, start):
        self.runtime = runtime
        self.start = start
        self.state = runtime.CameraState(start - 1./FPS)
        self.cue = 0
        self.frame = 0
        self.cue_start = 0
        self.position = REST
        self.origin = self.position
        self.initial_view = (0., 0.)
        self.clicked_at = -FPS
        self.wheeled_at = -FPS
        self.wheel_direction = 0

    @property
    def done(self):
        return self.cue == len(CUES)

    def render_state(self, scroll, escape):
        cue = CUES[self.cue]
        elapsed = (self.frame - self.cue_start)/FPS
        if self.frame == self.cue_start:
            self.origin = self.position
            self.initial_view = self.state.view

        target = cue.point
        if cue.body is not None:
            target = (self.state.hover_anchor if self.state.hover == cue.body
                      else self.state.center_uv(cue.body))
        if cue.action == 'enter':
            target = self.origin
        if target is not None:
            t = min(1., elapsed / cue.travel) if cue.travel else 1.
            bend = t*t*(3.-2.*t)
            self.position = tuple(a + (b-a)*bend for a,b in zip(self.origin,target))
        self.state.advance(self.start+self.frame/FPS, self.position, target is not None)
        if cue.action and self.frame - self.cue_start == round(cue.at*FPS):
            if cue.action == 'escape':
                escape()
            else:
                self.state.click(self.position)
                self.clicked_at = self.frame
                if cue.action == 'burst':
                    assert self.state.burst is not None
        wheel_frame = self.frame - self.cue_start - round(.46*FPS)
        spacing = round(.19*FPS)
        if cue.wheel and 0 <= wheel_frame < abs(cue.wheel)*spacing and wheel_frame % spacing == 0:
            self.wheel_direction = 1 if cue.wheel > 0 else -1
            scroll(self.position, self.wheel_direction)
            self.wheeled_at = self.frame
        if self.frame - self.cue_start + 1 == round(cue.seconds*FPS):
            self.check(cue)
            self.cue += 1
            self.cue_start = self.frame + 1
        self.frame += 1
        return (*self.position, 0. if target is None else max(.02, 1.-(self.frame-self.clicked_at)/23),
                self.wheel_direction*max(0.,1.-(self.frame-self.wheeled_at)/16))

    def check(self, cue):
        if not cue.check:
            return
        kind, *args = cue.check
        state = self.state
        if kind == 'pan':
            assert args[1]*state.camera[args[0]] > .072, state.camera
        elif kind == 'hover':
            assert state.hover == args[0] and state.label_alpha > .94, (self.cue, state.hover)
            assert self.runtime.screen_distance(state.center_uv(args[0]),(.5,.5)) < .012
        elif kind == 'released':
            assert state.hover == -1 and state.label_alpha < .07
        elif kind == 'detail':
            assert state.entered and state.focus == args[0] and state.arrival == 1.
        elif kind == 'yaw':
            assert abs(state.view[0]-self.initial_view[0]) > 1.1
        elif kind == 'pitch':
            assert abs(state.view[1]-self.initial_view[1]) > .50
        elif kind == 'zoom-in':
            assert state.camera[2] > 3.8*self.runtime.DETAIL_ZOOM
        elif kind == 'zoom-out':
            assert abs(state.camera[2]-self.runtime.DETAIL_ZOOM) < .02
        elif kind == 'burst':
            assert self.clicked_at >= self.cue_start
        elif kind == 'overview':
            assert not state.entered and state.focus == -1 and state.camera[3] < .025


STARTUP = '''from pathlib import Path
from traceback import format_exc

def onStart():
    folder = Path(project.folder)
    script = folder.parent.parent / 'live-fluids' / 'record_full_demo.py'
    try:
        scope = dict(globals(), __file__=str(script), __name__='touchdesigner_full_demo')
        exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'), scope)
        scope['record_native']()
    except Exception:
        (folder/'record-error.txt').write_text(format_exc(), encoding='utf-8')
'''


def graph_inventory():
    nodes = []
    pending = [op('/project1'),op('/perform'),op('/local')]
    while pending:
        node = pending.pop(0)
        entry = {'path': node.path, 'type': str(node.type), 'inputs': [n.path for n in node.inputs if n]}
        names = ('top', 'pixeldat', 'computedat', 'panels', 'panelvalue', 'chop', 'callbacks',
                 'winop', 'file', 'target', 'valuechange', 'mousewheel', 'operand')
        for name in names:
            par = getattr(node.par, name, None)
            if par is not None:
                value = par.eval()
                if value is not None and str(value):
                    entry[name] = str(value)
        nodes.append(entry)
        pending.extend(getattr(node,'children',()))
    return nodes


def record_native():
    import numpy as np

    folder = Path(project.folder)
    (folder/'network.json').write_text(json.dumps(graph_inventory(),ensure_ascii=False,indent=2),encoding='utf-8')
    audio = np.load(folder/'audio-state.npy')
    version = datetime.now().strftime('%H%M%S')
    scene = op('/project1')
    shader = scene.op('solar_atlas')
    module = scene.op('orbit_engine').module
    native = module.atlas()
    module.testing = True
    route = DemoRoute(module,monotonic())
    native.state = route.state
    scene.op('audio_device').par.active = False
    for source in native.sources:
        if source is not None:
            source.par.play = False
    project.realTime = False
    root.time.play = True
    movie = scene.create(moviefileoutTOP,'full_demo_movie')
    movie.inputConnectors[0].connect(scene.op('out_image'))
    output = folder/f'full-demo-{version}.mov'
    movie.par.file = str(output)
    movie.par.videocodec = 'mjpa'
    movie.par.moviepixelformat = 'yuv422'
    movie.par.quality = 92
    movie.par.fps = FPS
    movie.par.uniquesuff = False
    scene.op('out_image').cook(force=True)
    movie.par.record = True
    report = folder/f'capture-{version}.txt'
    (folder/'active.txt').write_text(str(report),encoding='utf-8')
    samples = []

    def wheel(point,direction):
        module.testing = False
        try:
            try:
                native.panel.interactMouse(*point,wheel=direction)
            except Exception as error:
                if 'No active panels' not in str(error):
                    raise
                route.state.scroll(direction)
        finally:
            module.testing = True

    def escape():
        module.testing = False
        try:
            module.go_back('Escape')
        finally:
            module.testing = True

    def frame():
        try:
            if route.done:
                movie.par.record = False
                movie.cook(force=True)
                assert not movie.errors(), movie.errors()
                (folder/'full-demo.ass').write_text(captions(samples),encoding='utf-8-sig')
                (folder/'finished.txt').write_text(str(output),encoding='utf-8')
                run('project.quit(force=True)',delayFrames=5)
                return
            previous = route.cue
            if route.frame == route.cue_start:
                with report.open('a',encoding='utf-8') as trace:
                    print(f'{route.frame/FPS:05.2f}  → {CUES[previous].title}',file=trace)
            data = audio[route.frame]
            samples.append(route.render_state(wheel,escape))
            native.state.energy[:] = data[:4]
            native.rms = float(data[4])
            native.apply(force=True)
            movie.cook(force=True)
            if route.cue != previous:
                assert not shader.errors(), shader.errors()
                target = native.state.focus + 1 if native.state.entered else 0
                assert int(data[5]) == target
                with report.open('a',encoding='utf-8') as trace:
                    print(f'{route.frame/FPS:05.2f}  {CUES[previous].title}  {module.SCENES[target]}',file=trace)
            run('args[0]()',frame,delayFrames=1)
        except Exception:
            movie.par.record = False
            (folder/'record-error.txt').write_text(format_exc(),encoding='utf-8')
            run('project.quit(force=True)',delayFrames=3)

    run('args[0]()',frame,delayFrames=5)


def ass_time(frame):
    centis = round(frame * 100 / FPS)
    hour, remainder = divmod(centis,360000)
    minute, remainder = divmod(remainder,6000)
    seconds, sub = divmod(remainder,100)
    return f'{hour}:{minute:02}:{seconds:02}.{sub:02}'


def captions(samples=()):
    heading = '''[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Microsoft YaHei UI,32,&H00DDFFF2,&H00FFFFFF,&H70060403,&H90060403,-1,0,0,0,100,100,0,0,1,2.7,0,1,42,42,91,1
Style: Hint,Microsoft YaHei UI,24,&H00F1E9DE,&H00FFFFFF,&HA0060403,&H90060403,0,0,0,0,100,100,0,0,1,2.2,0,1,42,42,54,1
Style: Cursor,Microsoft YaHei UI,19,&H00EDFFC9,&H00FFFFFF,&H0019160A,&H9019160A,0,0,0,0,100,100,0,0,1,1.65,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    frame = 0
    lines = [heading]
    for cue in CUES:
        end = frame + round(cue.seconds*FPS)
        for style, words in (('Main',cue.title),('Hint',cue.description)):
            lines.append(f'Dialogue: 0,{ass_time(frame)},{ass_time(end)},{style},,0,0,0,,{words}\n')
        frame = end
    for index, (u,v,click,wheel) in enumerate(samples):
        if click == 0.:
            continue
        start,end = ass_time(index),ass_time(index+1)
        x,y = round(u*720),round((1.-v)*1280)
        dot = r'{\an5\pos(%d,%d)}●' % (x,y)
        lines.append(f'Dialogue: 1,{start},{end},Cursor,,0,0,0,,{dot}\n')
        if click > .06:
            size = round(14+39*(1.-click))
            alpha = round(255*(1.-click))
            ring = r'{\an5\pos(%d,%d)\fs%d\alpha&H%02X&}○' % (x,y,size,alpha)
            lines.append(f'Dialogue: 1,{start},{end},Cursor,,0,0,0,,{ring}\n')
        if abs(wheel) > .15:
            sign = '↑' if wheel > 0 else '↓'
            arrow = r'{\an5\pos(%d,%d)\fs24}' % (x+22,y)
            lines.append(f'Dialogue: 1,{start},{end},Cursor,,0,0,0,,{arrow}{sign}\n')
    return ''.join(lines)


def prepare_soundtrack():
    import sys
    import numpy as np

    sys.path.insert(0,str(HERE.parent))
    import orbit_runtime as runtime

    rate = 44100
    block_size = rate//FPS
    ffmpeg = next((WORKSPACE/'.tools'/'watchvideo'/'vendor'/'ffmpeg').rglob('ffmpeg.exe'),None)
    if ffmpeg is None:
        ffmpeg = shutil.which('ffmpeg')
    if ffmpeg is None:
        raise RuntimeError('FFmpeg is required to decode the six project tracks.')
    clips = sorted((WORKSPACE/'深空回声-音乐试听').glob('*.mp3'))
    assert len(clips) == len(runtime.SCENES), clips
    sources = []
    for clip in clips:
        raw = subprocess.check_output([str(ffmpeg),'-v','error','-i',str(clip),'-f','f32le',
                                      '-ac','2','-ar',str(rate),'-'])
        sources.append(np.frombuffer(raw,dtype='<f4').reshape(-1,2))

    route = DemoRoute(runtime,0.)
    state = route.state
    audio_state = []
    position = [0]*len(sources)
    gain = [0.]*len(sources)
    target = -1
    sample_offsets = np.arange(block_size)
    with wave.open(str(BUILD/'soundtrack.wav'),'wb') as audio:
        audio.setparams((2,2,rate,0,'NONE','not compressed'))
        while not route.done:
            route.render_state(lambda _,direction:state.scroll(direction),state.leave)
            scene = state.focus+1 if state.entered else 0
            if scene != target:
                target = scene
                position[target] = 0
                spectrum = runtime.Spectrum()
            mix = np.zeros((block_size,2),dtype=np.float32)
            rms = 0.
            for i, samples in enumerate(sources):
                gain[i] = runtime.approach(gain[i],.52 if i==target else 0.,state.dt,7. if i==target else 5.5)
                if i != target and gain[i] < .0007:
                    continue
                block = samples[(position[i]+sample_offsets)%len(samples)]
                position[i] += block_size
                mix += gain[i]*block
                if i == target:
                    mono = block.mean(axis=1)
                    rms = float(np.sqrt(np.mean(mono*mono)))
                    energy = spectrum.read(mono)
                    energy *= min(1.,gain[i]*2.) if i else .15
                    for band,value in enumerate(energy):
                        previous = state.energy[band]
                        state.energy[band] = runtime.approach(previous,value,state.dt,22. if value>previous else 6.)
            audio_state.append((*state.energy,rms,target))
            audio.writeframes((np.clip(mix,-1.,1.)*32767).astype('<i2').tobytes())
    np.save(BUILD/'audio-state.npy',np.asarray(audio_state,dtype=np.float32))


def stage(source_project):
    from build_interactive_revision import TD_BIN
    from prepare_install import dat

    BUILD.mkdir(parents=True,exist_ok=True)
    for name in ('record-error.txt','finished.txt'):
        (BUILD/name).unlink(missing_ok=True)
    prepare_soundtrack()
    (BUILD/'full-demo.ass').write_text(captions(),encoding='utf-8-sig')
    target = BUILD/'Full-demo-stage.toe'
    with TemporaryDirectory(dir=BUILD) as temporary:
        pack = Path(temporary)
        source = pack/target.name
        shutil.copyfile(source_project,source)
        subprocess.run([str(TD_BIN/'toeexpand.exe'),source.name],cwd=pack)
        clock = source.with_suffix('.toe.dir')/'project1'/'clock.text'
        dat(clock,STARTUP)
        params = clock.with_suffix('.parm')
        body = params.read_text(encoding='ascii')
        assert 'framestart 67108864 on' in body
        params.write_text(body.replace('framestart 67108864 on','start 67108864 on'),encoding='ascii')
        subprocess.run([str(TD_BIN/'toecollapse.exe'),source.with_suffix('.toe.toc').name],cwd=pack,check=True)
        shutil.copyfile(source,target)
    print(target)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=WORKSPACE/'深空回声-彩雾交互版.toe')
    stage(parser.parse_args().project)
