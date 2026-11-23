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

uniform vec4 uTransition;

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

vec3 wakeTint(int id);

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
    float gradeAmount = .81;

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
    vec3 theme = wakeTint(scene);
    vec3 deep = mix(coolTint(scene),theme,.47);
    vec3 lit = mix(theme, normalize(theme+.36), smoothstep(.48,.92,light)*.55);
    vec3 graded = mix(footage, mix(deep,lit,smoothstep(.05,.54,light))*light*1.62, gradeAmount);
    graded *= (.73 + .27 * smoothstep(.016, .36, light)) * (.89 + .23 * uAudio.y * uScene.y);
    graded += tint * max(0.0, light - .20) * (.06 + .13 * uAudio.w * uScene.y);
    return vec3(.0015, .0016, .0032) + graded * envelope * feather * .67 * smoothstep(.07, .94, detail);
}
vec3 whiteLight(int id) {
    if (id == 0) return vec3(1.00, .825, .62);
    if (id == 1) return vec3(.80, .88, 1.00);
    if (id == 2) return vec3(1.00, .872, .75);
    if (id == 3) return vec3(.74, .94, 1.00);
    return vec3(1.00, .74, .68);
}

const vec3 BLACK = vec3(.004,.006,.012);
vec3 thermalColor(float r) {
    vec3 color=mix(vec3(1.,.302,.039),vec3(1.,.761,.145),smoothstep(.34,.51,r));
    color=mix(color,vec3(.522,.831,.286),smoothstep(.545,.705,r));
    color=mix(color,vec3(.082,.620,.612),smoothstep(.69,.86,r));
    return mix(color,vec3(.106,.318,.561),smoothstep(.865,1.07,r));
}

vec3 solarCorona(vec2 p,float time) {
    float r=length(p);
    float angle=atan(p.y,p.x);
    vec3 energy=vec3(0.);
    const float bound=1.14;
    if (r<bound) {
        float depth=sqrt(bound*bound-r*r);
        float dz=2.*depth/48.;
        float transmission=1.;
        for (int j=0;j<48;j++) {
            float z=depth-(float(j)+.5)*dz;
            vec3 w=vec3(p,z);
            float radial=length(w*vec3(1.,1.,.88));
            // Slow curls bend the thermal layers without disconnecting the core.
            float curl=sin(8.*w.y+5.*w.x+3.*z+.88*time);
            curl += .63*sin(7.*w.x-5.*z-.57*time+1.4*sin(9.*w.y));
            radial+=.028*curl*smoothstep(.21,.81,radial);
            float density=(.31+1.23*exp(-7.3*radial*radial))*(1.-smoothstep(.90,1.11,radial));
            float folds=.88+.12*sin(12.*w.x-8.*w.y+4.*z+.58*time);
            float emission=folds*(.74+.28*exp(-4.6*radial*radial));
            emission*=.93-.12*w.x+.12*w.y+.09*z;
            energy+=transmission*thermalColor(radial)*density*emission*dz;
            transmission*=exp(-.33*dz*density);
        }
    }
    float phase=angle+.027*sin(time*.6);
    float direction=floor(phase/1.04719755+.5);
    float rayAngle=phase-direction*1.04719755;
    float offset=r*abs(sin(rayAngle));
    float width=.012+.020*exp(-.66*r);
    float beam=exp(-pow(offset/width,1.50));
    float scattering=.42*exp(-pow(offset/(3.4*width),1.40));
    float strength=.78+.22*cos(direction*2.22+.46);
    float rayFalloff=exp(-.77*r-.14*r*r)*smoothstep(.16,.46,r);
    float spectrum=.27+.57*r;
    vec3 rayColor=thermalColor(spectrum);
    rayColor=mix(rayColor,vec3(.082,.620,.612),.59*smoothstep(.93,1.65,r));
    energy+=(beam+scattering)*rayFalloff*strength*.52*rayColor;
    vec2 drift=p+vec2(.065,-.042);
    float halo=exp(-1.27*dot(drift,drift));
    float fog=halo*(.068+.033*sin(2.*angle+.45)*smoothstep(.2,.7,r));
    vec3 atmospheric=mix(vec3(.106,.318,.561),vec3(.082,.620,.612),exp(-5.8*(r-.73)*(r-.73))*.50);
    energy+=fog*atmospheric;
    float peak=max(energy.r,max(energy.g,energy.b));
    vec3 corona=energy/(.83+.30*peak);
    float ripple=.017*sin(5.*angle+.67*time)*smoothstep(.10,.38,r);
    float core=1.-smoothstep(.21,.54,r+ripple);
    float heat=.93+.043*cos(5.3*p.x+3.9*p.y-.66*time);
    return BLACK+mix(corona,heat*vec3(1.,.302,.039),.86*core);
}

