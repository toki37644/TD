"""Native rendering and input-state smoke tests for the staged solar atlas."""

from pathlib import Path
from time import monotonic
from traceback import format_exc

import numpy as np


qa_dir = Path(project.folder) / 'frames'
qa_dir.mkdir(exist_ok=True)
qa_log = qa_dir / 'qa.txt'
qa_log.write_text('', encoding='utf-8')
qa_mod = op('/project1/orbit_engine').module
app = qa_mod.atlas()
final_top = op('/project1/out_image')
mix = op('/project1/music_mix')
nebula = op('/project1/nebula_footage')
first_nebula_frame = nebula.numpyArray().copy()


def check_log(line):
    with qa_log.open('a', encoding='utf-8') as file:
        print(line, file=file)
    print(line)


def check_states():
    for i in range(5):
        state = qa_mod.CameraState(0.)
        state.advance(3., (.5, .5), False)
        hover = state.center_uv(i)
        for frame in range(1, 77):
            state.advance(3. + frame / 60., hover, True)
        assert state.focus == i and not state.entered, (i, state.focus)
        assert qa_mod.screen_distance(state.center_uv(i), (.5, .5)) < .036
        state.click(hover)
        assert state.entered and state.focus == i
        for frame in range(77, 103):
            state.advance(3. + frame / 60., (.16, .28), True)
        assert state.intent > .80 and state.lock_fade > .83
        state.click(qa_mod.RETURN)
        for frame in range(103, 180):
            state.advance(3. + frame / 60., (.05, .917), True)
        assert not state.entered and state.focus == -1 and state.camera[3] < .009
    assert qa_mod.orbit_positions(0.) != qa_mod.orbit_positions(1.)
    check_log('PASS all five hover targets, camera tracking, commit, pointer, return; orbit and spin continue')


def save_frame(name):
    final_top.cook(force=True)
    assert (final_top.width, final_top.height) == (1200, 675)
    assert not final_top.errors(), final_top.errors()
    assert not op('/project1/solar_atlas').errors()
    assert not op('/project1/particles').errors()
    final_top.save(str(qa_dir / (name + '.png')))


def render_track(index, started):
    try:
        now = monotonic()
        elapsed = now - started
        route = (.77, .69) if index else (.08, .04)
        app.state.advance(now, route, index > 0)
        app.audio()
        app.apply()
        if elapsed < 1.54:
            run('args[0](args[1],args[2])', render_track, index, started, delayFrames=1)
            return
        assert app.track == index
        signal = app.sources[index].numpyArray()
        output = mix.numpyArray()
        assert signal is not None and signal.size and abs(signal).max() > .003, index
        assert output is not None and output.size and abs(output).max() > .002, index
        assert max(app.state.energy) > .014, (index, app.state.energy)
        assert not app.sources[index].errors(), app.sources[index].errors()
        assert not op('/project1/audio_device').errors(), op('/project1/audio_device').errors()
        save_frame(f'{index}_{qa_mod.SCENES[index]}')
        check_log(f'{qa_mod.SCENES[index]}  mix peak {float(abs(output).max()):.3f}  '
                  f'spectrum {np.round(app.state.energy, 3).tolist()}')
        if index + 1 < len(qa_mod.SCENES):
            begin(index + 1)
        else:
            check_motion()
            assert (nebula.width, nebula.height) == (336, 620) and not nebula.errors()
            assert np.count_nonzero(first_nebula_frame != nebula.numpyArray()) > 1000
            app.state = qa_mod.CameraState(monotonic())
            qa_mod.testing = False
            check_log('PASS all embedded sources decoded, audio output, and six native frames')
    except Exception:
        check_log(format_exc())
        qa_mod.testing = False


def check_motion():
    state = app.state
    state.energy[:] = (.52, .42, .34, .22)
    state.pointer, state.intent = (.20, .69), 1.
    state.motion = 1.
    app.apply(force=True)
    first = app.particles.render(state)
    save_frame('7_cursor_left')
    state.pointer = (.79, .67)
    app.apply(force=True)
    second = app.particles.render(state)
    save_frame('8_cursor_right')
    assert np.count_nonzero(first != second) > 5000
    state.energy[:] = (.86, .70, .58, .71)
    third = app.particles.render(state)
    assert np.count_nonzero(second != third) > 5000
    for move in range(1, 28):
        state.advance(state.last + .016, (.16 + .025 * move, .65 + .003 * move), True)
    assert len(state.cursor_trail) > 8
    assert app.particles.cursor_dust(state)[0][0].size > 190
    check_log('PASS mouse and music move particle coordinates; pointer motion leaves persistent dust')


def begin(index):
    now = monotonic()
    app.state = qa_mod.CameraState(now - 3.)
    app.state.last = now - .016
    if index:
        app.state.focus = app.state.shown = index - 1
        app.state.entered = True
    render_track(index, now)


check_states()
qa_mod.testing = True

now = monotonic()
app.state = qa_mod.CameraState(now)
assert app.state.hit(app.state.center_uv(0)) == -1
opening_brightness = []
for elapsed, stage in ((.32, 'ignition'), (1.28, 'orbit_reveal'), (2.65, 'star_chart')):
    app.state.advance(now + elapsed, (.05, .92), False)
    app.apply(force=True)
    save_frame(f'opening_{stage}')
    pixels = final_top.numpyArray()[:, :, :3]
    opening_brightness.append(np.count_nonzero(np.max(pixels, axis=2) > .11))
assert opening_brightness[0] < opening_brightness[1] < opening_brightness[2], opening_brightness
check_log(f'PASS opening light, expanding rings, and stable solar system {opening_brightness}')
begin(0)
