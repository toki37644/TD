"""Run from the native staging project. Captures stay in the local build cache."""
from pathlib import Path
from time import monotonic

where = Path(project.folder)
source = where.parent.parent / 'check_orbit.py'
scope = dict(globals(), __file__=str(source))
exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), scope)


def record_preview(state=None):
    module = op('/project1/orbit_engine').module
    native = module.atlas()
    report = where / 'frames' / 'qa.txt'
    if state is None:
        notes = report.read_text(encoding='utf-8')
        if 'PASS all embedded sources decoded' not in notes:
            if 'Traceback' not in notes:
                run('args[0]()', record_preview, delayFrames=12)
            return
        module.testing = True
        native.state = module.CameraState(monotonic() - 2.90)
        native.state.advance(monotonic(), (.93,.08), False)
        native.apply(force=True)
        project.realTime = False
        panel = op('/project1')
        panel.op('audio_device').par.active = False
        movie = panel.create(moviefileoutTOP,'review_movie')
        movie.inputConnectors[0].connect(panel.op('out_image'))
        movie.par.file = str(where/'interaction-native.mov')
        movie.par.videocodec = 'mjpa'
        movie.par.moviepixelformat = 'yuv422'
        movie.par.quality = 92
        movie.par.audiochop = panel.op('music_mix').path
        movie.par.audiocodec = 'pcm16'
        movie.par.fps = 60
        movie.par.uniquesuff = False
        movie.par.record = True
        state = [native.state.start + 2.9, 0, movie]
    start, step, movie = state
    now = start + step/60.
    app = native.state
    outside = (.93,.08)
    left, right = (.22,.63), (.79,.65)
    if step < 104:
        point, inside = outside, False
    elif step < 204:
        point, inside = app.center_uv(2), True
    elif step < 360:
        t = min(1., (step-204)/125.)
        point, inside = (.50-.28*t,.51+.12*t), True
    elif step < 456:
        point, inside = left, True
    elif step < 589:
        t = min(1., (step-456)/110.)
        point, inside = (.22+.57*t,.63+.16*t*(1.-t)+.02*t), True
    elif step < 695:
        point, inside = right, True
    else:
        point, inside = module.RETURN, step < 723
    if step in (204, 371, 695):
        app.click(point)
    app.advance(now, point, inside)
    native.audio()
    native.apply(force=True)
    movie.cook(force=True)
    if step in (75, 170, 248, 328, 403, 561, 646, 778):
        out = op('/project1/out_image')
        out.cook(force=True)
        assert not out.errors(), out.errors()
        out.save(str(where/'frames'/f'interaction-{step}.png'))
    if step == 810:
        movie.par.record = False
        movie.cook(force=True)
        assert not movie.errors(), movie.errors()
        assert not app.entered and app.focus == -1
        with report.open('a',encoding='utf-8') as log:
            print('PASS routed preview and captured stereo interaction movie',file=log)
        run('project.quit(force=True)',delayFrames=5)
        return
    state[1] += 1
    run('args[0](args[1])', record_preview, state, delayFrames=1)


run('args[0]()', record_preview, delayFrames=12)