vec3 wakeTint(int id) {
    if (id == 0) return vec3(1.0,.255,.043);
    if (id == 1) return vec3(.259,.404,1.0);
    if (id == 2) return vec3(1.0,.149,.663);
    if (id == 3) return vec3(0.,.965,.694);
    return vec3(1.0,.110,.290);
}

vec3 nearWake(vec2 q, vec4 body, int id, float time, float drive) {
    float r=length(q);
    if (r>1.42 || r<.80) return vec3(0.);
    vec2 radial=body.xy-uSun.xy;
    vec2 back=normalize(vec2(radial.y,-radial.x*.72)+vec2(.0001));
    if (id==0) back=vec2(cos(-.66+.24*sin(time*.59)),sin(-.66+.24*sin(time*.59)));
    vec2 side=vec2(-back.y,back.x);
    float along=dot(q,back), span=dot(q,side);
    float roll=time*(.74+.13*float(id));
    float fold=span+.11*sin(4.6*along+roll)+.066*sin(9.2*along-1.28*roll);
    float cloudWidth=.37+.075*sin(6.2*along-.71*roll)+.045*drive;
    float plume=bell((along-1.015-.042*sin(roll))/.30)*bell(fold/cloudWidth);
    float eddy=bell((along-.92)/.26)*bell((span+.23+.08*sin(roll))/.27);
    float contact=smoothstep(.81,1.02,r)*(1.-smoothstep(1.23,1.42,r));
    float turbulent=.74+.26*sin(8.1*span-4.2*along+roll)*sin(5.3*along+1.14*roll);
    return wakeTint(id)*(.38+.25*drive)*(plume+.32*eddy)*contact*turbulent;
}

vec2 flowEddy(vec2 p, vec2 center, float spread, float twist) {
    vec2 delta=p-center;
    return center+turn(twist*exp(-dot(delta,delta)/(spread*spread)))*delta;
}

// Displaced, overlapping shells. Each trace samples a previous phase of the flow.
vec3 beatPigment(int id, int band) {
    if (id==0) {
        vec3 dyes[5]=vec3[5](vec3(1.,.22,.018),vec3(1.,.68,.07),vec3(.55,.98,.10),
                             vec3(.035,.92,.75),vec3(.12,.40,.88));
        return dyes[band];
    }
    if (id==1) {
        vec3 dyes[5]=vec3[5](vec3(.20,.39,1.),vec3(.54,.76,1.),vec3(.044,.91,.84),
                             vec3(.54,.27,1.),vec3(1.,.53,.22));
        return dyes[band];
    }
    if (id==2) {
        vec3 dyes[5]=vec3[5](vec3(1.,.065,.44),vec3(.61,.14,1.),vec3(1.,.43,.20),
                             vec3(1.,.64,.88),vec3(.045,.81,1.));
        return dyes[band];
    }
    if (id==3) {
        vec3 dyes[5]=vec3[5](vec3(.035,.90,.64),vec3(.15,.38,1.),vec3(.75,1.,.15),
                             vec3(.13,.91,1.),vec3(.65,.24,.98));
        return dyes[band];
    }
    vec3 dyes[5]=vec3[5](vec3(1.,.28,.14),vec3(.95,.08,.40),vec3(1.,.65,.20),
                         vec3(.58,.17,.96),vec3(.08,.86,.87));
    return dyes[band];
}

vec2 shellShape(vec2 p, float phase, float push, float id) {
    float angle=atan(p.y,p.x);
    float swell=.025*sin(3.*angle+.65*phase)+.043*sin(5.*angle-.80*phase);
    swell+=.021*sin(11.*angle+1.4*phase);
    float contour=length(p/vec2(.95,1.03))-.987-swell;
    vec2 inlet=p-vec2(.55+.05*sin(phase),.59-.06*push);
    inlet=turn(.32+.32*push)*inlet/vec2(1.03,.95);
    float alcove=length(inlet)-(.485+.071*push+.028*sin(phase+id*.53));
    return vec2(contour,alcove);
}

