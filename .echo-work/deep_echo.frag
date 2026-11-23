// Deep Echo | procedural stellar atlas, TouchDesigner GLSL TOP
uniform vec4 uClockPointer;
uniform vec4 uPulse;
uniform vec4 uFlags;
uniform vec4 uRoute;
uniform vec4 uMusic;
out vec4 fragColor;

const float ratio = 1200.0 / 675.0;
const vec2 aspect = vec2(ratio, 1.0);
const vec2 beacons[3] = vec2[3](vec2(.39, .43), vec2(.63, .66), vec2(.82, .39));

float hash21(vec2 p) {
    vec3 a = fract(p.xyx * vec3(.1031, .11369, .13787));
    a += dot(a, a.yzx + 19.19);
    return fract((a.x + a.y) * a.z);
}

float valueNoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f*f*(3.0-2.0*f);
    return mix(mix(hash21(i), hash21(i+vec2(1,0)), f.x),
               mix(hash21(i+vec2(0,1)), hash21(i+1.0), f.x), f.y);
}

float clouds(vec2 p) {
    const mat2 turn = mat2(.84, .54, -.54, .84);
    float v = 0.0, a = .52;
    for (int k = 0; k < 6; k++) {
        v += a * valueNoise(p);
        p = turn * p * 2.09 + vec2(31.7, -9.4);
        a *= .49;
    }
    return v;
}

float gaussian(float x) { return exp(-x*x); }
float ring(float d, float r, float w) {
    return 1.0 - smoothstep(w, w+.0016, abs(d-r));
}
float segment(vec2 p, vec2 a, vec2 b) {
    vec2 ab = b-a;
    return length(p - (a+ab*clamp(dot(p-a, ab)/max(dot(ab,ab),.00001),0.,1.)));
}

vec3 stars(vec2 p, float freq, float threshold, float size, float time) {
    vec2 cell = floor(p*freq);
    vec2 v = fract(p*freq);
    float id = hash21(cell+vec2(14.9,42.7));
    vec2 at = .20+.60*vec2(hash21(cell+5.9),hash21(cell+17.1));
    vec2 q = (v-at)/freq*675.;
    float d = length(q);
    float power = smoothstep(threshold,1.,id);
    float sharp = exp(-d*d/(size*size)) + .10*exp(-d/(size*2.2));
    float flares = exp(-abs(q.x)*4.-abs(q.y)/3.) + exp(-abs(q.y)*4.-abs(q.x)/3.);
    float sparkle = .89+.11*sin(time*.65+id*100.);
    vec3 tint = mix(vec3(.42,.68,.83),vec3(.98,.88,.74),hash21(cell+39.1));
    return tint * power * sparkle * (sharp + .13*flares*step(.985,id));
}

