"""Continuous orbits, camera state, audio analysis and shared particle simulation."""

from collections import deque
from math import cos, exp, hypot, sin, tau
from time import monotonic

import numpy as np


ROOT = '/project1/'
FRAME_SIZE = (720, 1280)
ASPECT = FRAME_SIZE[0] / FRAME_SIZE[1]
SIZE = (540, 960)
ARRIVAL_SECONDS = 1.52
HOVER_DWELL = .12
HOVER_RELEASE = .10
CENTER_SECONDS = 1.0
RETURN_SECONDS = .85
SCENES = ('overview', 'sun', 'mercury', 'venus', 'earth', 'mars')
# The overview previously imposed a .015 render minimum on Mercury.
RADII = (.065, .015, .023, .027, .020)
DETAIL_ZOOM = .78 * ASPECT / (2. * max(RADII))
AXIS_POSITIONS = (-.205, -.076, .024, .132, .232)
AXIS_PHASES = (0, 1.37, 2.67, .87, 1.54)
ORBIT_SPEEDS = (0, .27, .21, .16, .13)
SPINS = (.045, .071, -.049, .088, .072)
RETURN = (.092, .926)


def approach(current, target, dt, rate):
    return target + (current - target) * exp(-rate * dt)


def glide(current, velocity, target, dt, seconds):
    # Critical damping reaches roughly 98% of a stationary target in seconds.
    # Carrying the velocity through a target change keeps reversals continuous.
    rate = 5.8 / seconds
    decay = exp(-rate * dt)
    offset = current - target
    slope = velocity + rate * offset
    return target + (offset + dt * slope) * decay, (velocity - rate * dt * slope) * decay


def screen_distance(a, b):
    return hypot((a[0] - b[0]) * ASPECT, a[1] - b[1])


def smooth_between(first, last, value):
    t = np.clip((value - first) / (last - first), 0., 1.)
    return t * t * (3. - 2. * t)


def orbit_positions(time):
    # An edge-on projection keeps the four orbits aligned on one axis.
    return [(center + (0. if i == 0 else .006 + i*.001) * cos(AXIS_PHASES[i] + time*ORBIT_SPEEDS[i]),
             0., radius, time*SPINS[i] + i*.83)
            for i, (center, radius) in enumerate(zip(AXIS_POSITIONS, RADII))]


def explore_axis(position, extent):
    edge = (position - .5) * 2.
    return np.sign(edge) * extent * smooth_between(.43, .99, abs(edge))