vec3 beatShell(vec2 q, int scene, vec2 mouse, float time, float spin,
               vec4 signal, float engagement, float pixelRadius) {
    if (length(q)>1.40) return vec3(0.0);
    float id=float(scene);
    float bass=signal.x*engagement;
    float middle=signal.y*engagement;
    float high=signal.z*engagement;
    float attack=signal.w*engagement;
    float t=time*(.53+.08*id)+spin*.35;
    float pulse=.034*sin(2.4*t)+.12*bass+.040*attack;
    vec2 v=turn(-.08+.09*id+.15*sin(.81*t)+.46*mouse.x*engagement)*q/(1.+pulse);
    v.y*=1.+.12*mouse.y*engagement;
    v=flowEddy(v,vec2(-.09,-.13),.65,.58+.21*sin(t)+.47*middle);
    v=flowEddy(v,vec2(.47,.48),.47,-.47+.13*sin(t*.92+id)-.28*bass);
    float a=atan(v.y,v.x);
    float around=smoothstep(.04,.29,length(v));
    vec2 shape=shellShape(v,t,bass,id);
    float boundary=max(shape.x,-shape.y);
    float fine=max(.009,1.20/pixelRadius);
    float silhouette=1.-smoothstep(-fine*.42,fine*1.3,boundary);
    if (boundary>.22) return vec3(0.0);
    float thickness=clamp(-shape.x,.0,1.);
    float turnIn=smoothstep(-.027,.22,shape.y);
    float stream=thickness+.16*around*sin(2.*a+.40*t)
                 +.093*sin(3.0*v.y-2.7*v.x+.63*t)+.118*(1.-turnIn);
    float seam=.031*sin(7.8*v.x+3.9*v.y-t)+.019*sin(10.7*v.y-t*.66);
    stream+=seam;
    vec3 main=beatPigment(scene,0);
    vec3 second=beatPigment(scene,1);
    vec3 third=beatPigment(scene,2);
    vec3 crest=beatPigment(scene,3);
    vec3 lip=beatPigment(scene,4);
    vec3 rim=mix(second,lip,.43+.22*sin(2.*a+.42*t));
    if (scene==2) rim=mix(rim,lip,.53);
    vec3 ink = mix(rim,main,smoothstep(.06,.36,stream));
    float flare=sin(3.2*v.x-4.3*v.y+.43*t+.44*id)+.35*around*sin(3.*a);
    ink=mix(ink,third,.84*smoothstep(.28,1.10,flare)*smoothstep(.26,.58,thickness));
    ink=mix(ink,crest,.48*bell((stream-.245)/.115));
    float shadow=.54+.51*smoothstep(-.92,.91,.59*v.x-.61*v.y-.11*sin(t));
    float innerGlow=.11+.68*smoothstep(.015,.43,thickness);
    ink*=shadow*innerGlow*(1.+.22*bass);

    float ringLine=0., folds=0.;
    int count=pixelRadius<46.?7:20;
    for (int i=0;i<20;i++) {
        if (i>=count) break;
        float life=float(i)/float(count-1);
        float previous=t-life*(1.29+.20*id);
        vec2 flow=turn(-.42*life)*v;
        flow+=vec2(.060*sin(previous+2.*v.y),-.041*cos(previous+2.*v.x))*life;
        flow/=1.-.26*life;
        vec2 outline=shellShape(flow,previous,bass*(1.-life*.48),id);
        float track=abs(max(outline.x,-outline.y));
        float width=max(fine*.47,.006+.009*(.5+.5*sin(a*4.+previous)));
        float torn=.32+.68*smoothstep(-.83,.76,sin(3.*a+.61*previous+life*24.));
        float line=exp(-track/width)*torn*(1.-.43*life);
        ringLine+=line*(1.-.32*life);
        folds+=line*life;
    }
    float filament=(1.-exp(-.88*ringLine))*(.76+.36*high);
    float spectralBreak=.46+.30*sin(4.*a-.44*t+7.*v.y)+.20*high;
    vec3 bright=mix(mix(rim,crest,clamp(spectralBreak,.0,1.)),vec3(.89,.95,1.),.32);
    float fineRib=bell(sin(104.*stream+1.9*sin(11.*a-.61*t))/.35);
    fineRib*=smoothstep(.012,.17,thickness)*(1.-smoothstep(.24,.65,thickness));
    fineRib*=.22+.78*pow(.5+.5*sin(3.9*v.x-3.2*v.y+2.*t),1.8);
    float crestLight=bell(boundary/(.024+.013*bass))*(.40+.43*turnIn);
    float outside=exp(-max(boundary,0.)*33.);
    float liquid=.70+.30*sin(4.*a+6.5*stream-.76*t+sin(9.2*v.y));
    float rollover=bell(boundary/.145)*(.23+.39*liquid)*silhouette;
    vec3 color=(ink*1.14+mix(rim,lip,.56)*rollover)*silhouette;
    color+=bright*(.72*filament+.155*fineRib+.66*crestLight)*outside;
    color+=rim*.085*folds*outside;
    color+=rim*(.09+.09*attack)*bell(boundary/.083);
    float rimGrain=hash21(floor(v*max(65.,pixelRadius*1.37)));
    float shredded=bell(boundary/.032)*pow(rimGrain,5.)*liquid*smoothstep(52.,105.,pixelRadius);
    color+=mix(rim,bright,.6)*shredded*(.79+.55*high);
    return color*(1.-smoothstep(1.27,1.40,length(q)));
}