vec3 scene(vec2 uv, float time, vec2 mouse, float hover, float charge) {
    vec2 p = uv*aspect;
    vec2 md = p-mouse;
    float distM = length(md);
    float cover = exp(-dot(md,md)/.017)*hover;
    vec2 w = p - md*cover*(.33+.32*charge);
    // Slanted dust sheet, with independent longitudinal and transverse turbulence.
    vec2 spine = normalize(vec2(.72,.69));
    vec2 flank = vec2(-spine.y,spine.x);
    vec2 c = w-vec2(1.075,.56);
    float along = dot(c,spine), across = dot(c,flank);
    vec2 field = vec2(along,across);
    vec2 drift = vec2(time*.0035,-time*.0017);
    float bend = clouds(vec2(along*2.1,across*1.25)+vec2(9.18,5.14)+drift);
    float twist = clouds(field*3.1+vec2(3.3,18.6)-drift*.5);
    float axis = across+.105*sin(along*5.1+.7)+.22*(bend-.52);
    vec2 turbulence = vec2(bend-.5,twist-.5);
    vec2 cr = field*vec2(3.3,5.8)+vec2(6.7,9.1)+turbulence*2.95+drift;
    float rolls = clouds(cr);
    float fray = clouds(cr*1.56+vec2(rolls*2.2,twist*1.65)+vec2(25.4,7.2));
    float curl = (rolls-.5)*.28 + (fray-.5)*.13;
    float lane = axis + curl;
    float span = exp(-abs(along+.018)*1.04);
    float layer = gaussian((lane-.042)/.233)*span;
    float dust = smoothstep(.29,.76,rolls*.62 + fray*.38);
    float folds = .4+.6*fray;
    float sheet = layer*dust*folds;
    float edge = gaussian((lane-.032)/.074)*(.32+1.10*dust);
    float blue = gaussian((lane-.17)/.18)*(.33+.80*dust)*span;
    float body = gaussian((along-.012)/.31)*gaussian((lane-.026)/.096);
    float vein = gaussian((lane-.019+(fray-.5)*.13)/.016);
    float stria = pow(1.-abs(sin((rolls*.75+fray*.25)*22.+along*2.1)),3.);
    float mantle = gaussian((lane+.125)/.095)*smoothstep(.29,.62,rolls);
    float selfShadow = 1.-.83*mantle;
    float micro = valueNoise(cr*56.0+37.);
    float grit = .90+.17*micro;
    float hoverFilament = cover*(.30+.70*charge);
    vec3 color = vec3(.006,.014,.025);
    color += vec3(.020,.052,.079) * (.3+.7*bend);
    color += vec3(.025,.132,.218)*blue;
    color += vec3(.10,.46,.53)*sheet*selfShadow;
    color += vec3(.18,.48,.48)*edge*span*(.14+.50*dust)*grit;
    color += vec3(.45,.59,.52)*body*(.14+1.52*pow(dust,1.3))*(.8+.9*fray)*grit;
    color += vec3(.45,.32,.17)*vein*(.13+.75*body)*dust*span;
    color += vec3(.075,.17,.16)*stria*layer*edge*(.4+hoverFilament*2.);
    float ember = body*smoothstep(.45,.72,dust)*(.42+.58*vein);
    color += vec3(.34,-.042,-.105)*ember;
    color *= mix(.79,1.,selfShadow);
    float thinDust = clouds(field*vec2(6.,11.)+turbulence*5.+vec2(40.3,8.2));
    float cirrus = smoothstep(.50,.78,thinDust)*gaussian((lane+.18)/.19)*span;
    color += vec3(.075,.118,.16)*cirrus;
    // A diffuse second cloud provides depth beyond the main dust lane.
    vec2 shelf = (w-vec2(1.51,.20))/vec2(.43,.17);
    float echo = exp(-dot(shelf,shelf)) * smoothstep(.40,.79,thinDust);
    color += vec3(.065,.15,.23)*echo;
    color += vec3(.11,.32,.32)*hoverFilament*layer*(.2+.8*stria);
    vec3 highlights = max(color-.76,vec3(0.));
    color = min(color,vec3(.76))+.24*(1.-exp(-highlights/.24));
    color *= mix(.41,1.,smoothstep(.16,.39,uv.x));
    vec3 star = stars(p+3.9,193.,.970,.60,time)*.73 +
                stars(p+5.1,79.,.928,.85,time)*.79 +
                stars(p+7.1,28.,.943,1.15,time)*1.03;
    color += star*(1.-.44*sheet)*mix(.42,1.,smoothstep(.17,.36,uv.x));
    // Sparse foreground suns punctuate the smaller stars in the distant sheet.
    vec2 suns[3]=vec2[3](vec2(.773,.76),vec2(.462,.258),vec2(.924,.531));
    for(int j=0;j<3;j++) {
        vec2 z=(uv-suns[j])*aspect*675.;
        float dd=length(z), weight=.66+.2*float(j);
        float spikes=exp(-abs(z.x)*2.6-abs(z.y)/3.)+exp(-abs(z.y)*2.6-abs(z.x)/4.3);
        vec3 st = j==1 ? vec3(.85,.70,.55) : vec3(.60,.77,.87);
        color += st*weight*(.91*exp(-dd*dd/1.18)+.22*spikes+.16*exp(-dd/4.));
    }
    return color;
}

float planetHash(vec3 p) {
    p = fract(p * vec3(.1031, .1030, .0973));
    p += dot(p, p.yxz + 33.33);
    return fract((p.x + p.y) * p.z);
}

