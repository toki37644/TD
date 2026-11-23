"""Continuous orbits, camera state, audio analysis and shared particle simulation."""

from collections import deque
from math import cos, exp, hypot, sin
from time import monotonic

import numpy as np


ROOT = '/project1/'
ASPECT = 16 / 9
SIZE = (960, 540)
ARRIVAL_SECONDS = 1.52
SCENES = ('overview', 'sun', 'mercury', 'venus', 'earth', 'mars')
RADII = (.080, .024, .031, .034, .028)
DISTANCES = (0, .154, .318, .388, .653)
PHASES = (0, 3.12, 3.04, .88, 1.47)
SPEEDS = (0, .047, .033, .024, .016)
SPINS = (.045, .071, -.049, .088, .072)
TILT = .032
RETURN = (.053, .918)


def approach(current, target, dt, rate):
    return target + (current - target) * exp(-rate * dt)


def screen_distance(a, b):
    return hypot((a[0] - b[0]) * ASPECT, a[1] - b[1])


def smooth_between(first, last, value):
    t = np.clip((value - first) / (last - first), 0., 1.)
    return t * t * (3. - 2. * t)


def orbit_positions(time):
    sun = (-.009, -.158)
    rows = []
    for i, radius in enumerate(RADII):
        phase = PHASES[i] + time * SPEEDS[i]
        x = DISTANCES[i] * cos(phase)
        lift = sin(phase)
        y = DISTANCES[i] * lift * (.68 + .22 * lift)
        rows.append((x * cos(TILT) - y * sin(TILT) + sun[0],
                     x * sin(TILT) + y * cos(TILT) + sun[1],
                     radius, time * SPINS[i] + i * .83))
    return rows


