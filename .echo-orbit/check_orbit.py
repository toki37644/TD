"""Native rendering and input-state smoke tests for the staged solar atlas."""

from pathlib import Path
from math import tau
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
nebula = op('/project1/nebula_field')
material = op('/project1/closeup_feedback')


def check_log(line):
    with qa_log.open('a', encoding='utf-8') as file:
        print(line, file=file)
    print(line)


def check_states():
    for time in (0., 3., 17., 140.):
        bodies = qa_mod.orbit_positions(time)
        assert all(body[1] == 0. for body in bodies)
        assert all(right[0] > left[0] for left, right in zip(bodies, bodies[1:]))
    for point, axis, direction in (((.02,.38), 0, -1), ((.98,.36), 0, 1),
                                   ((.50,.02), 1, -1), ((.50,.98), 1, 1)):
        state = qa_mod.CameraState(0.)
        state.advance(3., (.5,.5), False)
        for frame in range(1, 77):
            state.advance(3. + frame / 60., point, True)
        assert direction * state.camera[axis] > .09, (point, state.camera)
        assert state.camera[2:] == (1., 0.)
    check_log('PASS portrait overview pans in four directions and retains the left-to-right axis')
    state = qa_mod.CameraState(0.)
    state.advance(3., (.5,.5), False)
    for frame in range(1, 14):
        state.advance(3. + frame/60., (.02+.073*frame,.50), True)
        assert state.hover == -1, (frame, state.hover)
    state = qa_mod.CameraState(0.)
    state.advance(3., (.5,.5), False)
    anchor = state.center_uv(0)
    for frame in range(1, 33):
        state.advance(3. + frame/60., anchor, True)
    assert state.hover == 0 and state.camera_velocity[0] < -.04
    assert .035 < qa_mod.screen_distance(state.center_uv(0), (.5,.5)) < .10
    midpoint = ((anchor[0]+state.center_uv(0)[0])*.5,.50)
    for frame in range(33, 41):
        state.advance(3. + frame/60., midpoint, True)
        assert state.hover == 0
    edge = (.98,.25)
    for frame in range(41, 49):
        state.advance(3. + frame/60., edge, True)
    assert state.hover == -1 and state.camera_velocity[0] < .02
    for frame in range(49, 155):
        state.advance(3. + frame/60., edge, True)
        assert state.hover == -1
    assert state.camera[0] > .10
    check_log('PASS fast sweep, follow corridor, and mid-glide handoff to edge panning')
    for i in range(5):
        state = qa_mod.CameraState(0.)
        state.advance(3., (.5, .5), False)
        anchor = state.center_uv(i)
        for frame in range(1, 77):
            state.advance(3. + frame / 60., anchor, True)
        assert state.hover == i and state.focus == -1 and not state.entered, (i, state.hover)
        assert state.camera[2:] == (1., 0.) and state.label_id == i and state.label_alpha > .94
        assert qa_mod.screen_distance(state.center_uv(i), (.5, .5)) < .004
        assert state.explore == (0., 0.) and state.hit(anchor) == i
        assert state.hit_radius(i) > 1.13 * state.bodies[i][2]
        for frame in range(77, 145):
            state.advance(3. + frame / 60., (.50,.65), True)
        assert state.hover == -1 and state.label_alpha < .09
        assert qa_mod.screen_distance(state.camera[:2], (0., 0.)) < .004
        anchor = state.center_uv(i)
        for frame in range(145, 200):
            state.advance(3. + frame / 60., anchor, True)
        state.click(anchor if i % 2 == 0 else state.center_uv(i))
        assert state.entered and state.focus == i
        assert state.uniforms()[-1][2] == 1.
        for frame in range(200, 226):
            state.advance(3. + frame / 60., (.16, .28), True)
        assert state.intent > .80 and state.lock_fade > .83
        assert state.view[0] < -1.9 and state.view[1] < -.48
        for frame in range(226, 256):
            state.advance(3. + frame / 60., (.84, .74), True)
        assert state.view[0] > 1.9 and state.view[1] > .52
        assert abs(state.camera[2] - qa_mod.DETAIL_ZOOM) < .035
        view = state.view
        state.advance(state.last + .016, qa_mod.RETURN, True)
        assert state.view == view
        state.click(qa_mod.RETURN)
        assert state.uniforms()[-1][2] == 0.
        for frame in range(257, 334):
            state.advance(3. + frame / 60., (.05, .917), True)
        assert not state.entered and state.focus == -1 and state.camera[3] < .009
    assert qa_mod.orbit_positions(0.) != qa_mod.orbit_positions(1.)
    check_log('PASS all five stationary hover anchors, centering, 14% enlargement, return and both rotation axes')


