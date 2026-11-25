"""Migrate a saved atlas to in-memory audio, then exercise the released network."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from traceback import format_exc
import shutil
import subprocess
import sys


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
BUILD = HERE.parent / '.venus-build' / 'stability'

STARTUP = '''from pathlib import Path
from traceback import format_exc

def onStart():
    folder = Path(project.folder)
    source = folder.parent.parent / 'live-fluids' / 'stabilize_project.py'
    try:
        scope = dict(globals(), __file__=str(source), __name__='touchdesigner_stability')
        exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),scope)
        scope[ENTRY]()
    except Exception:
        (folder/'stability-error.txt').write_text(format_exc(),encoding='utf-8')
        run('project.quit(force=True)',delayFrames=4)
'''

PCM_CALLBACK = '''def onCook(scriptOp):
    runtime = op('/project1/orbit_engine').module
    player = runtime.atlas().pcm
    scriptOp.clear()
    scriptOp.copyNumpyArray(player.block, baseName='stereo')
    scriptOp.rate = runtime.AUDIO_RATE
    scriptOp.start = player.start
    scriptOp.isTimeSlice = True
'''


def install():
    scene = op('/project1')
    clock = scene.op('clock')
    runtime_dat = scene.op('orbit_engine')
    original_names = ('overview', 'sun', 'mercury', 'venus', 'earth', 'mars')
    for name in original_names:
        for prefix in ('volume_', 'audio_'):
            node = scene.op(prefix + name)
            if node is not None:
                node.destroy()
    for name in ('audio_pcm', 'audio_pcm_callbacks'):
        previous = scene.op(name)
        if previous is not None:
            previous.destroy()
    runtime_dat.text = (HERE.parent/'orbit_runtime.py').read_text(encoding='utf-8')
    module = runtime_dat.module
    for asset in list(scene.vfs):
        if asset.name == module.PCM_ASSET:
            asset.destroy()
    scene.vfs.addFile(str(BUILD/module.PCM_ASSET), overrideName=module.PCM_ASSET)

    pcm = scene.create(scriptCHOP,'audio_pcm')
    callbacks = pcm.par.callbacks.eval()
    if callbacks is None:
        callbacks = scene.create(textDAT,'audio_pcm_callbacks')
    callbacks.text = PCM_CALLBACK
    callbacks.nodeX, callbacks.nodeY = -54, -395
    pcm.par.callbacks = callbacks.path
    pcm.par.timeslice = True
    pcm.nodeX, pcm.nodeY = 145, -396
    mix = scene.op('music_mix')
    mix.inputConnectors[0].connect(pcm)
    pcm.cook(force=True)
    assert not pcm.errors(), pcm.errors()
    assert pcm.numChans == 2 and pcm.rate == 44100 and pcm.isTimeSlice, (
        pcm.numChans,pcm.rate,pcm.isTimeSlice,pcm.numSamples,pcm.par.callbacks.eval())
    asset = scene.vfs[module.PCM_ASSET]
    assert asset.size > 1000000

    # Cook the secondary graph once before the runtime can freeze it in overview.
    feedback = scene.op('closeup_feedback')
    feedback.allowCooking = True
    feedback.op('out1').cook(force=True)
    feedback.allowCooking = False
    scene.op('out_image').cook(force=True)
    assert not scene.op('solar_atlas').errors(), scene.op('solar_atlas').errors()
    clock.text = '''def onStart():
    root.time.play = True

def onFrameStart(frame):
    op('/project1/orbit_engine').module.tick()
'''
    clock.par.framestart = True
    root.time.play = True
    output = BUILD/f'Stable-release-{datetime.now():%H%M%S}.toe'
    assert project.save(str(output))
    (BUILD/'release.txt').write_text(str(output),encoding='utf-8')
    run('project.quit(force=True)',delayFrames=4)


def verify():
    """Exercise a freshly reopened .toe, including native recording and device output."""
    import numpy as np

    scene = op('/project1')
    module = scene.op('orbit_engine').module
    module.testing = True
    native = module.atlas()
    assert native.pcm is not None and len(native.pcm.clips) == 6
    assert list(scene.op('music_mix').inputs) == [scene.op('audio_pcm')]
    start = monotonic()
    state = native.state = module.CameraState(start - 1./60.)
    out = scene.op('out_image')
    feedback = scene.op('closeup_feedback')
    report = BUILD/'verification.txt'
    report.write_text('',encoding='utf-8')
    device = scene.op('audio_device')
    root.time.play = True
    project.realTime = False
    device.par.active = False
    movie = scene.create(moviefileoutTOP,'stability_capture')
    movie.inputConnectors[0].connect(out)
    movie.par.file = str(BUILD/'stability-test.mov')
    movie.par.videocodec = 'mjpa'
    movie.par.moviepixelformat = 'yuv422'
    movie.par.audiochop = scene.op('music_mix').path
    movie.par.audiocodec = 'pcm16'
    movie.par.fps = 60
    movie.par.uniquesuff = False
    movie.par.record = True

    # 24-second repro boundary, followed by the other four planets and re-entry.
    entries = {1410:2, 1680:0, 1940:1, 2200:3, 2460:4, 2720:2}
    leaves = {1600, 1860, 2120, 2380, 2640, 2900}
    seen = set()
    wrapped = set()
    live_changes = [(1., 3), (2.6, -1), (3.5, 1), (5.1, -1),
                    (6., 0), (7.6, -1), (8.5, 4), (10.1, -1)]
    previous_end = None
    live_started = None

    def log(line):
        with report.open('a',encoding='utf-8') as handle:
            print(line,file=handle)

    def frame(index=0):
        nonlocal previous_end, live_started
        try:
            if index == 3000:
                movie.par.record = False
                movie.cook(force=True)
                assert not movie.errors(), movie.errors()
                assert seen == set(range(6)) and wrapped == set(range(1,6))
                assert not feedback.allowCooking
                log('PASS recorded 50 seconds including the old 24-second boundary and all six audio tracks')
                project.realTime = True
                device.par.active = True
                live_started = monotonic()
            now = start + index/60.
            if index >= 3000:
                elapsed = monotonic() - live_started
                now = start + 50. + elapsed
                if live_changes and elapsed >= live_changes[0][0]:
                    _, target = live_changes.pop(0)
                    state.click(module.RETURN if target < 0 else state.center_uv(target))
                    assert state.focus == target
            point = (.49,.65)
            if index in entries:
                state.click(state.center_uv(entries[index]))
                assert state.entered and state.focus == entries[index]
                log(f'{index}: entered {module.SCENES[state.focus+1]}')
            elif index in leaves:
                if index in (1600, 2120, 2640):
                    state.click(module.RETURN)
                else:
                    module.testing = False
                    try:
                        module.go_back('Escape')
                    finally:
                        module.testing = True
                assert not state.entered and state.detail_zoom == module.DETAIL_ZOOM
            if state.entered:
                point = (.53 + .24*np.sin(index*.04), .53 + .22*np.cos(index*.035))
                if index < 3000:
                    elapsed_frames = index - max(t for t in entries if t <= index)
                    if elapsed_frames == 100:
                        state.scroll(4)
                    if elapsed_frames == 125:
                        track = state.focus + 1
                        native.pcm.cursor[track] = len(native.pcm.clips[track])-10
                        wrapped.add(track)
            state.advance(now,point,True)
            native.audio()
            native.apply()
            if index < 3000:
                movie.cook(force=True)
            else:
                out.cook(force=True)
            if index % 60 == 0 or index in entries or index in leaves:
                assert not native.audio_chop.errors(), native.audio_chop.errors()
                assert not out.errors(), out.errors()
                assert (out.width,out.height) == module.FRAME_SIZE
                assert bool(feedback.allowCooking) == (state.shown >= 0)
                signal = scene.op('music_mix').numpyArray()
                assert signal.shape[0] == 2 and np.isfinite(signal).all()
                if index > 0 and abs(signal).max() > .002:
                    seen.add(native.track)
                if index % 120 == 0:
                    log(f'{index}: {module.SCENES[native.track]} samples={signal.shape[1]} feedback={feedback.allowCooking}')
            pcm = native.pcm
            if previous_end is not None and 0 < pcm.end-previous_end <= 8820:
                assert pcm.start == previous_end, (index, pcm.start, previous_end)
            previous_end = pcm.end
            if index >= 3000 and monotonic() - live_started >= 12.:
                assert not live_changes
                assert not device.errors(), device.errors()
                log(f'PASS 12 seconds in real time with Audio Device Out active; {index+1} total frame callbacks')
                (BUILD/'verified.txt').write_text('PASS\n',encoding='utf-8')
                run('project.quit(force=True)',delayFrames=4)
            else:
                run('args[0](args[1])',frame,index+1,delayFrames=1)
        except Exception:
            log(format_exc())
            if movie.par.record.eval():
                movie.par.record = False
            run('project.quit(force=True)',delayFrames=4)

    run('args[0]()',frame,delayFrames=10)


def prepare_audio():
    import numpy as np

    sys.path.insert(0,str(HERE.parent))
    from orbit_runtime import AUDIO_RATE, PCM_ASSET, SCENES

    ffmpeg = next((WORKSPACE/'.tools/watchvideo/vendor/ffmpeg').rglob('ffmpeg.exe'), None)
    if ffmpeg is None:
        ffmpeg = shutil.which('ffmpeg')
    if ffmpeg is None:
        raise RuntimeError('FFmpeg is required to prepare the embedded PCM tracks.')
    clips = sorted((WORKSPACE/'深空回声-音乐试听').glob('*.mp3'))
    assert len(clips) == len(SCENES)
    tracks = {}
    for name, clip in zip(SCENES, clips):
        raw = subprocess.check_output([str(ffmpeg),'-v','error','-i',str(clip),'-f','s16le',
                                       '-ac','2','-ar',str(AUDIO_RATE),'-'])
        tracks[name] = np.frombuffer(raw,dtype='<i2').reshape(-1,2)
        assert len(tracks[name]) > AUDIO_RATE and np.any(tracks[name])
    np.savez_compressed(BUILD/PCM_ASSET, **tracks)


def stage(source, entry):
    from build_interactive_revision import TD_BIN
    from prepare_install import dat

    BUILD.mkdir(parents=True,exist_ok=True)
    target = BUILD/f'{entry}-stage.toe'
    with TemporaryDirectory(dir=BUILD) as folder:
        work = Path(folder)
        packed = work/target.name
        shutil.copyfile(source,packed)
        subprocess.run([str(TD_BIN/'toeexpand.exe'),packed.name],cwd=work)
        clock = packed.with_suffix('.toe.dir')/'project1'/'clock.text'
        dat(clock,STARTUP.replace('ENTRY',repr(entry)))
        params = clock.with_suffix('.parm')
        body = params.read_text(encoding='ascii')
        params.write_text(body.replace('framestart 67108864 on','start 67108864 on'),encoding='ascii')
        subprocess.run([str(TD_BIN/'toecollapse.exe'),packed.with_suffix('.toe.toc').name],cwd=work,check=True)
        shutil.copyfile(packed,target)
    print(target)


if __name__ == '__main__':
    BUILD.mkdir(parents=True,exist_ok=True)
    if '--verify' in sys.argv:
        release = Path((BUILD/'release.txt').read_text(encoding='utf-8').strip())
        stage(release,'verify')
    else:
        source = WORKSPACE/'深空回声-彩雾交互版.toe'
        backup = BUILD/'workspace-before.toe'
        shutil.copyfile(source,backup)
        prepare_audio()
        stage(backup,'install')
