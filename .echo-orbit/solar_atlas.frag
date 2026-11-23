// Solar system and procedural light. The particles arriving on input 0 are simulated separately.
uniform vec4 uCamera;  // world center, zoom, blend into the current destination
uniform vec4 uPointer; // seconds, normalized screen position, local attraction
uniform vec4 uAudio;   // low, mid, high, transient
uniform vec4 uScene;   // destination, committed view, hover indicator, back indicator
uniform vec4 uSun;
uniform vec4 uMercury;
uniform vec4 uVenus;
uniform vec4 uEarth;
uniform vec4 uMars;
uniform vec4 uLabel;   // labeled body, opacity, side of the leader, dispersing

out vec4 fragColor;

const vec2 ASPECT = vec2(16.0 / 9.0, 1.0);

float hash21(vec2 p) {
    vec3 q = fract(vec3(p.xyx) * .1031);
    q += dot(q, q.yzx + 33.33);
    return fract((q.x + q.y) * q.z);
}

mat2 turn(float a) {
    return mat2(cos(a), sin(a), -sin(a), cos(a));
}

float bell(float x) {
    return exp(-x * x);
}

vec3 coolTint(int index) {
    if (index == 0) return vec3(.42, .11, .29);
    if (index == 1) return vec3(.15, .19, .46);
    if (index == 2) return vec3(.36, .16, .43);
    if (index == 3) return vec3(.08, .25, .56);
    if (index == 4) return vec3(.43, .075, .26);
    return vec3(.255, .104, .59);
}

vec3 hotTint(int index) {
    if (index == 0) return vec3(1.00, .54, .24);
    if (index == 1) return vec3(.64, .74, 1.00);
    if (index == 2) return vec3(1.00, .77, .42);
    if (index == 3) return vec3(.47, .87, 1.00);
    if (index == 4) return vec3(1.00, .48, .32);
    return vec3(.91, .45, .71);
}