class CameraState:
    def __init__(self, now):
        self.start = self.last = now
        self.time = self.dt = self.flow_time = 0.0
        self.bodies = orbit_positions(0.)
        self.camera = (0., 0., 1., 0.)
        self.camera_velocity = (0., 0.)
        self.explore = (0., 0.)
        self.pointer = (.5, .5)
        self.pointer_velocity = (0., 0.)
        self.intent = .0
        self.motion = .0
        self.timelock = 0.0
        self.hover = self.focus = self.shown = -1
        self.hover_anchor = None
        self.hover_started = self.last
        self.hover_left_at = None
        self.hover_candidate = -1
        self.candidate_since = self.last
        self.hover_released_at = None
        self.release_candidate = -1
        self.overview_settle_until = self.last
        self.pan_handoff = None
        self.view = (0., 0.)
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
        self.burst = None

    def center_uv(self, body_id):
        x, y, _, _ = self.bodies[body_id]
        cx, cy, zoom, _ = self.camera
        return ((x - cx) * zoom / ASPECT + .5, (y - cy) * zoom + .5)

    def hit_radius(self, body_id):
        scale = 1. + .14 * self.label_alpha if self.label_id == body_id else 1.
        return self.bodies[body_id][2] * self.camera[2] * scale

    def visible_hit(self, position):
        closest = -1
        distance = 1.0
        for i in range(len(self.bodies)):
            gap = screen_distance(position, self.center_uv(i))
            if gap < self.hit_radius(i) + .019 and gap < distance:
                closest, distance = i, gap
        return closest

    def can_hover(self):
        return self.time >= .67 and self.last >= self.timelock and self.camera[3] < .15

    def holds_hover(self, position, follow=False):
        anchor = self.hover_anchor
        center = self.center_uv(self.hover)
        if (screen_distance(position, anchor) < .024 or
                screen_distance(position, center) < self.hit_radius(self.hover) + .024):
            return True
        if not follow or self.last - self.hover_started > CENTER_SECONDS + .15:
            return False
        # Only the short path swept by this body is eligible during the glide.
        ax, ay = (center[0] - anchor[0]) * ASPECT, center[1] - anchor[1]
        px, py = (position[0] - anchor[0]) * ASPECT, position[1] - anchor[1]
        length_squared = ax*ax + ay*ay
        progress = (ax*px + ay*py) / max(.0001, length_squared)
        return 0. < progress < 1. and hypot(px - progress*ax, py - progress*ay) < .025

    def hit(self, position):
        if not self.can_hover():
            return -1
        if self.hover >= 0 and self.holds_hover(position):
            return self.hover
        return self.visible_hit(position)

    def release_hover(self, position, candidate=-1):
        self.pan_handoff = (self.last, self.bodies[self.hover][:2])
        self.hover = self.hover_candidate = -1
        self.hover_anchor = self.hover_left_at = None
        self.overview_settle_until = self.last + RETURN_SECONDS
        self.hover_released_at = position
        self.release_candidate = candidate

    def update_hover(self, position, inside):
        if self.entered or not self.can_hover():
            self.hover_candidate = -1
            return
        if not inside:
            if self.hover >= 0:
                self.release_hover(None)
            self.hover_candidate = -1
            self.hover_released_at = None
            return
        if self.hover >= 0:
            if self.holds_hover(position, follow=True):
                self.hover_left_at = None
                return
            if self.hover_left_at is None:
                self.hover_left_at = self.last
                self.release_candidate = self.visible_hit(position)
            if self.last - self.hover_left_at < HOVER_RELEASE:
                return
            replacement = self.visible_hit(position)
            self.release_hover(position, replacement if replacement == self.release_candidate else -1)
            return
        target = self.visible_hit(position)
        if self.hover_released_at is not None:
            if screen_distance(position, self.hover_released_at) < .010:
                if target != self.release_candidate:
                    target = -1
            else:
                self.hover_released_at = None
        if target != self.hover_candidate:
            self.hover_candidate = target
            self.candidate_since = self.last
        if target >= 0 and self.last - self.candidate_since >= HOVER_DWELL:
            self.hover = target
            self.hover_anchor = position
            self.hover_started = self.last
            self.hover_left_at = None

    def leave(self):
        self.entered = False
        self.arrival = 1.
        self.arrival_start = None
        self.focus = self.hover = -1
        self.hover_candidate = -1
        self.hover_anchor = self.hover_left_at = self.hover_released_at = None
        self.overview_settle_until = self.last + RETURN_SECONDS
        self.pan_handoff = None
        self.timelock = self.last + .60
        self.cursor_trail.clear()
        self.burst = None

    def click(self, position, inside=True):
        if not inside:
            return
        if self.entered:
            if screen_distance(position, RETURN) < .051:
                self.leave()
            else:
                self.burst = ((position[0] - .5) * ASPECT, position[1] - .5, self.last)
            return
        target = self.hit(position)
        if target >= 0:
            u, v = self.center_uv(target)
            radius = self.hit_radius(target)
            self.arrival_origin = ((u - .5) * ASPECT, v - .5, radius)
            self.arrival_start = self.last
            self.arrival = 0.
            self.focus = self.shown = target
            self.entered = True
            self.hover = -1
            self.hover_candidate = -1
            self.hover_anchor = self.hover_left_at = self.hover_released_at = None
            self.pan_handoff = None
            self.view = (0., 0.)

    def advance(self, now, position, inside):
        self.dt = max(0., min(.080, now - self.last))
        self.last = now
        self.time = now - self.start
        self.bodies = orbit_positions(self.time)
        self.flow_time += self.dt * (.88 + .66 * self.energy[1])
        dt = self.dt
        self.update_hover(position, inside)
        if inside and self.hover < 0 and self.hover_candidate < 0 and not self.entered and self.camera[3] < .15:
            target = (explore_axis(position[0], .14), explore_axis(position[1], .22))
            self.explore = tuple(approach(before, after, dt, 2.7)
                                 for before, after in zip(self.explore, target))
        if self.arrival_start is not None:
            self.arrival = min(1., (now - self.arrival_start) / ARRIVAL_SECONDS)
            if self.arrival >= 1.:
                self.arrival_start = None
        if self.entered and self.focus >= 0:
            x, y, _, _ = self.bodies[self.focus]
            detail = (x, y, DETAIL_ZOOM, 1.)
            camera_seconds = .62
        elif self.hover >= 0:
            detail = (*self.bodies[self.hover][:2], 1., 0.)
            camera_seconds = CENTER_SECONDS
        else:
            pan = self.explore
            if self.pan_handoff is not None:
                started, origin = self.pan_handoff
                blend = smooth_between(0., .22, now - started)
                pan = tuple(a + (b-a)*blend for a, b in zip(origin, pan))
                if blend >= 1.:
                    self.pan_handoff = None
            detail = (*pan, 1., 0.)
            remaining = max(0., self.overview_settle_until - now)
            camera_seconds = .60 + (RETURN_SECONDS - .60) * min(1., remaining / .35)
        x, vx = glide(self.camera[0], self.camera_velocity[0], detail[0], dt, camera_seconds)
        y, vy = glide(self.camera[1], self.camera_velocity[1], detail[1], dt, camera_seconds)
        self.camera_velocity = (vx, vy)
        self.camera = (x, y, approach(self.camera[2], detail[2], dt, 4.9),
                       approach(self.camera[3], detail[3], dt, 4.3))
        if self.focus < 0 and self.camera[3] < .008:
            self.shown = -1
        speed = min(1., screen_distance(self.pointer, position) * 16.) if inside else 0.
        self.motion = approach(self.motion, speed, dt, 18. if speed > self.motion else 3.8)
        previous_pointer = self.pointer
        if inside:
            self.pointer = tuple(approach(before, after, dt, 12.) for before, after in zip(self.pointer, position))
        velocity = ((self.pointer[0] - previous_pointer[0]) * ASPECT / max(.005, dt),
                    (self.pointer[1] - previous_pointer[1]) / max(.005, dt))
        self.pointer_velocity = tuple(approach(before, after, dt, 9.) for before, after in
                                      zip(self.pointer_velocity, velocity))
        in_return = self.entered and inside and screen_distance(position, RETURN) < .051
        if self.entered and inside and not in_return:
            yaw, pitch = (position[0] - .5) * tau, (position[1] - .5) * 2.48
            self.view = (approach(self.view[0], yaw, dt, 8.5),
                         approach(self.view[1], pitch, dt, 8.5))
        self.intent = approach(self.intent, float(self.entered and inside and not in_return), dt, 7.)
        self.back_glow = approach(self.back_glow, float(in_return), dt, 12.)
        self.lock_fade = approach(self.lock_fade, float(self.entered), dt, 6.7)
        if self.entered and inside and not in_return and speed > .13:
            point = ((self.pointer[0] - .5) * ASPECT, self.pointer[1] - .5)
            self.cursor_trail.append((*point, now))
        while self.cursor_trail and now - self.cursor_trail[0][2] > 1.12:
            self.cursor_trail.popleft()
        if self.burst and now - self.burst[2] > 1.25:
            self.burst = None
        self.update_label(inside)

    def update_label(self, inside):
        target = self.hover if inside and not self.entered else -1
        if target != self.label_id and self.label_alpha < .022:
            self.label_id = target
            if target >= 0:
                self.label_side = -1. if self.bodies[target][0] > .055 else 1.
        visible = target >= 0 and target == self.label_id
        self.label_leaving = not visible
        self.label_alpha = approach(self.label_alpha, float(visible), self.dt, 8.5 if visible else 6.1)

    def uniforms(self):
        return (self.camera, (self.time, *self.pointer, self.intent * (.26 + .74 * self.motion)), tuple(self.energy),
                (self.shown, self.lock_fade, self.hover if not self.entered else -1, self.back_glow),
                *self.bodies, (self.label_id, self.label_alpha, self.label_side, float(self.label_leaving)),
                (self.arrival, *self.arrival_origin), (*self.view, float(self.entered), 0.))


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
        count = 35200
        self.random = rng.random((7, count))
        self.lane = rng.normal(0, 1, count)
        self.spark = .10 + .61 * self.random[4] ** 4.7
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
        layers = [(sun_x + lx*.53, sun_y + ly*.72, fade * brightness*.60, .825 + .175 * hue)]

        seed, spread, line, spark, color, tempo = self.stream
        distance = np.clip((seed - .5) * 2., -.99, .99)
        swirl = 2 * np.pi * line + state.flow_time * (.17 + tempo * .09)
        px = distance * .91 + .023 * np.sin(swirl)
        ridge = .006 * np.sin(px * 14.1 - .22 * state.flow_time)
        thickness = .004 + .018 * abs(distance) + .011 * state.energy[0]
        py = ridge + self.scatter * thickness * (.48 + .85 * spread)
        embers = np.exp(-((abs(distance) - .29) / .35) ** 2)
        clouds = np.exp(-((abs(distance) - .75) / .20) ** 2)
        bright = (.10 + .62 * spark ** 3) * (.88 * embers + .42 * clouds)
        bright *= .64 + .36 * np.sin(swirl + px * 11) ** 2
        layers.append((sun_x + px, sun_y + py, fade * bright, color * .92))

        x, y, intensity, hue = self.sky
        shimmer = .72 + .28 * np.sin(181 * intensity + .47 * state.time)
        layers.append(((x - .5) * (ASPECT + .32), (y - .5) * 1.56,
                       (.031 + .20 * intensity ** 5) * shimmer * fade, hue))
        return [((x - cx) * zoom, (y - cy) * zoom, a, h) for x, y, a, h in layers]

    def closeup(self, state):
        r, azimuth, speed, drift, _, choice, height = self.random
        i = state.shown
        bass, mid, high, event = state.energy
        time = state.flow_time
        phase = (r + time * (.051 + .088 * speed)) % 1.
        side = np.where(azimuth >= .5, 1., -1.)
        branch = (azimuth * 2.) % 1. - .5
        spread = self.lane * (.45 + phase)
        if i == 0:  # Two opposed prominences coil out from the Sun.
            theta = 2. * np.pi * azimuth + side * (2.7 * phase + .18 * time)
            radius = .27 + phase * (.31 + .16 * drift + .19 * bass)
            radius += .056 * np.sin(3. * theta + time) + .030 * spread
            strip, plume = radius * np.cos(theta) * 1.47, radius * np.sin(theta) * .73
        elif i == 1:  # A short seam feeds a narrow downstream wake.
            strip = -.46 + phase * (1.38 + .32 * bass)
            plume = .11 * np.sin(3. * strip + time * .47) + .062 * spread
            plume += branch * (.08 + .22 * phase)
        elif i == 2:  # Venus throws two broad, curved veils into opposite corners.
            theta = .82 + 2.5 * phase + .14 * time + .19 * spread + branch * .59
            radius = .17 + phase * (.78 + .22 * bass + .19 * drift)
            strip = side * radius * (np.cos(theta) - .24)
            plume = side * radius * np.sin(theta) * .56 + .049 * spread
        elif i == 3:  # A layered, ribbon-like aurora opens diagonally around Earth.
            strip = (phase - .5) * (1.86 + .35 * bass)
            plume = .15 * np.sin(strip * 5.8 - time * .48) + side * (.081 + .060 * phase)
            plume += .066 * spread + branch * .21
        else:  # Dust leaves Mars in two forks with different flight speeds.
            strip = -.55 + phase * (1.51 + .27 * side + .22 * bass)
            plume = side * (.055 + .22 * phase) + .085 * spread
            plume += .076 * np.sin(5.6 * strip + time * .76 + branch)
        lean = (.94, 1.17, 1.10, 1.05, -1.11)[i]
        x = (strip * cos(lean) - plume * sin(lean)) * .68
        y = (strip * sin(lean) + plume * cos(lean)) * .90
        mx, my = (state.pointer[0] - .5) * ASPECT, state.pointer[1] - .5
        vx, vy = state.pointer_velocity
        dx, dy = mx - x, my - y
        local = np.exp(-(dx * dx + dy * dy) / .052)
        pull = state.intent * local * (.47 + .39 * state.motion) * (.32 + .64 * phase)
        x += dx * pull + (-dy * .19 + np.tanh(vx) * .25) * pull * state.motion
        y += dy * pull + (dx * .19 + np.tanh(vy) * .25) * pull * state.motion
        life = np.sin(np.pi * phase) ** .64
        a = self.spark * life * state.camera[3] ** 1.26
        a *= (1.20 + .91 * bass + (1.17 * event + .86 * high) * (choice > .65))
        clusters = np.sin(strip * 14.3 + 2.1 * side - time*.31) ** 4
        a *= (.72+.43*clusters) * (1. + .62 * pull)
        a *= 1. - .74 * np.exp(-(x/.145)**2) * smooth_between(.325,.476,y)
        if state.burst:
            bx, by, began = state.burst
            age = state.last - began
            rx, ry = x - bx, y - by
            distance = np.hypot(rx, ry)
            shake = np.exp(-((distance - .53 * age) / .092) ** 2) * np.sin(np.pi * age / 1.25)
            shove = .21 * shake / (distance + .062)
            x += rx * shove
            y += ry * shove
            a *= 1. + 1.3 * shake
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
        strength = .44 + 1.25 * attack + .47 * high
        align = .19 + .16 * (state.shown % 3)
        u, v = state.center_uv(state.shown)
        origin_x, origin_y = (u - .5) * ASPECT, v - .5
        rim = state.bodies[state.shown][2] * state.camera[2] * 1.23
        cx, cy = (state.pointer[0] - .5) * ASPECT, state.pointer[1] - .5
        probe = rim + .088
        local = np.exp(-((origin_x + probe*np.cos(fan) - cx) ** 2 +
                         (origin_y + probe*np.sin(fan) - cy) ** 2) / .16)
        attract = .52 * state.motion * state.intent * local
        result = []
        channels = np.where(hue > .85, 2, np.where(hue > .38, 1, 0))
        for delay, gain in ((0., 1.), (.017, .52), (.036, .24), (.061, .11)):
            z = np.maximum(0., age - delay)
            gravity = (align + .24 * seed) * z * (1 + .66 * bass)
            curve = fan + z * (.65 + .52 * mid) * (2 * width - 1)
            x = origin_x + (rim + gravity) * np.cos(curve)
            y = origin_y + (rim + gravity) * np.sin(curve)
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
        a = (.23 + .85 * self.trail_tone ** 2.1) * fade * (.69 + .60 * state.energy[2])
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
        self.uniform_parameters = [[getattr(self.shader.par, f'vec{i}value{axis}') for axis in 'xyzw']
                                   for i in range(min(self.shader.seq.vec.numBlocks, len(self.state.uniforms())))]
        nebula = op(ROOT + 'nebula_field')
        self.nebula_uniforms = () if nebula is None else tuple(
            tuple(getattr(nebula.par, f'vec{i}value{axis}') for axis in 'xyzw') for i in range(3))
        self.panel = op(ROOT + 'viewport')
        self.sources = [op(ROOT + 'audio_' + name) for name in SCENES]
        self.envelopes = [op(ROOT + 'volume_' + name) for name in SCENES]
        self.cloud = op(ROOT + 'particles')
        self.feedback = op(ROOT + 'feedback_material')
        self.closeup = op(ROOT + 'closeup_feedback')
        self.rms = 0.
        self.cloud.lock = True
        self.last_raster = 0.0
        self.hover_origin = None
        self.hover_enabled = False

    def apply(self, force=False):
        now = monotonic()
        if force or now - self.last_raster >= .026:
            self.cloud.copyNumpyArray(self.particles.render(self.state))
            self.last_raster = now

        uniforms = self.state.uniforms()
        targets = (*zip(self.uniform_parameters, uniforms), *zip(self.nebula_uniforms, uniforms[1:4]))
        for pars, values in targets:
            for par, value in zip(pars, values):
                par.val = float(value)
        bass, mid, _, attack = self.state.energy
        if self.feedback is not None:
            close = self.state.lock_fade
            self.feedback.par.Drive = float((1.-close)*(.16+.89*bass+.32*attack) + close*(.12+1.74*self.rms))
            self.feedback.par.Detail = float(.50 + (1.-close)*.96*mid + close*1.50*self.rms)
        if self.closeup is not None:
            self.closeup.par.Harmonicgain = .5 + 1.5 * self.rms

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
        if signal is not None and signal.size:
            mono = signal.mean(axis=0)
            self.rms = float(np.sqrt(np.mean(mono * mono)))
            energy = self.spectrum.read(mono)
        else:
            self.rms = 0.
            energy = np.zeros(4)
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
