"""Run from the native staging project. Captures stay in the local build cache."""
from pathlib import Path
from time import monotonic

where = Path(project.folder)
source = where.parent.parent / 'check_orbit.py'
scope = dict(globals(), __file__=str(source))
exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), scope)

VENUS_FRAMES = 810
BODY_FRAMES = 272
OTHER_BODIES = (0, 1, 3, 4)
END = VENUS_FRAMES + len(OTHER_BODIES) * BODY_FRAMES


def record_other_body(module, native, step, now):
    app = native.state
    sequence, frame = divmod(step - VENUS_FRAMES, BODY_FRAMES)
    body = OTHER_BODIES[sequence]
    point = (.47, .64)
    if 34 <= frame <= 65:
        point = app.center_uv(body)
        if frame == 65:
            assert app.hover == body and app.label_alpha > .90
            app.click(point)
            assert app.entered and app.focus == body
    elif 66 <= frame < 236:
        position = min(1., (frame - 66) / 150.)
        point = (.23 + .54 * position, .33 + .36 * position)
    elif frame == 236:
        if body == 3:
            module.testing = False
            try:
                module.go_back('Escape')
            finally:
                module.testing = True
        else:
            app.click(module.RETURN)
        assert not app.entered and app.focus == -1
    app.advance(now, point, True)
    if frame == 198:
        assert app.entered and app.arrival > .99
        return f'tour-{module.SCENES[body + 1]}'


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
        release = Path((where/'build-ok.txt').read_text(encoding='utf-8').strip())
        movie.par.file = str(release.with_suffix('.mov'))
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
    if step == END:
        movie.par.record = False
        movie.cook(force=True)
        assert not movie.errors(), movie.errors()
        assert not app.entered and app.focus == -1 and native.track == 0
        with report.open('a',encoding='utf-8') as log:
            print('PASS native recording entered all five bodies and returned through the icon and Escape',file=log)
        run('project.quit(force=True)',delayFrames=5)
        return
    capture = None
    outside = (.93,.08)
    left, right = (.23,.31), (.77,.69)
    if step >= VENUS_FRAMES:
        capture = record_other_body(module, native, step, now)
    elif step < 76:
        point, inside = outside, False
    elif step < 104:
        point, inside = (.85,.74), True
    elif step <= 204:
        point, inside = app.center_uv(2), True
    elif step < 360:
        t = min(1., (step-204)/125.)
        point, inside = (.50-.27*t,.50-.19*t), True
    elif step < 456:
        point, inside = left, True
    elif step < 589:
        t = min(1., (step-456)/110.)
        point, inside = (.23+.54*t,.31+.38*t+.16*t*(1.-t)), True
    elif step < 695:
        point, inside = right, True
    elif step < 760:
        point, inside = module.RETURN, step < 723
    else:
        point, inside = (.08,.22), True
    if step in (204, 371, 695):
        app.click(point)
    if step == 204:
        assert app.entered and app.focus == 2
    elif step == 371:
        assert app.entered and app.burst is not None
    elif step == 695:
        assert not app.entered
    if step < VENUS_FRAMES:
        app.advance(now, point, inside)
    native.audio()
    if step == 170:
        assert app.hover == 2 and app.label_alpha > .9 and app.camera[2] == 1.
    elif step == 328:
        assert app.entered and app.arrival > .99 and native.track == 3
    elif step == 778:
        assert native.track == 0
    elif capture is not None:
        assert native.track == app.focus + 1
    native.apply(force=True)
    movie.cook(force=True)
    if step in (75, 170, 248, 328, 403, 561, 646, 778):
        capture = f'interaction-{step}'
    if capture is not None:
        out = op('/project1/out_image')
        out.cook(force=True)
        assert not out.errors(), out.errors()
        out.save(str(where/'frames'/f'{capture}.png'))
    state[1] += 1
    run('args[0](args[1])', record_preview, state, delayFrames=1)


run('args[0]()', record_preview, delayFrames=12)