float planetNoise(vec3 p) {
    vec3 i = floor(p), f = fract(p);
    f = f*f*(3.-2.*f);
    vec2 low = mix(vec2(planetHash(i), planetHash(i+vec3(0,1,0))),
                   vec2(planetHash(i+vec3(1,0,0)), planetHash(i+vec3(1,1,0))), f.x);
    vec2 high = mix(vec2(planetHash(i+vec3(0,0,1)), planetHash(i+vec3(0,1,1))),
                    vec2(planetHash(i+vec3(1,0,1)), planetHash(i+vec3(1,1,1))), f.x);
    return mix(mix(low.x, low.y, f.y), mix(high.x, high.y, f.y), f.z);
}

float planetTerrain(vec3 p) {
    return .54*planetNoise(p) + .26*planetNoise(p*2.07+vec3(7,2,11)) +
           .13*planetNoise(p*4.23+vec3(3,8,4)) + .07*planetNoise(p*8.59+10.);
}

mat2 planetTurn(float angle) {
    float c = cos(angle), s = sin(angle);
    return mat2(c,s,-s,c);
}

vec3 planetLayer(vec3 background, vec2 uv, vec2 pointer) {
    const float radius = .160;
    vec2 q = (uv-vec2(.84,.68))*aspect/radius;
    float d = length(q);
    if (d > 1.15) return background;

    pointer = clamp(pointer, 0., 1.);
    vec2 lightPan = (pointer-vec2(.69,.425))*vec2(2.75,2.42);
    vec3 light = normalize(vec3(lightPan + vec2(-.24,.36), .61));
    vec2 limb = q/max(d,.0001);
    float haloLight = .09+.91*smoothstep(-.34,.83,dot(limb,light.xy));
    float halo = exp(-max(0.,d-1.)*48.)*(1.-smoothstep(1.08,1.15,d));
    background += vec3(.066,.36,.52)*haloLight*halo*.53;
    float scanOffset = length((uv-uPulse.xy)*aspect)-uPulse.z;
    float scanLight = uPulse.w*exp(-abs(scanOffset+.014)*39.);
    background += vec3(.24,.10,.023)*scanLight*halo;
    if (d > 1.010) return background;

    vec3 normal = vec3(q*min(1.,1./max(d,.0001)), sqrt(max(0.,1.-d*d)));
    vec3 terrain = normal;
    terrain.xz = planetTurn((pointer.x-.62)*4.5+.26)*terrain.xz;
    terrain.yz = planetTurn((.5-pointer.y)*2.85-.12)*terrain.yz;

    vec3 warp = vec3(planetNoise(terrain*3.1+vec3(1,7,0)),
                     planetNoise(terrain*3.4+vec3(7,2,3)),
                     planetNoise(terrain*3.2+vec3(2,4,8))) - .5;
    vec3 ground = terrain*4.1 + warp*1.65 + vec3(8,2,11);
    float rock = planetTerrain(ground);
    float channels = planetTerrain(ground*2.85+vec3(7,3,9));
    float flecks = planetNoise(ground*18.2);
    // Large, fixed ridges and a flooded impact basin carry the rotation visually.
    float ridge = gaussian(dot(terrain, normalize(vec3(.86,.37,-.12))) * 3.6);
    float height = rock+.16*ridge-.06;
    float basinDist = length(terrain-normalize(vec3(.60,.35,.91)));
    float basin = 1.-smoothstep(.105,.31,basinDist+.055*(channels-.5));
    height -= .22*basin;
    float basinRim = gaussian((basinDist-.265)*24.)*(.23+.77*channels);
    float land = smoothstep(.465,.525,height);
    float shoals = gaussian((height-.477)*30.);
    vec3 water = mix(vec3(.035,.13,.19),vec3(.11,.39,.44),smoothstep(.34,.66,channels));
    water += vec3(.04,.18,.17)*shoals;
    vec3 stone = mix(vec3(.33,.20,.135),vec3(.73,.49,.29),smoothstep(.50,.77,height));
    stone *= .68+.56*channels;
    stone += vec3(.36,.26,.16)*basinRim;
    vec3 albedo = mix(water,stone,land)*(.91+.16*flecks);
    vec3 weather = terrain*vec3(4.5,12.,4.5)+warp*2.15+vec3(14,3,6);
    float cloud = smoothstep(.51,.74,planetTerrain(weather));
    float fineCloud = smoothstep(.43,.72,planetNoise(weather*2.35));
    albedo = mix(albedo,vec3(.69,.76,.73), cloud*(.23+.52*fineCloud));

    float diffuse = dot(normal,light);
    float daylight = smoothstep(-.09,.52,diffuse);
    float warmth = gaussian((diffuse-.08)*5.2);
    vec3 day = albedo*(vec3(.165,.23,.30) + (.74*daylight+.25*max(diffuse,0.))*vec3(1.04,.95,.83));
    day += albedo*vec3(.16,.075,.012)*warmth;
    vec3 halfAngle = normalize(light+vec3(0,0,1));
    float reflection = pow(max(dot(normal,halfAngle),0.),30.)*(1.-land)*(1.-cloud)*daylight;
    day += vec3(.086,.19,.225)*reflection;
    float atmosphere = exp(-normal.z*5.5)*(.13+.87*smoothstep(-.22,.53,diffuse));
    day += atmosphere*vec3(.24,.73,.88);
    day += scanLight*vec3(.25,.125,.045)*(.30+.33*normal.z+.27*land+.41*atmosphere);
    float edge = 1.-smoothstep(.994,1.006,d);
    return mix(background,day,edge);
}