def save_frame(name):
    final_top.cook(force=True)
    assert (final_top.width, final_top.height) == qa_mod.FRAME_SIZE
    assert not final_top.errors(), final_top.errors()
    assert not op('/project1/solar_atlas').errors()
    assert not op('/project1/particles').errors()
    final_top.save(str(qa_dir / (name + '.png')))


def check_scroll():
    for i, radius in enumerate(qa_mod.RADII):
        state = qa_mod.CameraState(0.)
        state.advance(3., (.5,.5), False)
        state.scroll(5)
        assert state.detail_zoom == qa_mod.DETAIL_ZOOM
        state.click(state.center_uv(i))
        assert state.focus == i
        for _ in range(110):
            state.advance(state.last + 1./60, (.5,.5), True)
        baseline = state.camera[2]
        state.scroll(4, inside=False)
        assert state.detail_zoom == qa_mod.DETAIL_ZOOM
        state.scroll(1)
        assert state.camera[2] == baseline
        state.advance(state.last + 1./60, (.5,.5), True)
        assert baseline < state.camera[2] < state.detail_zoom
        state.scroll(400)
        assert abs(state.detail_zoom * radius - qa_mod.INSPECT_RADIUS) < 1e-6
        for _ in range(66):
            state.advance(state.last + 1./60, (.5,.5), True)
        assert abs(state.camera[2] - state.detail_zoom) < .003
        enlarged = state.camera[2]
        state.scroll(-400)
        state.advance(state.last + 1./60, (.5,.5), True)
        assert qa_mod.DETAIL_ZOOM < state.camera[2] < enlarged
        for _ in range(66):
            state.advance(state.last + 1./60, (.5,.5), True)
        assert abs(state.camera[2] - baseline) < .003
        state.scroll(2)
        state.click(qa_mod.RETURN)
        assert state.detail_zoom == qa_mod.DETAIL_ZOOM and not state.entered
    panel = op('/project1/viewport')
    wheel = op('/project1/wheel_zoom')
    assert panel.par.mousewheel.eval() and wheel.par.valuechange.eval()
    assert wheel.par.panelvalue.eval() == 'wheel' and wheel.par.panels.eval() == panel
    check_log('PASS native wheel binding and all five zoom ranges, smoothing, bounds, and return reset')
    original = app.state
    probe = qa_mod.CameraState(monotonic()-3.)
    probe.advance(monotonic(), (.5,.5), True)
    probe.click(probe.center_uv(2))
    assert probe.entered and probe.focus == 2
    app.state = probe
    try:
        panel.interactMouse(.5,.5)
        panel.interactMouse(.5,.5,wheel=1.)
        assert probe.detail_zoom > qa_mod.DETAIL_ZOOM, (panel.panel.inside.val, wheel.errors())
        panel.interactMouse(.5,.5,wheel=-1.)
        assert abs(probe.detail_zoom - qa_mod.DETAIL_ZOOM) < 1e-6, wheel.errors()
    finally:
        app.state = original
    check_log('PASS viewport-generated wheel events traverse the release callback in both directions')


def check_globe_mask(index, nominal):
    # Render the real coverage calculation alone for measurement. The changing
    # feedback, halo, and background otherwise make edge detection ambiguous.
    pixel = op('/project1/atlas_pixel')
    original = pixel.text
    source = original.split('void main() {', 1)[0]
    marker = '    vec3 globe = locked*silhouette'
    assert marker in source
    source = source.replace(marker, '    return vec3(silhouette);\n' + marker, 1)
    source += '''
void main() {
    vec2 world = (vUV.st-.5)*ASPECT/uCamera.z+uCamera.xy;
    int id = int(floor(uScene.x+.5));
    vec4 bodies[5] = vec4[5](uSun,uMercury,uVenus,uEarth,uMars);
    vec3 mask = bodyLayer(vec3(0.),world,vec2(0.),bodies[id],id,1.,true,uPointer.x);
    fragColor = TDOutputSwizzle(vec4(mask,1.));
}
'''
    try:
        pixel.text = source
        final_top.cook(force=True)
        assert not op('/project1/solar_atlas').errors()
        rows, columns = np.nonzero(final_top.numpyArray()[:,:,0] > .5)
    finally:
        pixel.text = original
        final_top.cook(force=True)
    measured = (int(columns.max()-columns.min()+1), int(rows.max()-rows.min()+1))
    assert all(abs(diameter-2.*nominal) <= 2. for diameter in measured), (index, measured, nominal)
    assert abs(measured[0]-measured[1]) <= 1, (index, measured)
    check_log(f'PASS {qa_mod.SCENES[index]} circular diameter {measured[0]} x {measured[1]} px, expected {2.*nominal:.1f}')