vec3 bodyLayer(vec3 background, vec2 world, vec2 cursor, vec4 body, int id,
               float visible, bool selected, float time) {
    if (visible<.002) return background;
    float transition=selected?uTransition.x:1.;
    float movement=smoothstep(0.,1.,transition);
    vec2 screen=(world-uCamera.xy)*uCamera.z;
    vec2 center=mix(uTransition.yz,(body.xy-uCamera.xy)*uCamera.z,movement);
    float radius=mix(uTransition.w,body.z*uCamera.z,movement);
    vec2 q=(screen-center)/max(radius,.016);
    float r=length(q);
    if (r>(id==0?2.25:1.42)) return background;
    float engagement=selected?uScene.y:0.;
    float bass=uAudio.x*engagement;
    float scatter=sin(3.14159265*transition);
    visible*=1.-.94*smoothstep(.18,.89,scatter);
    background+=visible*nearWake(q,body,id,time,.82*bass);
    if (id==0) {
        float fade=1.-smoothstep(1.35,2.25,r);
        background+=visible*.28*fade*(solarCorona(q,time+body.w)-BLACK);
    }
    vec3 surface=beatShell(q,id,cursor,time,body.w,uAudio,engagement,radius*675.);
    float peak=max(max(surface.r,surface.g),surface.b);
    return background*(1.-.78*visible*smoothstep(.04,.48,peak))+surface*visible;
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

    float orbitR[4] = float[4](.154, .318, .388, .653);
    for (int i = 0; i < 4; ++i) {
        float rank = float(i);
        float arrived = smoothstep(.52 + .14 * rank, 1.30 + .19 * rank, time);
        float height = orbitUV.y/orbitR[i];
        float sine = 2.*height/(.68+sqrt(max(.003,.4624+.88*height)));
        vec2 actualTrack=vec2(orbitUV.x,orbitR[i]*sine);
        float trackRadius=length(actualTrack);
        float trackAngle=atan(actualTrack.y,actualTrack.x);
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

    float settled = smoothstep(.30,.91,alpha);
    float letters = nameInk(local, index) * settled;
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
    color += mix(vec3(.38,.59,.90), whiteLight(index), .28) * light * settled;
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
    vec3 cool = mix(vec3(.115, .29, .68), coolTint(scene), uCamera.w);
    vec3 warm = mix(vec3(.46, .58, .94), hotTint(scene), uCamera.w);
    float skyLight = max(uCamera.w, smoothstep(.43, 1.84, time));
    color += motes.r * (cool * 1.40 + vec3(.11, .12, .17)) * skyLight;
    color += motes.g * (warm * 1.16 + vec3(.055, .040, .070)) * skyLight;
    color += motes.b * vec3(.89, .91, 1.0) * (1.22 * skyLight);
    if (scene>=0 && uTransition.x<.999) {
        vec3 eventHue=wakeTint(scene);
        color += sin(3.14159265*uTransition.x) * (motes.r*.43+motes.g*.67+motes.b*.29)*eventHue;
    }

    vec4 bodies[5] = vec4[5](uSun, uMercury, uVenus, uEarth, uMars);
    vec2 disk = turn(.12) * (world - uSun.xy);
    vec2 relativeSun = world - uSun.xy;
    float arcd = length(relativeSun / vec2(1.0, .96));
    float arcMist = bell((arcd - .202) / .033) * (1.0 - bell(disk.y / .039));
    float sideMist = bell((disk.y + .024 * sin(disk.x * 4.7)) / .054) * bell(disk.x / .60);
    color += vec3(.12, .15, .27) * (.47 * arcMist + .13 * sideMist) * (1.0 - uCamera.w) * skyLight;
    color += atlasDial(relativeSun, turn(-.032)*relativeSun, time);
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
            color = bodyLayer(color, world, pointer, bodies[i], i, appear, false, time);
        }
    }
    if (scene >= 0) color = bodyLayer(color, world, pointer, bodies[scene], scene, 1.0, true, time);
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