vec3 nebulaLayer(vec2 screen, vec2 pointer, int scene) {
    float detail = uCamera.w;
    if (detail < .002 || scene < 0) return vec3(.0015, .0016, .0032);
    float time = uPointer.x;
    vec2 field = screen;
    vec2 rel = screen - pointer;
    float pull = bell(length(rel) / .23) * uPointer.w;
    field += .14 * rel * pull;
    field *= 1.0 - (.039 * uAudio.x + .018 * uAudio.w) * uScene.y;
    vec2 source;
    vec3 tint;
    float envelope = 1.0;
    float gradeAmount = .31;

    if (scene == 0) {
        // Turn the video texture around two opposite prominences.
        float distance = length(field / vec2(1.15, 1.0));
        float angle = atan(field.y, field.x);
        float lift = sin(2.0 * angle - .22 * time);
        float flame = .342 + .041 * sin(3.0 * angle + .21 * time) + .054 * uAudio.x;
        float width = .096 + .046 * sin(angle - .57) * sin(angle - .57);
        envelope = bell((distance - flame) / width) *
                   (.13 + .87 * pow(.5 + .5 * sin(2.0 * angle + .90), 1.9));
        source = vec2(.53 + .28 * cos(2.0 * angle - .14 * time), .49 + 1.27 * (distance - flame) + .116 * lift);
        tint = vec3(1.77, .76, .34);
        gradeAmount = .82;
    } else if (scene == 1) {
        // A short, cold wake, narrowing into a lit seam by the planet.
        vec2 wake = turn(-.41) * (field + vec2(.07,.033));
        float path = .082 * sin(3.4 * wake.x);
        float width = .047 + .101 * smoothstep(-.18,.72,wake.x);
        envelope = bell((wake.y - path) / width) *
                   smoothstep(-.46,-.05,wake.x) * (1.0 - smoothstep(.63,.97,wake.x));
        source = vec2(.40 + .58 * wake.x, .493 + 1.22 * (wake.y - path) + .23 * wake.x);
        tint = vec3(.93, 1.31, 1.81);
        gradeAmount = .86;
    } else if (scene == 2) {
        // Two billows roll around the two sides of Venus.
        vec2 billow = turn(.26) * field;
        float fold = billow.x - .125 * sin(billow.y * 7.5 - .19 * time);
        float lip = .345 + .092 * sin(5.1 * billow.y + .23 * time);
        float left = bell((fold + lip) / .186) * bell((billow.y + .13) / .52);
        float right = bell((fold - lip) / .196) * bell((billow.y - .19) / .52);
        envelope = left + right;
        source = vec2(.53 + fold * .62, .53 + .64 * billow.y + .18 * sin(fold * 4.8));
        tint = vec3(1.56, 1.01, 1.29);
        gradeAmount = .55;
    } else if (scene == 3) {
        // Keep the diagonal sweep of the source in the Earth scene.
        source = vec2(.50, .505) + vec2(.465 * field.x + .045 * field.y, .49 * field.y - .085 * field.x);
        tint = vec3(1.08, 1.30, 1.90);
    } else {
        // Dust fans fork toward the upper left in two overlapping streaks.
        vec2 fan = turn(-2.53) * (field - vec2(.06,-.033));
        float bow = .11 * sin(fan.x * 4.1) - .024;
        float spread = .075 + .205 * smoothstep(-.13,.64,fan.x);
        float primary = bell((fan.y - bow) / spread);
        float secondary = bell((fan.y - bow + .147 * smoothstep(.01,.70,fan.x)) / (.44 * spread));
        envelope = (.84 * primary + .52 * secondary) * smoothstep(-.20,.06,fan.x) *
                   (1.0 - smoothstep(.65,.97,fan.x));
        source = vec2(.65 - .57 * fan.x, .515 + .90 * (fan.y - bow) - .21 * fan.x);
        tint = vec3(1.87, .70, .51);
        gradeAmount = .86;
    }
    float margin = min(min(source.x, 1.0 - source.x), min(source.y, 1.0 - source.y));
    float feather = smoothstep(.0, .105, margin);
    vec3 footage = texture(sTD2DInputs[1], clamp(source, .001, .999)).rgb;
    const vec3 LUMA = vec3(.229, .614, .157);
    float light = dot(footage, LUMA);
    vec3 graded = mix(footage, light * tint, gradeAmount);
    graded *= (.73 + .27 * smoothstep(.016, .36, light)) * (.89 + .23 * uAudio.y * uScene.y);
    graded += tint * max(0.0, light - .20) * (.06 + .13 * uAudio.w * uScene.y);
    return vec3(.0015, .0016, .0032) + graded * envelope * feather * smoothstep(.07, .94, detail);
}
vec3 whiteLight(int id) {
    if (id == 0) return vec3(1.00, .825, .62);
    if (id == 1) return vec3(.80, .88, 1.00);
    if (id == 2) return vec3(1.00, .872, .75);
    if (id == 3) return vec3(.74, .94, 1.00);
    return vec3(1.00, .74, .68);
}

vec3 coloredLight(int id) {
    if (id == 0) return vec3(1.00, .46, .21);
    if (id == 1) return vec3(.45, .57, .94);
    if (id == 2) return vec3(.95, .63, .37);
    if (id == 3) return vec3(.29, .66, .92);
    return vec3(.92, .36, .38);
}

vec2 sheetDensity(vec3 p, float stage, float kind, float energy) {
    // The folds remain continuous through the interior of the sphere.
    float winding = 2.36*p.x + 2.22*p.z + .24*stage + kind*.67;
    float v = sin(winding + .98*sin(3.18*p.z - 1.42*p.y));
    float turn = sin(4.05*p.z - 2.62*p.x - .37*stage + kind*.61);
    float flutter = sin(7.3*p.x + 6.6*p.z + .79*sin(4.0*p.y) + .31*stage);
    float shelf = p.y - (.31*v + .19*turn + .072*flutter);
    float sweep = p.y + .46*p.z + .39*p.x
                  - .24*sin(3.16*p.x - 2.14*p.z + .33*stage) + .16;
    float seam = abs(shelf + .09 + energy*.09);
    float seam2 = abs(sweep - .014*sin(12.0*p.z - .6*stage));
    float folded = exp(-seam * 17.5) * (.21 + .79*pow(.5 + .5*turn, 2.0));
    float wing = exp(-seam2 * 23.0) * (.35 + .65*pow(.5 + .5*v, 3.0));
    float echo = exp(-abs(shelf - .112) * 14.0) * (.15 + .25*pow(.5 + .5*flutter, 2.0));
    float volume = folded + .76*wing + echo;
    float lace = (.20 + .80*pow(.5 + .5*flutter, 3.0)) * (folded + wing);
    return vec2(volume, lace);
}