def check_globe(index):
    app.apply(force=True)
    final_top.cook(force=True)
    first = final_top.numpyArray().copy()
    view = app.state.view
    width, height = qa_mod.FRAME_SIZE
    u, v = app.state.center_uv(index - 1)
    x, y = round(u*width), round(v*height)
    nominal = qa_mod.RADII[index - 1] * qa_mod.DETAIL_ZOOM * height
    depth = round(nominal*.53)
    roi = np.s_[y-depth:y+depth, x-depth:x+depth, :3]

    def surface(yaw, pitch):
        app.state.view = (view[0] + yaw, view[1] + pitch)
        app.apply(force=True)
        final_top.cook(force=True)
        return final_top.numpyArray()[roi].copy()

    baseline = first[roi]
    yaw_delta = np.mean(np.abs(baseline - surface(1.18, 0.)))
    pitch_delta = np.mean(np.abs(baseline - surface(0., -.86)))
    assert min(yaw_delta, pitch_delta) > .006, (index, yaw_delta, pitch_delta)
    if index == 3:
        previous = baseline
        for step in range(1, 9):
            turned = surface(step*tau/8.,0.)
            assert .006 < np.mean(np.abs(previous-turned)) < .52, step
            previous = turned
        assert np.mean(np.abs(baseline-turned)) < .008
        check_log('PASS Venus closes a full revolution with coherent surface shading')
    app.state.view = view
    app.apply(force=True)
    # TOP arrays are ordered from the bottom row, while title positions start at the top.
    title = first[-155:, 230:490, :3][::-1].max(axis=2)
    assert np.count_nonzero(title[62:107] > .60) > 100, index
    assert np.count_nonzero(title[114:143] > .60) > 24, index
    check_log(f'PASS {qa_mod.SCENES[index]} rotates on both axes ({yaw_delta:.3f}, {pitch_delta:.3f}), both title lines')
    check_globe_mask(index, nominal)


def check_nebula(index):
    nebula.cook(force=True)
    assert (nebula.width, nebula.height) == qa_mod.FRAME_SIZE and not nebula.errors(), nebula.errors()
    image = nebula.numpyArray().copy()
    assert np.count_nonzero(image[:,:,:3].max(axis=2) > .055) > 4000, index
    if index == 4:
        nebula.save(str(qa_dir / 'earth_nebula_only.png'))
        state_time = app.state.time
        app.state.time += 2.0
        app.apply()
        nebula.cook(force=True)
        delta = np.mean(np.abs(image[:,:,:3] - nebula.numpyArray()[:,:,:3]))
        assert delta > .0015, delta
        app.state.time = state_time
        app.apply()
        check_log(f'PASS Earth portrait cloud layer contains live moving structure ({delta:.3f})')


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
        signal = app.pcm.source if app.pcm is not None else app.sources[index].numpyArray()
        output = mix.numpyArray()
        assert signal is not None and signal.size and abs(signal).max() > .003, index
        assert output is not None and output.size and abs(output).max() > .002, index
        assert max(app.state.energy) > .014, (index, app.state.energy)
        source = app.audio_chop if app.pcm is not None else app.sources[index]
        assert not source.errors(), source.errors()
        assert not op('/project1/audio_device').errors(), op('/project1/audio_device').errors()
        gain = material.op('noise3').par.gain.eval()
        assert app.rms > .001 and abs(gain - (.5 + 1.5 * app.rms)) < 1e-5
        save_frame(f'{index}_{qa_mod.SCENES[index]}')
        if index:
            check_globe(index)
            check_nebula(index)
        check_log(f'{qa_mod.SCENES[index]}  mix peak {float(abs(output).max()):.3f}  '
                  f'feedback gain {gain:.3f}  spectrum {np.round(app.state.energy, 3).tolist()}')
        if index + 1 < len(qa_mod.SCENES):
            begin(index + 1)
        else:
            check_motion()
            assert op('/project1/nebula_footage') is None
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
    first = app.particles.render(state).copy()
    save_frame('7_cursor_left')
    state.pointer = (.79, .67)
    app.apply(force=True)
    second = app.particles.render(state).copy()
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
try:
    check_scroll()
except Exception:
    check_log(format_exc())
    raise
assert material.op('comp1').par.operand.eval() == 'outsideluminance'
assert material.op('comp3').par.operand.eval() == 'maximum'
assert material.op('feedback1').par.top.eval() == material.op('comp3')
assert material.op('fold_field') is None
check_log('PASS native tutorial seed and maximum feedback loop')
assert (op('/project1/planet_names').width, op('/project1/planet_names').height) == (256, 720)
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
check_log(f'PASS opening light, axis reveal, and stable solar system {opening_brightness}')
begin(0)