class CameraState:
    def __init__(self, now):
        self.start = self.last = now
        self.time = self.dt = self.flow_time = 0.0
        self.bodies = orbit_positions(0.)
        self.camera = (0., 0., 1., 0.)
        self.pointer = (.5, .5)
        self.focus_anchor = self.pointer
        self.intent = .0
        self.motion = .0
        self.catch = self.timelock = 0.0
        self.hover_time = self.away_time = 0.0
        self.hover = self.focus = self.shown = -1
        self.entered = False
        self.back_glow = 0.0
        self.lock_fade = 0.0
        self.label_id = -1
        self.label_alpha = 0.
        self.label_side = 1.
        self.label_leaving = False
        self.arrival_start = None
        self.arrival = 1.
        self.arrival_origin = (0., 0., 0.)
        self.energy = np.zeros(4, dtype=np.float32)
        self.cursor_trail = deque(maxlen=27)

    def center_uv(self, body_id):
        x, y, _, _ = self.bodies[body_id]
        cx, cy, zoom, _ = self.camera
        return ((x - cx) * zoom / ASPECT + .5, (y - cy) * zoom + .5)

    def hit(self, position):
        if self.time < .67:
            return -1
        closest = -1
        distance = 1.0
        for i, body in enumerate(self.bodies):
            detail = self.camera[3] > .40
            if detail and i != self.shown:
                continue
            center = self.center_uv(i)
            radius = body[2] * self.camera[2]
            gap = screen_distance(position, center)
            if gap < radius + .019 and gap < distance:
                closest, distance = i, gap
        return closest

    def leave(self):
        self.entered = False
        self.arrival = 1.
        self.arrival_start = None
        self.focus = self.hover = -1
        self.hover_time = self.away_time = 0.0
        self.timelock = self.last + .60
        self.cursor_trail.clear()

    def click(self, position, inside=True):
        if not inside:
            return
        if self.entered:
            if screen_distance(position, RETURN) < .051:
                self.leave()
            return
        target = self.focus if self.focus >= 0 else self.hit(position)
        if target >= 0:
            u, v = self.center_uv(target)
            radius = self.bodies[target][2] * self.camera[2]
            self.arrival_origin = ((u - .5) * ASPECT, v - .5, radius)
            self.arrival_start = self.last
            self.arrival = 0.
            self.focus = self.shown = target
            self.entered = True
            self.hover = -1

    def advance(self, now, position, inside):
        self.dt = max(0., min(.080, now - self.last))
        self.last = now
        self.time = now - self.start
        self.bodies = orbit_positions(self.time)
        self.flow_time += self.dt * (.88 + .66 * self.energy[1])
        dt = self.dt
        if self.arrival_start is not None:
            self.arrival = min(1., (now - self.arrival_start) / ARRIVAL_SECONDS)
            if self.arrival >= 1.:
                self.arrival_start = None
        if not self.entered and self.focus < 0 and now >= self.timelock:
            hover = self.hit(position) if inside else -1
            self.hover_time = self.hover_time + dt if hover == self.hover else 0.0
            self.hover = hover
            if hover >= 0 and self.hover_time >= .22:
                self.focus = self.shown = hover
                self.focus_anchor = position
                self.catch = now + 1.05
                self.away_time = 0.0
        if not self.entered and self.focus >= 0 and now > self.catch:
            close_to_anchor = screen_distance(position, self.focus_anchor) < .075
            close_to_subject = screen_distance(position, self.center_uv(self.focus)) < .292
            self.away_time = 0.0 if inside and (close_to_anchor or close_to_subject) else self.away_time + dt
            if self.away_time > .22:
                self.leave()

        if self.focus >= 0:
            x, y, radius, _ = self.bodies[self.focus]
            detail = (x, y, .268 / radius, 1.)
        else:
            detail = (0., 0., 1., 0.)
        self.camera = tuple(approach(before, after, dt, rate) for before, after, rate in
                            zip(self.camera, detail, (6.4, 6.4, 4.9, 4.3)))
        if self.focus < 0 and self.camera[3] < .008:
            self.shown = -1
        speed = min(1., screen_distance(self.pointer, position) * 16.) if inside else 0.
        self.motion = approach(self.motion, speed, dt, 18. if speed > self.motion else 3.8)
        if inside:
            self.pointer = tuple(approach(before, after, dt, 12.) for before, after in zip(self.pointer, position))
        in_return = self.entered and inside and screen_distance(position, RETURN) < .051
        self.intent = approach(self.intent, float(self.entered and inside and not in_return), dt, 7.)
        self.back_glow = approach(self.back_glow, float(in_return), dt, 12.)
        self.lock_fade = approach(self.lock_fade, float(self.entered), dt, 6.7)
        if self.entered and inside and not in_return and speed > .13:
            point = ((self.pointer[0] - .5) * ASPECT, self.pointer[1] - .5)
            self.cursor_trail.append((*point, now))
        while self.cursor_trail and now - self.cursor_trail[0][2] > 1.12:
            self.cursor_trail.popleft()
        self.update_label(inside)

    def update_label(self, inside):
        target = self.hover if inside and not self.entered else -1
        if target != self.label_id and self.label_alpha < .022:
            self.label_id = target
            if target >= 0:
                self.label_side = -1. if self.bodies[target][0] > .055 else 1.
        visible = target >= 0 and target == self.label_id
        self.label_leaving = not visible
        self.label_alpha = approach(self.label_alpha, float(visible), self.dt, 12. if visible else 6.1)

    def uniforms(self):
        return (self.camera, (self.time, *self.pointer, self.intent * (.26 + .74 * self.motion)), tuple(self.energy),
                (self.shown, self.lock_fade, self.hover if not self.entered else -1, self.back_glow),
                *self.bodies, (self.label_id, self.label_alpha, self.label_side, float(self.label_leaving)),
                (self.arrival, *self.arrival_origin))