vec3 bodyLayer(vec3 background, vec2 world, vec2 cursor, vec4 body, int id,
               float visible, bool selected, float time, float specks) {
    if (visible <= .001) return background;
    vec2 q = (world - body.xy) / body.z;
    float d = length(q);
    if (d > 1.33) return background;

    float engagement = selected ? uScene.y : 0.0;
    float audio = selected ? uAudio.x * engagement : 0.0;
    float attack = selected ? uAudio.w * engagement : 0.0;
    vec3 tinted = coloredLight(id);
    vec3 shimmer = whiteLight(id);
    if (id == 0) {
        float detail = uCamera.w;
        tinted = mix(vec3(.38, .46, .88), tinted, detail);
        shimmer = mix(vec3(.83, .89, 1.0), shimmer, detail);
    }
    vec2 limb = q / max(d, .0001);
    vec2 light = normalize(mix(vec2(-.39, .67), vec2(-.37, .67) + 1.17*cursor,
                                .86*engagement));
    float shading = .44 + .56 * smoothstep(-.85, .91, dot(limb, light));
    float band = sin(10.5*atan(limb.y, limb.x) + 1.8*sin(4.63*limb.y - body.w));
    float edge = bell((d - .981) * 62.0) * (.107 + .121*shading + .095*band*band);
    float veil = exp(-max(0.0, d - 1.0) * 43.0) * bell((d - .97) * 9.7);
    float lightBloom = (.056 + .051*audio + .052*attack) * veil;
    background += visible * (tinted * lightBloom + shimmer * edge * shading);
    float litSpecks = specks * (1.0 - smoothstep(1.13, 1.31, d));
    vec3 luminousDots = visible * litSpecks * mix(tinted, shimmer, .78) * (1.16 + .25*shading);
    if (d >= 1.0) return background + luminousDots;

    float depth = sqrt(max(0.0, 1.0 - dot(q, q)));
    float yaw = body.w * .83 + .41 * cursor.x * engagement;
    float tilt = .13 - .39 * cursor.y * engagement;
    mat2 yawTurn = turn(yaw);
    mat2 pitchTurn = turn(tilt);
    float projection = body.z * uCamera.z * 675.0;
    int steps = projection < 74.0 ? 11 : 22;
    float stride = (2.0 * depth) / float(steps);
    float phase = time * (.33 + .075 * float(id)) + 1.2*audio;
    vec2 pixel = gl_FragCoord.xy;
    float grit = hash21(pixel);
    float sum = 0.0;
    float threads = 0.0;
    for (int zIndex = 0; zIndex < 22; ++zIndex) {
        if (zIndex >= steps) break;
        float z = -depth + (float(zIndex) + .39 + .26 * grit) * stride;
        vec3 p = vec3(q, z);
        p.xz = yawTurn * p.xz;
        p.yz = pitchTurn * p.yz;
        vec2 vapor = sheetDensity(p, phase, float(id), audio);
        float current = .64 + .36 * sin(p.x * 9.3 - p.y * 7.1 + 1.75*float(id));
        float nearView = .59 + .41 * smoothstep(-.53, .71, z);
        sum += vapor.x * (.54 + .46*current) * nearView;
        threads += vapor.y * nearView;
    }

    sum *= stride;
    threads *= stride;
    float clear = (1.0 - smoothstep(.94, 1.0, d));
    float inclusion = pow(clamp(grit, .03, 1.0), 1.4);
    float powder = .49 + .64 * inclusion;
    vec3 lightBody = tinted * sum * (.32 + .29 * shading);
    lightBody += shimmer * pow(max(0.0, sum + .19*threads), 1.42) * (2.02 + .42 * audio);
    lightBody += shimmer * threads * inclusion * .28;
    if (id == 0) {
        lightBody *= 1.0 + .54 * (1.0 - uCamera.w);
    }
    float absorption = min(.94, sum * .34 + pow(depth, .46) * .66) * clear;
    vec3 inside = background * (1.0 - visible * absorption);
    return inside + lightBody * powder * clear * visible + luminousDots;
}
float lineSegment(vec2 p, vec2 a, vec2 b) {
    vec2 d = b - a;
    return length(p - a - d * clamp(dot(p - a, d) / dot(d, d), 0.0, 1.0));
}

