// Portrait gas and distant stars. Interactive dust is composited in solar_atlas.
uniform vec4 uPointer;
uniform vec4 uAudio;
uniform vec4 uScene;

out vec4 fragColor;

float hash(vec2 cell) {
    vec3 p = fract(cell.xyx * vec3(.1031,.1030,.0973));
    p += dot(p,p.yzx + 33.33);
    return fract((p.x + p.y)*p.z);
}

float noise(vec2 p) {
    vec2 cell = floor(p);
    vec2 f = fract(p);
    f = f*f*(3.-2.*f);
    return mix(mix(hash(cell),hash(cell+vec2(1.,0.)),f.x),
               mix(hash(cell+vec2(0.,1.)),hash(cell+vec2(1.,1.)),f.x),f.y);
}

mat2 turn(float angle) {
    return mat2(cos(angle),sin(angle),-sin(angle),cos(angle));
}

float bell(float x) {
    return exp(-x*x);
}

vec3 ribbon(vec2 lane, float width, float reach, float phase, vec3 shade, vec3 light) {
    float end = 1.-smoothstep(reach*.63,reach,abs(lane.x));
    if (end < .002 || abs(lane.y) > width*2.85) return vec3(0.);
    vec2 q = vec2(lane.x*15. - phase, lane.y*27.);
    float curl = noise(q*.55 + 7.);
    q.y += (curl-.5)*1.35 + .24*sin(q.x*1.26);
    q.x += .61*sin(q.y*.49 + phase*.2);
    float large = noise(q*.76);
    float grain = noise(turn(.23)*q*2.1 + 21.);
    float flecks = noise(turn(-.33)*q*4.65 + 37.);
    float fine = noise(vec2(q.x*7.2,q.y*12.5) + 63.);
    float strands = noise(vec2(q.x*5.8+.84*flecks,q.y*21.+.92*grain) + 97.);
    float mass = .55*large + .25*grain + .13*flecks + .07*fine;
    float cut = smoothstep(.34,.59,mass);
    float contour = grain-.51 + .24*(large-.5) + .21*(flecks-.5) + .11*(fine-.5);
    float brokenEdge = 1.-smoothstep(.033,.18,abs(contour));
    float striation = smoothstep(.39,.77,.58*strands+.27*fine+.15*flecks);
    float thread = brokenEdge*(.26+.55*striation) + .46*striation;
    float edge = bell((abs(lane.y+(curl-.5)*width*.63)-width*.53)/(width*.66));
    float envelope = end * bell(lane.y/width);
    vec3 body = shade * (.05+.40*cut+.09*striation) * envelope;
    vec3 filaments = light * thread * cut * edge * envelope * (.18+.22*flecks+.12*fine);
    return body + filaments;
}

vec3 cloud(vec2 point, int scene, float time) {
    if (scene == 0) {
        float angle = atan(point.y,point.x);
        float radius = length(point);
        float sweep = angle - .21*time;
        float arms = .45+.55*pow(.5+.5*sin(2.*sweep+.7),2.);
        float flare = .307+.054*sin(2.*sweep)+.022*uAudio.x;
        return ribbon(vec2(radius*.75-.23, radius-flare),.082,.33,
                      time*.37+2.2*sin(sweep),vec3(.69,.15,.063),vec3(1.,.56,.21))*arms;
    }
    if (scene == 1) {
        vec2 p = turn(-1.05)*(point+vec2(.055,.043));
        float wake = p.y-.052*sin(5.*p.x-.22*time);
        float width = mix(.045,.106,smoothstep(-.33,.53,p.x));
        return ribbon(vec2(p.x-.065,wake),width,.64,time*.57,
                      vec3(.10,.19,.53),vec3(.36,.62,1.));
    }
    if (scene == 2) {
        vec2 p = turn(-.76)*point;
        float curved = p.y+.10*sin(p.x*5.1-.20*time);
        return ribbon(vec2(p.x+.12,curved-.11),.101,.64,time*.51,
                      vec3(.38,.087,.27),vec3(.93,.30,.54)) +
               ribbon(vec2(p.x-.11,curved+.12),.077,.62,-time*.41+21.,
                      vec3(.21,.085,.40),vec3(.52,.32,.91));
    }
    if (scene == 3) {
        // Opposing drifts expose dark lanes between two narrow cloud sheets.
        vec2 p = turn(-1.02)*point;
        float a = p.y - .091 - .048*sin(5.7*p.x-.20*time) - .013*sin(15.*p.x+.39*time);
        float b = p.y + .144 - .036*sin(6.4*p.x+.18*time);
        return ribbon(vec2(p.x-.045,a),.074,.66,time*.42,
                      vec3(.052,.40,.44),vec3(.23,.97,.89)) +
               ribbon(vec2(p.x+.075,b),.062,.59,-time*.29+17.,
                      vec3(.068,.18,.42),vec3(.31,.61,.96));
    }
    vec2 p = turn(1.02)*point;
    float fork = .075 + .17*smoothstep(-.29,.51,p.x);
    float arc = .055*sin(p.x*6.+.24*time);
    return ribbon(vec2(p.x-.036,p.y-fork-arc),.079,.62,time*.62,
                  vec3(.54,.13,.109),vec3(.99,.44,.29)) +
           ribbon(vec2(p.x+.035,p.y+fork*.66-arc),.057,.56,time*.38+29.,
                  vec3(.34,.062,.18),vec3(.81,.25,.47));
}

vec3 stars(vec2 point, float scale, float seed, float gain, float time) {
    vec2 grid = point*scale;
    vec2 cell = floor(grid);
    float fate = hash(cell+seed);
    if (fate < .56) return vec3(0.);
    vec2 center = vec2(hash(cell+seed+17.),hash(cell+seed+39.));
    vec2 d = (fract(grid)-mix(vec2(.17),vec2(.83),center))*1280./scale;
    float radius = mix(.54,1.24,pow(center.x,2.6));
    float twinkle = .85 + .15*sin(time*(.30+.39*center.y)+fate*38.);
    vec3 tint = mix(vec3(.43,.57,.91),vec3(.94,.83,.73),center.x);
    float light = bell(length(d)/radius)*(fate-.52)*gain*twinkle;
    return tint*light;
}

void main() {
    int scene = int(floor(uScene.x + .5));
    if (scene < 0 || scene > 4) {
        fragColor = TDOutputSwizzle(vec4(0.,0.,0.,1.));
        return;
    }
    vec2 aspect = vec2(9./16.,1.);
    vec2 screen = (vUV.st-.5)*aspect;
    vec2 cursor = (uPointer.yz-.5)*aspect;
    float time = uPointer.x;
    float energy = .90+.16*uAudio.y+.09*uAudio.w;
    vec2 delta = screen-cursor;
    vec2 field = screen+.014*(cursor-screen)*bell(length(delta)/.25)*uPointer.w;
    vec3 gas = cloud(field,scene,time)*energy;
    vec3 dust = stars(screen,86.,8.,.28,time) + stars(screen,38.,91.,.59,time);
    float title = bell(screen.x/.145)*smoothstep(.325,.476,screen.y);
    vec3 color = (gas+dust)*(1.-.72*title);
    fragColor = TDOutputSwizzle(vec4(clamp(color,0.,1.),1.));
}