vec3 beaconMark(vec2 q, float found, float n, float time, float pulseLight) {
    float d = length(q);
    vec2 a = abs(q);
    float core = exp(-d*d/.000005);
    float hazy = exp(-d/.012);
    float arm = (1.-smoothstep(.0005,.0019,min(a.x,a.y)))*
                smoothstep(.005,.008,max(a.x,a.y))*(1.-smoothstep(.012,.014,max(a.x,a.y)));
    float diamond = abs(a.x+a.y-.015);
    float notch = (1.-smoothstep(.0005,.0019,diamond))*smoothstep(.0031,.007,max(a.x,a.y)-min(a.x,a.y));
    float angle = atan(q.y,q.x);
    float arcs = ring(d,.024,.00042)*smoothstep(.22,.36,cos(angle*4.+.5));
    float live = .7+.3*sin(time*1.45+n*2.7);
    vec3 cold = vec3(.30,.68,.72);
    vec3 amber = vec3(1.,.64,.24);
    return cold*(1.-found)*(.54*core+.21*hazy+.32*arm+.15*notch+.15*pulseLight*arcs) +
           amber*found*(core+.32*hazy+.86*notch+.74*arcs+.52*arm+.22*live*ring(d,.030+.004*live,.0005));
}

vec3 beaconLabel(vec3 color, vec2 q, int id) {
    // Instrument lettering in reference-canvas pixels; upper-right of the crosshair.
    vec2 g=q*675.-vec2(24.,8.);
    if (any(lessThan(g,vec2(-3.))) || any(greaterThan(g,vec2(11.,14.)))) return color;
    float d;
    if (id==0) {
        d=min(segment(g,vec2(0.,0.),vec2(3.7,10.5)),segment(g,vec2(3.7,10.5),vec2(7.4,0.)));
        d=min(d,segment(g,vec2(1.55,4.1),vec2(5.85,4.1)));
    } else if (id==1) {
        d=segment(g,vec2(0.,0.),vec2(0.,10.5));
        d=min(d,segment(g,vec2(0.,10.5),vec2(5.,10.5)));
        d=min(d,segment(g,vec2(5.,10.5),vec2(7.1,8.3)));
        d=min(d,segment(g,vec2(7.1,8.3),vec2(6.8,6.9)));
        d=min(d,segment(g,vec2(6.8,6.9),vec2(5.,5.5)));
        d=min(d,segment(g,vec2(0.,5.5),vec2(5.,5.5)));
        d=min(d,segment(g,vec2(5.,5.5),vec2(7.2,3.9)));
        d=min(d,segment(g,vec2(7.2,3.9),vec2(7.2,2.1)));
        d=min(d,segment(g,vec2(7.2,2.1),vec2(5.,0.)));
        d=min(d,segment(g,vec2(5.,0.),vec2(0.,0.)));
    } else {
        d=segment(g,vec2(7.4,9.1),vec2(5.6,10.5));
        d=min(d,segment(g,vec2(5.6,10.5),vec2(2.3,10.5)));
        d=min(d,segment(g,vec2(2.3,10.5),vec2(0.,8.2)));
        d=min(d,segment(g,vec2(0.,8.2),vec2(0.,2.3)));
        d=min(d,segment(g,vec2(0.,2.3),vec2(2.3,0.)));
        d=min(d,segment(g,vec2(2.3,0.),vec2(5.6,0.)));
        d=min(d,segment(g,vec2(5.6,0.),vec2(7.4,1.5)));
    }
    color=mix(color,vec3(.045,.061,.072),.80*(1.-smoothstep(1.05,2.0,d)));
    return mix(color,vec3(.99,.86,.64),1.-smoothstep(.46,1.25,d));
}

