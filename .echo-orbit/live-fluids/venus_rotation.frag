uniform vec4 uMotion; // Time, spin angle, music envelope, nebula opacity.
out vec4 fragColor;

const vec2 ASPECT = vec2(16.0 / 9.0, 1.0);

mat2 turn(float angle) {
    float s = sin(angle), c = cos(angle);
    return mat2(c, s, -s, c);
}

vec2 hash2(vec2 cell) {
    vec3 p = fract(cell.xyx * vec3(.1031, .1030, .0973));
    p += dot(p, p.yzx + 33.33);
    return fract((p.xx + p.yz) * p.zy);
}

float bell(float x) {
    return exp(-x * x);
}

vec3 stars(vec2 screen) {
    vec2 cell = floor(screen * 24.0);
    vec2 fate = hash2(cell + 334.0);
    vec2 point = (fract(screen * 24.0) - mix(vec2(.12), vec2(.88), fate)) / 24.0;
    float radius = mix(.00052, .00145, fate.x * fate.x);
    float light = bell(length(point) / radius) * step(.54, fate.y);
    float shimmer = .83 + .17 * sin(uMotion.x * .71 + 43.0 * fate.x);
    return mix(vec3(.26, .36, .61), vec3(.84, .69, .78), fate.x) * light * shimmer * .44;
}

vec3 driftingDust(vec2 position, float scale, float opacity, float seed) {
    vec2 grid = position * scale;
    vec2 cell = floor(grid);
    vec2 fate = hash2(cell + seed);
    vec2 point = fract(grid) - mix(vec2(.16), vec2(.84), fate);
    float grain = bell(length(point * vec2(.73, 1.15)) / mix(.025, .074, fate.x));
    float sparkle = bell(length(point) / .16) * .085;
    float flicker = .74 + .26 * sin(uMotion.x * (1.1 + fate.x) + 32.0 * fate.y);
    vec3 tint = mix(vec3(.39, .43, .94), vec3(.98, .37, .68), fate.x);
    return tint * (grain + sparkle) * step(.44, fate.y) * opacity * flicker;
}

vec3 nebula(vec2 screen) {
    float time = uMotion.x;
    float pulse = clamp(uMotion.z, 0., 1.);
    vec2 lane = turn(-.31) * screen;
    float side = 2.0 * smoothstep(-.23, .23, lane.x) - 1.0;
    float ridge = lane.y - .067 * sin(lane.x * 6.5 - .35 * time)
                - .019 * sin(lane.x * 14.0 + time * .58);
    float width = .083 + .080 * smoothstep(.15, .75, abs(lane.x));
    float fade = smoothstep(.17, .37, abs(lane.x)) * (1.0 - smoothstep(.53, .91, abs(lane.x)));
    float haze = bell(ridge / width) * fade;
    float loft = bell((ridge - side * .117) / (width * .58)) * fade;
    vec2 flow = vec2(lane.x - side * time * .047, ridge - side * time * .014);

    // Use the existing nebula texture only as density inside two wisps.
    vec2 sampleUV = vec2(.5 + screen.x * .42 + .043 * sin(time * .42),
                         .5 + screen.y * .72 + .030 * sin(lane.x * 7.0 - time * .43));
    vec3 textureColor = texture(sTD2DInputs[1], clamp(sampleUV, .002, .998)).rgb;
    float density = dot(textureColor, vec3(.24, .58, .18));
    vec3 tint = mix(vec3(.38, .17, .46), vec3(.68, .25, .48), .5 + .5 * side);
    vec3 gas = tint * (pow(density, 1.4) * .42 + .019) * (haze + .29 * loft);
    vec3 grains = driftingDust(flow, 66.0, .56 * haze + .62 * loft, 37.0);
    grains += driftingDust(flow * vec2(.82, 1.0) + vec2(.028 * time, .007 * time),
                          32.0, haze * .64, 572.0);
    return stars(screen) + (gas + grains) * uMotion.w * (.76 + .38 * pulse);
}

vec3 feedbackInk(vec2 point) {
    vec2 textureUV = .5 + point * vec2(.169, .300);
    return texture(sTD2DInputs[0], textureUV).rgb;
}

vec3 revolvingSurface(vec3 normal) {
    // Both projections are continuous across the object poles. The chart and its
    // folds turn in object space; the light stays in camera space.
    vec3 body = normal;
    body.xy = turn(.26) * body.xy;
    body.xz = turn(uMotion.y) * body.xz;
    body.yz = turn(-.18) * body.yz;
    vec2 front = vec2(.88 * body.x + .20 * body.y * body.z,
                      .85 * body.y + .20 * body.z);
    vec2 rear = vec2(.84 * body.x - .19 * body.y * body.z,
                     .78 * body.y - .28 * body.z + .075 * body.x);
    vec3 ink = mix(feedbackInk(rear), feedbackInk(front), smoothstep(-.30, .40, body.z));

    float fold = body.y + .38 * body.x - .18 * body.z
               + .135 * sin(3.8 * body.x + 2.7 * body.z)
               + .064 * sin(6.9 * body.x - 4.1 * body.z);
    float warm = max(ink.r - ink.b * .72, 0.);
    float belt = bell((fold - .04) / .285);
    float seam = bell((fold + .10) / .034) + .46 * bell((fold - .08) / .052);
    vec3 color = mix(ink, vec3(1., .25, .093), belt * .25 * warm);
    color += vec3(.49, .12, .15) * seam * (.13 + .27 * warm);
    // A localized fold gives the eye one strand to follow over the limb.
    float longitude = dot(body, normalize(vec3(-.56, .19, .79)));
    float crest = smoothstep(.14, .88, longitude) * bell((fold - .09) / .067);
    color = mix(color, vec3(.94, .52, .68), .48 * crest);
    return color;
}

void main() {
    vec2 screen = (vUV.st - .5) * ASPECT;
    vec3 color = nebula(screen);
    float pulse = clamp(uMotion.z, 0., 1.);
    float radius = .315 * (1.0 + .019 * pulse);
    vec2 q = screen / radius;
    float r = length(q);
    if (r < 1.15) {
        float angle = atan(q.y, q.x);
        float fold = .008 * sin(5.0 * angle + uMotion.y * 1.7)
                   + .004 * sin(9.0 * angle - uMotion.x * 1.1);
        float edge = r - 1.0 - fold;
        float mask = 1.0 - smoothstep(-.003, .004, edge);
        vec3 n = normalize(vec3(q, sqrt(max(.001, 1.0 - r * r))));
        vec3 ink = revolvingSurface(n);
        vec3 light = normalize(vec3(-.63, .63, .59));
        float diffuse = smoothstep(-.62, .87, dot(n, light));
        float shade = .25 + .76 * diffuse;
        float fresnel = pow(1.0 - n.z, 2.75);
        float glint = pow(max(0., dot(n, normalize(light + vec3(0., 0., 1.)))), 21.);
        vec3 atmosphere = mix(vec3(.21, .14, .80), vec3(.14, .67, .97),
                              smoothstep(-.65, .90, dot(n, light)));
        vec3 surface = ink * shade + vec3(.094, .04, .076) * glint;
        surface += atmosphere * fresnel * (.23 + .40 * diffuse);
        color = mix(color, surface, mask);

        float haze = bell(max(edge, 0.) / .035) * (1.0 - mask);
        float flare = .45 + .55 * pow(.5 + .5 * sin(3.0 * angle - uMotion.y), 3.0);
        color += atmosphere * haze * flare * (.10 + .075 * pulse);
    }
    fragColor = TDOutputSwizzle(vec4(clamp(color, 0., 1.), 1.));
}