class Spectrum:
    def __init__(self):
        self.samples = np.zeros(2048, dtype=np.float32)
        self.window = np.hanning(len(self.samples))
        self.previous = np.zeros(1025)
        hertz = np.fft.rfftfreq(len(self.samples), 1 / 44100)
        self.bands = ((hertz >= 28) & (hertz < 160),
                      (hertz >= 160) & (hertz < 1700),
                      (hertz >= 1700) & (hertz < 7200))

    def read(self, buffer):
        count = min(buffer.size, self.samples.size)
        if count == 0:
            return np.zeros(4)
        self.samples[:-count] = self.samples[count:]
        self.samples[-count:] = buffer[-count:]
        magnitude = np.abs(np.fft.rfft(self.samples * self.window)) / 512.
        raw = np.array([np.linalg.norm(magnitude[band]) for band in self.bands])
        flux = np.linalg.norm(np.maximum(magnitude - self.previous, 0.))
        self.previous = magnitude
        return 1. - np.exp(-np.r_[raw * [12., 10., 28.], flux * 20.])


class ParticleField:
    def __init__(self):
        rng = np.random.default_rng(14571)
        self.ring = rng.random((6, 17500), dtype=np.float32)
        self.stream = rng.random((6, 16400), dtype=np.float32)
        self.scatter = rng.normal(0, 1, 16400).astype(np.float32)
        self.sky = rng.random((4, 1300), dtype=np.float32)
        count = 21600
        self.random = rng.random((7, count))
        self.lane = rng.normal(0, 1, count)
        self.spark = .08 + .44 * self.random[4] ** 4.7
        dots = rng.random((6, 23000), dtype=np.float32)
        height = 2 * dots[0] - 1
        arc = 2 * np.pi * dots[1]
        cross_section = np.sqrt(1 - height ** 2)
        radius = .69 + .30 * dots[2] ** .49
        self.skin = (radius * cross_section * np.cos(arc), radius * height,
                     radius * cross_section * np.sin(arc))
        self.powder = dots[3:]
        self.trail_noise = rng.normal(0, 1, (2, 24)).astype(np.float32)
        self.trail_tone = rng.random(24, dtype=np.float32)
        self.spray = rng.random((5, 1500), dtype=np.float32)

    def overview(self, state):
        sun_x, sun_y, _, _ = state.bodies[0]
        cx, cy, zoom, detail = state.camera
        fade = (1. - detail) ** 1.45
        polar, rim, grain, sparkle, hue, drift = self.ring
        angle = polar * 2 * np.pi + state.flow_time * (.067 + .034 * drift)
        lift = np.sin(angle)
        radius = .204 + .062 * (rim - .5) + .010 * np.sin(3 * angle + grain * 4)
        lx = radius * np.cos(angle)
        ly = radius * lift * .96 - .074 * lx
        y_gap = 1. - np.exp(-((ly + .072 * lx) / .026) ** 2)
        arc = np.exp(-((rim - .5) / .31) ** 2)
        brightness = (.30 + .75 * sparkle ** 2) * arc * y_gap
        brightness *= (.73 + .40 * (lift > 0)) * (1. + .48 * state.energy[0])
        layers = [(sun_x + lx, sun_y + ly, fade * brightness, .825 + .175 * hue)]

        seed, spread, line, spark, color, tempo = self.stream
        distance = np.clip((seed - .5) * 2., -.99, .99)
        swirl = 2 * np.pi * line + state.flow_time * (.17 + tempo * .09)
        px = distance * .91 + .023 * np.sin(swirl)
        ridge = -.124 * px + .018 * np.sin(px * 9.1 - .16 * state.flow_time)
        thickness = .010 + .028 * abs(distance) + .012 * state.energy[0]
        py = ridge + self.scatter * thickness * (.48 + .85 * spread)
        embers = np.exp(-((abs(distance) - .29) / .35) ** 2)
        clouds = np.exp(-((abs(distance) - .75) / .20) ** 2)
        bright = (.10 + .62 * spark ** 3) * (.88 * embers + .42 * clouds)
        bright *= .64 + .36 * np.sin(swirl + px * 11) ** 2
        layers.append((sun_x + px, sun_y + py, fade * bright, color * .92))

        x, y, intensity, hue = self.sky
        shimmer = .72 + .28 * np.sin(181 * intensity + .47 * state.time)
        layers.append(((x - .5) * (ASPECT + .26), (y - .5) * 1.26,
                       (.031 + .20 * intensity ** 5) * shimmer * fade, hue))
        return [((x - cx) * zoom, (y - cy) * zoom, a, h) for x, y, a, h in layers]

    def closeup(self, state):
        r, azimuth, speed, drift, _, choice, height = self.random
        i = state.shown
        bass, mid, high, event = state.energy
        lean = (.50, .61, .51, .51, .56)[i]
        thickness = (.19, .15, .27, .22, .18)[i]
        curl = (3.58, 4.4, 3.05, 3.42, 4.1)[i]
        direction = (1., -1., 1., -1., 1.)[i]
        phase = (r + state.flow_time * (.078 + .10 * speed)) % 1.
        lane = np.floor(azimuth * 4.) * np.pi * .5
        wave = phase * curl + .18 * state.flow_time * direction
        phase_noise = .26 * self.lane + .21 * np.sin(phase * 10. + lane + state.flow_time)
        theta = lane + direction * (wave + phase_noise)
        radius = .12 + phase * (.94 + .15 * drift + .21 * bass)
        radius += .047 * np.sin(wave * 2.6) + .07 * self.lane * drift
        strip = radius * np.cos(theta)
        plume = radius * np.sin(theta) * thickness
        plume += .037 * self.lane * (.48 + phase) + .027 * np.sin(strip * 14. + height * 5.)
        x = strip * cos(lean) - plume * sin(lean) + .08
        y = strip * sin(lean) + plume * cos(lean) - .02
        tip = lane + direction * (curl + .18 * state.flow_time + .26 * self.lane)
        dx = .08 + np.cos(tip) * cos(lean) - np.sin(tip) * thickness * sin(lean)
        dy = -.02 + np.cos(tip) * sin(lean) + np.sin(tip) * thickness * cos(lean)
        mx, my = (state.pointer[0] - .5) * ASPECT, state.pointer[1] - .5
        local = np.exp(-((x - mx) ** 2 + (y - my) ** 2) / .21)
        drag = state.intent * (.33 + .67 * state.motion)
        pull = drag * local * (phase ** 1.45) * (.32 + .64 * choice)
        x += (mx - dx) * pull
        y += (my - dy) * pull
        life = np.sin(np.pi * phase) ** .64
        a = self.spark * life * state.camera[3] ** 1.26
        a *= (.82 + .77 * bass + (1.05 * event + .80 * high) * (choice > .65))
        a *= .50 + .50 * np.sin(theta * 1.7 + height * 2.1) ** 2
        return x, y, a, height

    def arrival_dust(self, state):
        if not state.entered or state.arrival >= 1. or state.shown < 0:
            return []
        progress = state.arrival
        progress_eased = smooth_between(.0, 1., progress)
        cx, cy, radius = state.arrival_origin
        target = state.center_uv(state.shown)
        destination_x, destination_y = (target[0] - .5) * ASPECT, target[1] - .5
        center_x = cx + (destination_x - cx) * progress_eased
        center_y = cy + (destination_y - cy) * progress_eased
        spread = sin(np.pi * progress) ** 1.14
        body_radius = radius + (state.bodies[state.shown][2] * state.camera[2] - radius) * progress_eased
        x, y, z = self.skin
        strength, tint, noise = self.powder
        spin = spread * (.63 + .58 * noise) + state.flow_time * .23
        expand = body_radius * (1. + (.59 + .61 * noise) * spread)
        xx = (x * np.cos(spin) - y * np.sin(spin)) * expand + center_x
        yy = (x * np.sin(spin) + y * np.cos(spin)) * expand + center_y
        yy += spread * (.053 * z + .038 * np.sin(6. * x + 5. * y))
        opacity = spread * (.12 + .88 * strength ** 4) * (.65 + .35 * (z > 0))
        channels = np.where(tint < .24, 0, np.where(tint < .91, 1, 2))
        return [(xx, yy, opacity, channels)]

    def spray_layers(self, state):
        """A small subset leaves the edge at transients, following curved paths."""
        start, seed, life, width, hue = self.spray
        bass, mid, high, attack = state.energy
        age = (life + state.flow_time * (.18 + .16 * seed)) % 1.
        fan = np.floor(start * 17) / 17 * 2 * np.pi + .21 * (hue - .5)
        strength = .32 + 1.1 * attack + .38 * high
        align = .19 + .16 * (state.shown % 3)
        cx, cy = (state.pointer[0] - .5) * ASPECT, state.pointer[1] - .5
        local = np.exp(-((.35 * np.cos(fan) - cx) ** 2 + (.35 * np.sin(fan) - cy) ** 2) / .16)
        attract = .52 * state.motion * state.intent * local
        result = []
        channels = np.where(hue > .85, 2, np.where(hue > .38, 1, 0))
        for delay, gain in ((0., 1.), (.017, .52), (.036, .24), (.061, .11)):
            z = np.maximum(0., age - delay)
            gravity = (align + .24 * seed) * z * (1 + .66 * bass)
            curve = fan + z * (.65 + .52 * mid) * (2 * width - 1)
            x = (.262 + gravity) * np.cos(curve)
            y = (.262 + gravity) * np.sin(curve)
            x += (cx - x) * attract * z ** 1.4
            y += (cy - y) * attract * z ** 1.4
            visibility = np.sin(np.pi * z) ** .65 * (1. - .70 * z)
            alpha = (.07 + .42 * seed ** 3) * strength * visibility * state.lock_fade * gain
            result.append((x, y, alpha, channels))
        return result

    def cursor_dust(self, state):
        if not state.cursor_trail:
            return []
        trail = np.asarray(state.cursor_trail, dtype=np.float32)
        # Relative times use float64 to retain subframes on long-running Windows systems.
        age = np.asarray([state.last - point[2] for point in state.cursor_trail])[:, None]
        spread = .007 + .050 * age
        x = trail[:, :1] + self.trail_noise[0] * spread + .052 * age
        y = trail[:, 1:2] + self.trail_noise[1] * spread + .015 * np.sin(12 * age)
        fade = np.maximum(0., 1 - age / 1.12) ** 1.3
        a = (.18 + .71 * self.trail_tone ** 2.1) * fade * (.65 + .55 * state.energy[2])
        colors = np.broadcast_to(np.where(self.trail_tone > .62, 2, 1), a.shape)
        return [(x.ravel(), y.ravel(), a.ravel(), colors.ravel())]

    def render(self, state):
        w, h = SIZE
        buckets = np.zeros((h * w * 4,), np.uint16)
        def palette_channels(layer):
            x, y, alpha, palette = layer
            return x, y, alpha, np.where(palette < .73, 0, np.where(palette < .97, 1, 2))

        layers = []
        if state.camera[3] < .995:
            layers.extend(map(palette_channels, self.overview(state)))
        if state.shown >= 0 and state.camera[3] > .008:
            layers.append(palette_channels(self.closeup(state)))
            if state.lock_fade > .025:
                layers.extend(self.spray_layers(state))
                layers.extend(self.cursor_dust(state))
        layers.extend(self.arrival_dust(state))
        for x, y, a, channel in layers:
            px, py = (x / ASPECT + .5) * w, (y + .5) * h
            safe = (px >= 1.) & (px < w - 2.) & (py >= 1.) & (py < h - 2.)
            px, py, channel = px[safe], py[safe], channel[safe]
            weight = 255 * a[safe]
            ix, iy = px.astype(np.int32), py.astype(np.int32)
            fx, fy = px - ix, py - iy
            base = (iy * w + ix) * 4 + channel
            np.add.at(buckets, base, (weight * (1. - fx) * (1. - fy)).astype(np.uint16))
            np.add.at(buckets, base + 4, (weight * fx * (1. - fy)).astype(np.uint16))
            np.add.at(buckets, base + w * 4, (weight * (1. - fx) * fy).astype(np.uint16))
            np.add.at(buckets, base + w * 4 + 4, (weight * fx * fy).astype(np.uint16))
        np.minimum(buckets, 255, out=buckets)
        return buckets.astype(np.uint8).reshape(h, w, 4)