float arcGate(float angle, float middle, float width) {
    return smoothstep(cos(width + .15), cos(width), cos(angle - middle));
}

float orbitTrace(float radius, float target, float pixels, float thin) {
    return bell((radius - target) * pixels / thin);
}

float planetLight(int index, float time) {
    float start = index == 0 ? .16 : .92 + .24 * float(index);
    return smoothstep(start, start + .59, time);
}

vec3 openingSignal(vec2 point, float time) {
    float at = 1.0 - smoothstep(.39, 1.22, time);
    float pulse = smoothstep(.03, .28, time) * at;
    vec2 p = point * (675.0 * uCamera.z);
    float radius = length(p);
    float glimmer = bell(radius / 4.5) + .25 * bell(radius / 21.0);
    glimmer += bell(p.y / 1.0) * bell(p.x / 63.0) * .32;
    glimmer += bell(p.x / .87) * bell(p.y / 32.0) * .26;
    float wave = orbitTrace(radius, time * 151.0, 1.0, 1.25) * pulse * .30;
    return vec3(.67, .81, 1.0) * (pulse * glimmer + wave);
}

vec3 atlasDial(vec2 point, vec2 orbitUV, float time) {
    float wide = 1.0 - smoothstep(.06, .71, uCamera.w);
    if (wide < .002) return vec3(0.0);
    const float TAU = 6.2831853;
    float pixels = 675.0 * uCamera.z;
    vec2 plane = turn(.21) * point / vec2(1.0, .87);
    float radius = length(plane);
    float angle = atan(plane.y, plane.x);
    vec3 silver = vec3(.47, .56, .72);
    vec3 blue = vec3(.20, .35, .70);

    float sweep = fract((angle + 1.34) / TAU);
    float sweepTime = smoothstep(.22, 1.68, time);
    float open = smoothstep(.12, .31, time) * (1.0 - smoothstep(sweepTime, sweepTime + .075, sweep));
    open = mix(open, 1.0, smoothstep(1.30, 1.77, time));
    float lead = bell((sweep - sweepTime) / .014) * (1.0 - smoothstep(1.27, 1.67, time));
    float shimmer = .84 + .16 * sin(angle * 3.0 - time * .32);
    float nearArc = arcGate(angle, -2.08, 1.29);
    float opposite = arcGate(angle, .66, .78);
    float inner = orbitTrace(radius, .235, pixels, .59) * (.21 + .55 * nearArc + .47 * opposite);
    float middle = orbitTrace(radius, .264, pixels, .65) * (.17 + .73 * nearArc);
    float pair = orbitTrace(radius, .274, pixels, .58) * (.19 + .48 * opposite);
    float outer = orbitTrace(radius, .320, pixels, .83) * (.35 + .68 * arcGate(angle, -1.71, 1.34));
    float fineGap = 1.0 - bell((angle + .91) / .082);
    vec3 color = (silver * (.32 * inner + .24 * middle) +
                  blue * (.29 * pair + .49 * outer)) * (shimmer * open + lead) * fineGap;

    float slots = angle * 144.0 / TAU;
    float spoke = abs(fract(slots + .5) - .5);
    float cardinal = 1.0 - step(.1, mod(floor(slots + .5), 6.0));
    float stroke = bell(spoke * TAU / 144.0 * radius * pixels / .72);
    float tickSpan = (1.0 - smoothstep(.0032 + .008 * cardinal, .0045 + .009 * cardinal, abs(radius - .257)));
    color += silver * stroke * tickSpan * (.14 + .12 * cardinal) * open * (.17 + .83 * nearArc);
    float beadAngle = abs(fract(angle * 58.0 / TAU + .5) - .5) * TAU / 58.0;
    float bead = length(vec2((radius - .299) * pixels, radius * beadAngle * pixels));
    float pearl = bell(bead / 1.17) + .24 * bell(bead / 3.3);
    float lantern = pow(.5 + .5 * sin(angle * 2.0 + time * .54), 3.0);
    color += mix(blue, silver, .36 + .47 * lantern) * pearl * (.16 + .27 * lantern) * open * (.22 + .78 * nearArc);

    float outerReveal = smoothstep(.78 + .31 * radius, 1.86 + .38 * radius, time);
    float partialOuter = arcGate(angle, 1.98, 1.12);
    float lowerArc = arcGate(angle, -1.08, 1.16);
    float etch = orbitTrace(radius, .390, pixels, .74) * (.18 + .51 * partialOuter);
    etch += .65 * orbitTrace(radius, .407, pixels, .63) * partialOuter;
    etch += .68 * orbitTrace(radius, .478, pixels, .70) * lowerArc;
    etch += .57 * orbitTrace(radius, .587, pixels, .65) * (.2 + .8 * partialOuter);
    etch += .40 * orbitTrace(radius, .756, pixels, .65) * (.15 + .85 * lowerArc);
    float sweepBeam = bell((radius - (.32 + .23 * fract(time * .105))) / .009);
    color += mix(silver, blue, .57) * (etch * .27 + sweepBeam * .026 * partialOuter) * outerReveal;

    float trackRadius = length(orbitUV);
    float trackAngle = atan(orbitUV.y, orbitUV.x);
    float orbitR[4] = float[4](.273, .445, .627, .817);
    for (int i = 0; i < 4; ++i) {
        float rank = float(i);
        float arrived = smoothstep(.52 + .14 * rank, 1.30 + .19 * rank, time);
        float trace = orbitTrace(trackRadius, orbitR[i], pixels, .90);
        float companion = orbitTrace(trackRadius, orbitR[i] + .014, pixels, .74);
        float side = arcGate(trackAngle, 2.15 - .72 * rank, .94);
        float dotted = bell((fract(trackAngle * 29.0 / TAU + .5) - .5) / .13);
        color += mix(silver, blue, .38 + .11 * rank) * arrived *
                 (trace * (.095 + .17 * side) + companion * (.067 + .15 * dotted) * side);
    }
    return color * wide;
}