void main() {
    vec2 uv = vUV.st, p = uv*aspect;
    float t = uClockPointer.x;
    vec2 mouse = uClockPointer.yz*aspect;
    float hover = clamp(uClockPointer.w,0.,1.), charge = clamp(uFlags.w,0.,1.);
    vec3 color = planetLayer(scene(uv,t,mouse,hover,charge),uv,uClockPointer.yz);
    float scanDist = length(p-uPulse.xy*aspect), radius = uPulse.z;
    float scan = uPulse.w;
    vec3 amber = vec3(1.,.54,.16);
    float diff = scanDist-radius;
    float trail = exp(-abs(diff+.012)*67.)*step(diff,0.);
    float primary = ring(scanDist,radius,.0012);
    float secondary = ring(scanDist,max(0.,radius-.013),.0004);
    color += amber*scan*(primary*.98+secondary*.28+trail*.12);
    for(int k=0;k<3;k++) {
        vec2 q = p-beacons[k]*aspect;
        color += beaconMark(q,uFlags[k],float(k),t,scan*exp(-abs(diff)*4.));
        float note = clamp(uMusic[k],0.,1.);
        float d = length(q);
        float wave = ring(d,.024+.072*(1.-note),.0007);
        color += vec3(1.,.71,.31)*note*(1.5*wave+.64*exp(-d/.035)+.78*exp(-d*d/.000053));
    }
    vec2 ordered[3];
    for(int k=0;k<3;k++) ordered[k] = beacons[clamp(int(floor(uRoute[k]+.5)),0,2)]*aspect;
    float routeGlow=0.;
    for(int k=0;k<2;k++) {
        if(uRoute[k+1]>-.5) {
            float d = segment(p,ordered[k],ordered[k+1]);
            routeGlow = max(routeGlow,(1.-smoothstep(.0005,.0021,d))*.64+.14*exp(-d*105.));
        }
    }
    color += amber*routeGlow;
    if(uRoute.z>-.5) {
        float firstDistance = length(ordered[1]-ordered[0]);
        float whole = firstDistance+length(ordered[2]-ordered[1]);
        float travel = clamp(uRoute.w,0.,1.)*whole;
        vec2 a = travel<firstDistance ? ordered[0] : ordered[1];
        vec2 b = travel<firstDistance ? ordered[1] : ordered[2];
        vec2 dir = normalize(b-a+vec2(.00001));
        vec2 tip = a+dir*(travel<firstDistance ? travel : travel-firstDistance);
        float tail = segment(p,tip,tip-dir*.032);
        float head = length(p-tip);
        color += vec3(1.,.80,.43)*(exp(-head*head/.000019)+.55*exp(-head/.012)+.8*exp(-tail*tail/.000004));
    }
    float md = length(p-mouse);
    float reticle = ring(md,.012+.007*charge,.00065);
    color += vec3(.41,.77,.78)*hover*.58*reticle;
    color += amber*charge*(.45*exp(-md/.045)+1.6*exp(-md*md/(.00004+.00016*charge))+
                .68*ring(md,.022+.034*charge,.00085));
    for (int k=0;k<3;k++) {
        if (uFlags[k]>.5) color=beaconLabel(color,p-beacons[k]*aspect,k);
    }
    float vignette = 1.-.22*smoothstep(.38,1.06,length((uv-.5)*vec2(1.14,1.)));
    color *= vignette;
    color += (hash21(floor(p*675.))-.5)*.008;
    fragColor = TDOutputSwizzle(vec4(clamp(color,0.,1.),1.));
}