class Atlas:
    def __init__(self):
        self.state = CameraState(monotonic())
        self.particles = ParticleField()
        self.track = -1
        self.gains = [0.] * len(SCENES)
        self.spectrum = Spectrum()
        self.shader = op(ROOT + 'solar_atlas')
        self.uniform_parameters = [[getattr(self.shader.par, f'vec{i}value{axis}') for axis in 'xyzw'] for i in range(11)]
        self.panel = op(ROOT + 'viewport')
        self.sources = [op(ROOT + 'audio_' + name) for name in SCENES]
        self.envelopes = [op(ROOT + 'volume_' + name) for name in SCENES]
        self.cloud = op(ROOT + 'particles')
        self.cloud.lock = True
        self.last_raster = 0.0
        self.hover_origin = None
        self.hover_enabled = False

    def apply(self, force=False):
        now = monotonic()
        if force or now - self.last_raster >= .026:
            self.cloud.copyNumpyArray(self.particles.render(self.state))
            self.last_raster = now

        for pars, values in zip(self.uniform_parameters, self.state.uniforms()):
            for par, value in zip(pars, values):
                par.val = float(value)

    def audio(self):
        target = self.state.focus + 1 if self.state.entered else 0
        if target != self.track:
            source = self.sources[target]
            source.par.play = True
            source.par.cuepulse.pulse()
            self.spectrum = Spectrum()
            self.track = target
        for i, node in enumerate(self.envelopes):
            gain = approach(self.gains[i], .52 if i == target else 0., self.state.dt, 7.0 if i == target else 5.5)
            if abs(gain - self.gains[i]) > .000001:
                node.par.gain = gain
            self.gains[i] = gain
            if i != target and gain < .0007 and self.sources[i].par.play.eval():
                self.sources[i].par.play = False
        # Analyze the same time-sliced stereo audio that supplies the device output.
        signal = self.sources[target].numpyArray()
        energy = self.spectrum.read(signal.mean(axis=0)) if signal is not None and signal.size else np.zeros(4)
        energy *= min(1, self.gains[target] * 2) if target else .15
        for i, value in enumerate(energy):
            current = self.state.energy[i]
            self.state.energy[i] = approach(current, value, self.state.dt, 22. if value > current else 6.)

    def tick(self):
        panel = self.panel.panel
        inside = bool(panel.inside.val)
        point = (float(panel.insideu.val), float(panel.insidev.val)) if inside else self.state.pointer
        if not self.hover_enabled:
            if self.hover_origin is None and inside:
                self.hover_origin = point
            elif self.hover_origin is not None:
                self.hover_enabled = not inside or screen_distance(point, self.hover_origin) > .007
        self.state.advance(monotonic(), point, inside and (self.state.entered or self.hover_enabled))
        self.audio()
        self.apply()

    def click(self):
        panel = self.panel.panel
        was_entered = self.state.entered
        self.state.click((float(panel.u.val), float(panel.v.val)), bool(panel.inside.val))
        if was_entered and not self.state.entered:
            self.wait_for_pointer()

    def wait_for_pointer(self):
        self.hover_enabled = False
        self.hover_origin = None


engine = None
testing = False


def atlas():
    global engine
    if engine is None:
        engine = Atlas()
    return engine


def tick():
    if not testing:
        atlas().tick()


def click():
    if not testing:
        atlas().click()


def go_back(value):
    if testing or str(value).lower() not in ('27', 'escape', 'esc', '\x1b'):
        return
    app = atlas()
    if app.state.entered or app.state.focus >= 0:
        app.state.leave()
        app.wait_for_pointer()