vec3 planetDial(vec2 point, vec4 body, int index, float time, bool hovered) {
    vec2 p = (point - body.xy) * (675.0 * uCamera.z);
    float rim = body.z * (675.0 * uCamera.z);
    float distance = length(p);
    if (distance > rim + 26.0) return vec3(0.0);
    float angle = atan(p.y, p.x);
    float sectors = arcGate(angle, 1.20 + .45 * float(index), .71);
    float echo = arcGate(angle, -1.99 + .48 * float(index), .45);
    float trace = orbitTrace(distance, rim + 7.0, 1.0, .74) * (.33 + .67 * sectors);
    trace += orbitTrace(distance, rim + 13.0, 1.0, .74) * (.58 * sectors + .59 * echo);
    float vertex = orbitTrace(distance, rim + 17.0, 1.0, 1.35) * arcGate(angle, time * .36 + float(index), .041);
    float brightness = hovered ? .70 : .29;
    return mix(vec3(.47,.60,.77), whiteLight(index), .29) * brightness *
           (trace + .72 * vertex) * planetLight(index, time) * (1.0 - smoothstep(.05, .63, uCamera.w));
}

float nameInk(vec2 point, int index) {
    vec2 coord = point / vec2(64.0,28.0) + .5;
    if (any(lessThan(coord,vec2(0.0))) || any(greaterThan(coord,vec2(1.0)))) return 0.0;
    coord.y = (coord.y + float(4 - index)) / 5.0;
    return texture(sTD2DInputs[2], coord).r;
}

