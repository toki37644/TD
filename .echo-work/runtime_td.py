"""TouchDesigner Text DAT: the shared input, discovery, and route state."""
from math import exp, hypot
from time import monotonic

BEACONS = ((.39, .43), (.63, .66), (.82, .39))
ASPECT = 1200 / 675
HOLD_SECONDS = .32
WAVE_SPEED = .75
ROOT = '/project1/'


def distance(a, b):
    return hypot((a[0] - b[0]) * ASPECT, a[1] - b[1])


def reset_target(pos):
    return 1090 <= pos[0]*1200 <= 1160 and 605 <= (1-pos[1])*675 <= 655


class Survey:
    def __init__(self, now):
        self.start = self.last = now
        self.cursor = (.62, .5)
        self.hover = 0.
        self.down = None
        self.pulse = None
        self.origin = (.62, .5)
        self.seen = [False]*3
        self.route = []
        self.launched = None
        self.key_down = False
        self.strikes = [None]*3
        self.motif = []

    def button(self, now, down, pos, inside=True):
        if down:
            if inside and self.down is None:
                self.down = (now, pos)
            return
        if self.down is None:
            return
        pressed, start_pos = self.down
        self.down = None
        if not inside:
            return
        if reset_target(start_pos) and reset_target(pos):
            self.__init__(now)
            return
        if now - pressed >= HOLD_SECONDS:
            self.origin, self.pulse = pos, now
            return
        if distance(pos, start_pos) > .07:
            return
        nearest = min(range(3), key=lambda i: distance(pos, BEACONS[i]))
        if self.seen[nearest] and distance(pos, BEACONS[nearest]) <= .062:
            self.strikes[nearest] = now
            if nearest not in self.route:
                self.route.append(nearest)
                if len(self.route) == 3:
                    self.launched = now
                    self.motif = [(now + .70 + i * .58, b) for i, b in enumerate(self.route)]

    def advance(self, now, pos, inside):
        dt = max(0., min(.3, now - self.last))
        self.last = now
        gain = 1. - exp(-dt * 16.)
        if inside:
            if self.hover < .02:
                self.cursor = pos
            else:
                self.cursor = tuple(a+(b-a)*gain for a,b in zip(self.cursor, pos))
        self.hover += (float(inside) - self.hover) * (1.-exp(-dt*8.))
        radius = strength = charge = progress = 0.
        if self.pulse is not None:
            age = max(0., now - self.pulse)
            radius = age * WAVE_SPEED
            strength = min(1., max(0., (2.15-radius)/.32))
            for i, point in enumerate(BEACONS):
                if distance(self.origin, point) <= radius:
                    self.seen[i] = True
            if radius > 2.15:
                self.pulse = None
        if self.down is not None:
            charge = min(1., max(0., now-self.down[0])/.85)
        if self.launched is not None:
            progress = min(1., max(0., now-self.launched)/4.8)
        while self.motif and self.motif[0][0] <= now:
            when, index = self.motif.pop(0)
            self.strikes[index] = when
        music = [0. if t is None or now-t > 1.8 else exp(-max(0.,now-t)*3.1) for t in self.strikes]
        order = self.route + [-1]*(3-len(self.route))
        return ((now-self.start, *self.cursor, self.hover),
                (*self.origin, radius, strength),
                (*map(float, self.seen), charge),
                (*order, progress), (*music, 0.))


survey = Survey(monotonic())
paused_for_capture = False
_vectors = None


def apply(vectors):
    global _vectors
    if _vectors is None:
        shader = op(ROOT+'starfield')
        _vectors = [[getattr(shader.par, 'vec%dvalue%s' % (i, axis)) for axis in 'xyzw'] for i in range(5)]
    for pars, values in zip(_vectors, vectors):
        for par, value in zip(pars, values):
            if par.eval() != value:
                par.val = value


def panel_input():
    panel = op(ROOT+'viewport').panel
    down = bool(panel.lselect.val)
    pos = ((float(panel.u.val), float(panel.v.val)) if down else
           (float(panel.insideu.val), float(panel.insidev.val)))
    return pos, bool(panel.inside.val), down


def button_event(down):
    if paused_for_capture:
        return
    pos, inside, _ = panel_input()
    # The clicked UV is also available on release when a fast click spans no frame ticks.
    if not down and inside:
        panel = op(ROOT+'viewport').panel
        pos = (float(panel.u.val), float(panel.v.val))
    survey.button(monotonic(), down, pos, inside)


def frame():
    if paused_for_capture:
        return
    now = monotonic()
    pos, inside, down = panel_input()
    key = bool(op(ROOT+'reset_key')[0][0])
    if key and not survey.key_down:
        survey.__init__(now)
    survey.key_down = key
    if down != (survey.down is not None):
        survey.button(now, down, pos, inside)
    apply(survey.advance(now, pos, inside))


def reset():
    global survey
    survey = Survey(monotonic())
    apply(survey.advance(survey.start, survey.cursor, False))