vec3 planetCaption(vec2 screen, vec4 body, int index) {
    float alpha = uLabel.y;
    float side = uLabel.z;
    float dissolve = 1.0 - alpha;
    float outward = uLabel.w;
    float pixels = 675.0 * uCamera.z;
    vec2 center = (body.xy - uCamera.xy) * pixels;
    float radius = body.z * pixels;
    vec2 origin = center + vec2(side * (radius * .76 + 73.0), min(radius * .64 + 32.0, 128.0));
    origin = clamp(origin, vec2(-535.0,-295.0), vec2(535.0,295.0));
    vec2 point = screen * 675.0;
    vec2 local = point - origin;
    if (abs(local.x) > (radius + 157.0) || abs(local.y) > radius + 63.0) return vec3(0.0);

    float coherent = smoothstep(.30,.91,alpha);
    float letters = nameInk(local, index) * coherent;
    float specks = 0.0;
    if (alpha < .985 && abs(local.x) < 95.0 && abs(local.y) < 52.0) {
        for (int layer = 0; layer < 4; ++layer) {
            float lane = float(layer);
            float drift = dissolve * (outward > .5 ? 1.0 : -.39);
            vec2 velocity = vec2(side * (12.0 + 11.5 * lane), 6.0 * lane - 10.5);
            vec2 travelled = local - velocity * drift;
            vec2 cell = floor((travelled + lane * 2.0) / 3.4);
            float seed = hash21(cell + 9.0 * lane);
            vec2 dotOrigin = (cell + .5) * 3.4 - lane * 2.0;
            dotOrigin += vec2(seed - .5, fract(seed * 21.0) - .5) * 1.55;
            float density = nameInk(dotOrigin, index);
            float dot = bell(length(travelled - dotOrigin) / (.48 + .28 * seed));
            specks += dot * density * (.52 + .48 * seed);
        }
    }
    float particleLife = alpha * (1.0 - smoothstep(.64,.995,alpha)) * (outward > .5 ? 2.9 : 2.1);
    vec3 color = vec3(.78,.89,1.0) * (letters + specks * particleLife);

    vec2 tip = center + vec2(side * .67, .71) * (radius + 4.0);
    vec2 elbow = origin + vec2(-side * 46.0, -18.0);
    vec2 end = origin + vec2(side * 34.0, -18.0);
    float wire = min(lineSegment(point,tip,elbow), lineSegment(point,elbow,end));
    float light = bell(wire / .74) * .42 + bell(length(point - tip) / 2.55) * .78;
    color += mix(vec3(.38,.59,.90), whiteLight(index), .28) * light * coherent;
    return color;
}

vec3 instrument(vec3 color, vec2 p, vec2 cursor) {
    // One symbol only, anchored to the frame in a dedicated hit area.
    vec2 hand = (p - (vec2(.053, .918) - .5) * ASPECT) * 675.0;
    float alpha = smoothstep(.10, .85, uScene.y);
    float halo = bell(length(hand) / 27.5);
    float circle = 1.0 - smoothstep(.75, 1.65, abs(length(hand) - 19.0));
    float stroke = min(lineSegment(hand, vec2(-8.0, 0.0), vec2(8.0, 0.0)),
                       min(lineSegment(hand, vec2(-8.0, 0.0), vec2(-2.0, 6.0)),
                           lineSegment(hand, vec2(-8.0, 0.0), vec2(-2.0, -6.0))));
    float arrow = 1.0 - smoothstep(.75, 1.60, stroke);
    color *= 1.0 - .54 * halo * alpha;
    color += vec3(.70, .73, .88) * alpha * (circle * (.21 + .37 * uScene.w) + .86 * arrow);
    float drag = length(p - cursor) * 675.0;
    color += hotTint(int(uScene.x + .5)) * (.35 * bell(drag / 2.6) + .075 * bell(drag / 13.5)) * uPointer.w;
    return color;
}

void main() {
    vec2 uv = vUV.st;
    vec2 screen = (uv - .5) * ASPECT;
    vec2 pointer = (uPointer.yz - .5) * ASPECT;
    vec2 world = screen / uCamera.z + uCamera.xy;
    float time = uPointer.x;
    int scene = int(floor(uScene.x + .5));
    vec3 color = nebulaLayer(screen, pointer, scene);
    vec4 motes = texture(sTD2DInputs[0], uv);
    vec2 spread = 1.7 / vec2(1200., 675.);
    float glow = (texture(sTD2DInputs[0], uv + vec2(spread.x, 0)).a +
                  texture(sTD2DInputs[0], uv - vec2(spread.x, 0)).a +
                  texture(sTD2DInputs[0], uv + vec2(0, spread.y)).a +
                  texture(sTD2DInputs[0], uv - vec2(0, spread.y)).a) * .25;
    float visiblePoints = 1.23 * motes.a + .53 * glow;
    vec3 cool = mix(vec3(.115, .29, .68), coolTint(scene), uCamera.w);
    vec3 warm = mix(vec3(.46, .58, .94), hotTint(scene), uCamera.w);
    float skyLight = max(uCamera.w, smoothstep(.43, 1.84, time));
    color += motes.r * (cool * 1.40 + vec3(.11, .12, .17)) * skyLight;
    color += motes.g * (warm * 1.16 + vec3(.055, .040, .070)) * skyLight;
    color += motes.b * vec3(.89, .91, 1.0) * (1.22 * skyLight);

    vec4 bodies[5] = vec4[5](uSun, uMercury, uVenus, uEarth, uMars);
    vec2 disk = turn(.12) * (world - uSun.xy);
    vec2 relativeSun = world - uSun.xy;
    float arcd = length(relativeSun / vec2(1.0, .96));
    float arcMist = bell((arcd - .202) / .033) * (1.0 - bell(disk.y / .039));
    float sideMist = bell((disk.y + .024 * sin(disk.x * 4.7)) / .054) * bell(disk.x / .60);
    color += vec3(.12, .15, .27) * (.47 * arcMist + .13 * sideMist) * (1.0 - uCamera.w) * skyLight;
    color += atlasDial(relativeSun, disk / vec2(1.0, .38), time);
    int hovered = int(floor(uScene.z + .5));
    if (uCamera.w < .63) {
        for (int i = 1; i < 5; ++i) {
            color += planetDial(world, bodies[i], i, time, i == hovered);
        }
    }

    // Draw far side first, non-selected bodies fade as the camera travels.
    for (int layer = 0; layer < 2; ++layer) {
        for (int i = 0; i < 5; ++i) {
            if (i == scene) continue;
            if ((layer == 0 && bodies[i].y >= uSun.y) || (layer == 1 && bodies[i].y < uSun.y)) continue;
            float appear = (1.0 - smoothstep(.05, .76, uCamera.w)) * planetLight(i, time);
            color = bodyLayer(color, world, pointer, bodies[i], i, appear, false, time, visiblePoints);
        }
    }
    if (scene >= 0) color = bodyLayer(color, world, pointer, bodies[scene], scene, 1.0, true, time, visiblePoints);
    // Near-side grains cross the center of the solar disk.
    float foreground = bell(disk.y * 34.0) * bell(disk.x * 4.65) * (1.0 - uCamera.w);
    color += (motes.b * vec3(.85,.89,1.0) + motes.r * vec3(.17,.37,.76)) * foreground * (.95 * skyLight);
    color += openingSignal(relativeSun, time) * (1.0 - uCamera.w);

    if (hovered >= 0) {
        vec4 body = bodies[hovered];
        float d = (length(world - body.xy) - body.z) * 675.0 * uCamera.z;
        float guide = bell((d - 6.0) * .73) * .41;
        color += (hotTint(hovered) + .22) * guide * (1.0 - smoothstep(.10, .69, uCamera.w));
    }
    color *= 1.0 - .30 * smoothstep(.43, 1.05, length(screen));
    color = instrument(color, screen, pointer);
    int label = int(floor(uLabel.x + .5));
    if (label >= 0 && label < 5 && uLabel.y > .015) color += planetCaption(screen, bodies[label], label);
    color += (hash21(floor(uv * vec2(1200.0, 675.0))) - .5) * .005;
    color = min(color, .82) + .18 * (1.0 - exp(-max(color - .82, 0.0) / .18));
    fragColor = TDOutputSwizzle(vec4(clamp(color, 0.0, 1.0), 1.0));
}
