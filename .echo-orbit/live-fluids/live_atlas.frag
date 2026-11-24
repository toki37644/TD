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
uniform vec4 uView;    // close-up yaw, pitch, and whether the view is open

out vec4 fragColor;

const vec2 ASPECT = vec2(9.0 / 16.0, 1.0);
const vec2 FRAME_SIZE = vec2(720.0, 1280.0);

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
    // Follow the tall particle plumes using the same portrait frame.
    field = turn(-.64) * field;
    field *= vec2(1.03,1.38);
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
        vec2 wake = turn(-.41) * (field + vec2(.07+.030*sin(.24*time),.033));
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
        vec2 sweep = turn(.11*sin(.16*time)) * field;
        source = vec2(.50, .505) + vec2(.465*sweep.x + .045*sweep.y, .49*sweep.y - .085*sweep.x);
        tint = vec3(1.08, 1.30, 1.90);
        envelope = .68;
    } else {
        // Dust fans fork toward the upper left in two overlapping streaks.
        vec2 fan = turn(-2.53) * (field - vec2(.06,-.033));
        float bow = .11 * sin(fan.x * 4.1 + .16*time) - .024;
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
    // Reframe the widescreen source around its detailed spiral arms.
    vec2 plate = vec2(.50,.53) + (clamp(source,.001,.999)-.5)*vec2(.68,.91);
    vec2 texel = uTD2DInfos[1].res.xy * 1.45;
    vec3 footage = texture(sTD2DInputs[1], plate).rgb;
    vec3 surround = texture(sTD2DInputs[1], plate+vec2(texel.x,0.)).rgb;
    surround += texture(sTD2DInputs[1], plate-vec2(texel.x,0.)).rgb;
    surround += texture(sTD2DInputs[1], plate+vec2(0.,texel.y)).rgb;
    surround += texture(sTD2DInputs[1], plate-vec2(0.,texel.y)).rgb;
    footage = max(vec3(0.), footage + .48*(footage-.25*surround));
    const vec3 LUMA = vec3(.229, .614, .157);
    float light = dot(footage, LUMA);
    footage /= 1. + .83*light;
    light /= 1. + .83*light;
    vec3 theme = wakeTint(scene);
    vec3 deep = mix(coolTint(scene),theme,.47);
    vec3 lit = mix(theme, normalize(theme+.36), smoothstep(.48,.92,light)*.55);
    vec3 graded = mix(footage, mix(deep,lit,smoothstep(.05,.54,light))*light*1.62, gradeAmount);
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

vec4 volumeSlice(vec2 uv, int layer) {
    ivec2 cell=ivec2(layer%16,layer/16);
    vec2 px=vec2(cell)*50.+vec2(1.5)+uv*47.;
    vec2 colorUV=vec2(px.x/800.,1.-px.y/1200.);
    vec3 ink=texture(sTD2DInputs[3],colorUV).rgb;
    float code=texture(sTD2DInputs[3],colorUV-vec2(0.,.5)).r;
    float opacity=code*code;
    float density=5.*opacity/max(.009,1.-opacity);
    return vec4(ink*density,density);
}

vec2 flowEddy(vec2 p, vec2 center, float spread, float twist) {
    vec2 delta=p-center;
    return center+turn(twist*exp(-dot(delta,delta)/(spread*spread)))*delta;
}

vec4 luminousDye(vec3 p, float time, int id, float drive, float transient) {
    float kind=float(id);
    float phase=kind*1.27 + (id==1?1.51:id==2?2.28:id==3?-.62:1.77);
    float flow=time*.78+phase;
    float side=id%2==0?-1.:1.;
    p.xy=flowEddy(p.xy,vec2(-.31,.19),.58+.067*sin(phase),side*(1.31+.65*sin(flow))*(.9+.22*p.z));
    p.xy=flowEddy(p.xy,vec2(.38,-.32),.44,-side*(1.17+.54*cos(flow+.53)));
    vec3 broad=sin(5.4*p.yzx+4.2*p.zxy+vec3(.70,-.58,.67)*flow);
    p+=(.069+.075*drive)*broad;
    p+=(.021+.023*transient)*sin(p.yzx*15.3+p.zxy*5.3+flow);
    vec3 uv=clamp(p/2.54+.5,0.,1.);
    float z=uv.z*47.;
    int layer=int(floor(z));
    int first=(id-1)*48;
    vec4 blend=mix(volumeSlice(uv.xy,first+layer),
                   volumeSlice(uv.xy,first+min(47,layer+1)),fract(z));
    return blend;
}

vec3 orbColor(vec2 q, int id, vec2 cursor, float time, float spin, vec2 rhythm, float engaged,
              float radiusInPixels) {
    float r=length(q);
    if (r>1.09) return vec3(0.);
    float mask=1.-smoothstep(.946,1.045,r);
    float depth=sqrt(max(.0,1.02-r*r));
    vec3 light=normalize(vec3(-.48+cursor.x*.83*engaged,.61+cursor.y*.69*engaged,.62));
    vec3 surface=normalize(vec3(q,depth+.01));
    float lit=smoothstep(-.55,.96,dot(surface,light));
    float pitch=.14 - cursor.y*.54*engaged;
    float yaw=spin*.66+cursor.x*.76*engaged+.13*sin(time*.43);
    mat2 xz=turn(yaw), yz=turn(pitch);
    int steps=radiusInPixels<52.?10:24;
    float dz=2.*depth/float(steps);
    float remaining=1.;
    vec3 energy=vec3(0.);
    for (int step=0;step<24;step++) {
        if (step>=steps || remaining<.014) break;
        float z=depth-(float(step)+.5)*dz;
        vec3 p=vec3(q,z);
        p.xz=xz*p.xz;
        p.yz=yz*p.yz;
        vec4 d=luminousDye(p,time,id,rhythm.x,rhythm.y);
        float absorption=1.-exp(-d.a*dz*(1.66+.33*rhythm.x));
        float concentration=smoothstep(.28,5.3,d.a);
        float depthLight=.51+.45*lit+.11*z-.21*concentration;
        vec3 dye=d.rgb/max(.001,d.a);
        energy+=remaining*absorption*dye*depthLight*(.97+.23*concentration);
        remaining*=1.-absorption;
    }
    vec3 tint=wakeTint(id);
    vec3 foundation=tint*(.071+.093*lit);
    energy += remaining * foundation;
    float luma=dot(energy,vec3(.2126,.7152,.0722));
    energy=max(vec3(0.),mix(vec3(luma),energy,1.29));
    float peak=max(max(energy.r,energy.g),energy.b);
    energy*=1.06/(.80+.39*peak);
    float swell=bell((r-.90)/.122)*(1.-smoothstep(.985,1.095,r));
    return (1.+.23*rhythm.x)*energy*mask+tint*.072*swell*lit;
}

vec3 bodyLayer(vec3 background, vec2 world, vec2 cursor, vec4 body, int id,
               float visible, bool selected, float time) {
    if (visible<.002) return background;
    float transition=selected?uTransition.x:1.;
    float ease=smoothstep(0.,1.,transition);
    float radius=body.z*uCamera.z;
    vec2 screen=(world-uCamera.xy)*uCamera.z;
    vec2 center=mix(uTransition.yz,(body.xy-uCamera.xy)*uCamera.z,ease);
    radius=mix(uTransition.w,radius,ease);
    vec2 q=(screen-center)/max(radius,.015);
    float r=length(q);
    if (r>(id==0?2.52:1.42)) return background;
    float drive=selected?uScene.y:0.;
    vec2 rhythm=uAudio.xw*drive;
    float scatter=sin(3.14159265*transition);
    visible*=1.-.95*smoothstep(.18,.89,scatter);
    background+=visible*nearWake(q,body,id,time,rhythm.x);
    if (id==0) {
        vec3 sun=solarCorona(q/(1.+.057*rhythm.x),time+body.w)-BLACK;
        float taper=1.-smoothstep(1.95,2.50,r);
        float directional=.84+.20*dot(normalize(vec2(.02)+q),normalize(vec2(.3,.54)+cursor*.58*drive));
        return background*(1.-visible*.70*(1.-smoothstep(.62,1.05,r)))+sun*taper*visible*directional;
    }
    if (r>1.10) return background;
    vec3 surface=orbColor(q,id,cursor,time,body.w,rhythm,drive,radius*675.);
    float mask=1.-smoothstep(.92,1.058,r);
    return background*(1.-.93*visible*mask)+surface*visible;
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
    vec2 p = point * (FRAME_SIZE.y * uCamera.z);
    float radius = length(p);
    float glimmer = bell(radius / 4.5) + .25 * bell(radius / 21.0);
    glimmer += bell(p.y / 1.0) * bell(p.x / 63.0) * .32;
    glimmer += bell(p.x / .87) * bell(p.y / 32.0) * .26;
    float wave = orbitTrace(radius, time * 151.0, 1.0, 1.25) * pulse * .30;
    return vec3(.67, .81, 1.0) * (pulse * glimmer + wave);
}

vec3 atlasDial(vec2 world, float time) {
    float wide = 1.0 - smoothstep(.06,.71,uCamera.w);
    if (wide < .002) return vec3(0.);
    vec2 px = world * FRAME_SIZE.y * uCamera.z;
    float reveal = mix(-.32,.78,smoothstep(.20,1.77,time));
    float open = 1.-smoothstep(reveal,reveal+.10,world.x);
    float core = bell(px.y/.71);
    float twin = bell((abs(px.y)-4.1)/.61);
    float spread = (.45+.55*bell((world.x+.11)/.39));
    float grain = hash21(floor(vec2(px.x*.57,px.y*.82)));
    float shimmer = .64+.36*sin(px.x*.024-time*.77);
    float lines = (.25*core+.10*twin+.036*bell(px.y/13.))*spread*shimmer;
    float survey = bell((abs(px.y)-23.)/.52)*(.21+.79*bell((world.x+.08)/.45));
    float marker = bell((fract(px.x/34.+.5)-.5)*47.);
    float graduation = marker*(bell((abs(px.y)-15.)/3.4)+.48*bell((abs(px.y)-27.)/1.7));
    float dust = pow(grain,11.)*bell(px.y/13.)*(.42+.58*shimmer);
    float sweep = bell((world.x-reveal)/.009) * bell(px.y/2.7);
    vec3 silver = vec3(.63,.68,.77);
    vec3 ray = silver*(lines+.064*survey+.183*graduation+.40*dust+.31*sweep);
    return ray * open * wide;
}

vec3 planetDial(vec2 point, vec4 body, int index, float time, bool hovered) {
    vec2 p = (point - body.xy) * (FRAME_SIZE.y * uCamera.z);
    float rim = body.z * (FRAME_SIZE.y * uCamera.z);
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

float nameInk(vec2 point, int index, float rowCenter, vec2 bounds) {
    if (any(greaterThan(abs(point),bounds))) return 0.0;
    vec2 coord = vec2(.5 + point.x/256., 1. - (144.*float(index)+rowCenter-point.y)/720.);
    return texture(sTD2DInputs[2], coord).r;
}

float hoverNameInk(vec2 point, int index) {
    return nameInk(point * 1.28, index, 28., vec2(64.,27.));
}

vec3 planetCaption(vec2 screen, vec4 body, int index) {
    float alpha = uLabel.y;
    float side = uLabel.z;
    float dissolve = 1.0 - alpha;
    float outward = uLabel.w;
    float pixels = FRAME_SIZE.y * uCamera.z;
    vec2 center = (body.xy - uCamera.xy) * pixels;
    float radius = body.z * pixels;
    vec2 origin = center + vec2(side * (radius * .32 + 15.0), radius + 43.0);
    vec2 limit = FRAME_SIZE*.5-vec2(64.,51.);
    origin = clamp(origin, -limit, limit);
    vec2 point = screen * FRAME_SIZE.y;
    vec2 local = point - origin;
    if (abs(local.x) > (radius + 157.0) || abs(local.y) > radius + 63.0) return vec3(0.0);

    float settled = smoothstep(.30,.91,alpha);
    float letters = hoverNameInk(local, index) * settled;
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
            float density = hoverNameInk(dotOrigin, index);
            float dot = bell(length(travelled - dotOrigin) / (.48 + .28 * seed));
            specks += dot * density * (.52 + .48 * seed);
        }
    }
    float particleLife = alpha * (1.0 - smoothstep(.64,.995,alpha)) * (outward > .5 ? 2.9 : 2.1);
    vec3 color = vec3(.78,.89,1.0) * (letters + specks * particleLife);

    vec2 tip = center + vec2(side * .21, .91) * (radius + 4.0);
    vec2 elbow = origin + vec2(-side * 14.0, -18.0);
    vec2 end = origin + vec2(side * 25.0, -18.0);
    float wire = min(lineSegment(point,tip,elbow), lineSegment(point,elbow,end));
    float light = bell(wire / .74) * .42 + bell(length(point - tip) / 2.55) * .78;
    color += mix(vec3(.38,.59,.90), whiteLight(index), .28) * light * settled;
    return color;
}

vec3 instrument(vec3 color, vec2 p, vec2 cursor) {
    // One symbol only, anchored to the frame in a dedicated hit area.
    vec2 hand = (p - (vec2(.092, .926) - .5) * ASPECT) * FRAME_SIZE.y;
    float alpha = smoothstep(.10, .85, uScene.y);
    float halo = bell(length(hand) / 27.5);
    float circle = 1.0 - smoothstep(.75, 1.65, abs(length(hand) - 19.0));
    float stroke = min(lineSegment(hand, vec2(-8.0, 0.0), vec2(8.0, 0.0)),
                       min(lineSegment(hand, vec2(-8.0, 0.0), vec2(-2.0, 6.0)),
                           lineSegment(hand, vec2(-8.0, 0.0), vec2(-2.0, -6.0))));
    float arrow = 1.0 - smoothstep(.75, 1.60, stroke);
    color *= 1.0 - .54 * halo * alpha;
    color += vec3(.70, .73, .88) * alpha * (circle * (.21 + .37 * uScene.w) + .86 * arrow);
    float drag = length(p - cursor) * FRAME_SIZE.y;
    color += hotTint(int(uScene.x + .5)) * (.35 * bell(drag / 2.6) + .075 * bell(drag / 13.5)) * uPointer.w;
    return color;
}

vec3 detailTitle(vec3 color, vec2 uv, int index) {
    vec2 point = (uv - vec2(.5,1.)) * FRAME_SIZE;
    float chinese = nameInk(point+vec2(0.,84.),index,84.,vec2(110.,27.));
    float english = nameInk(point+vec2(0.,128.),index,128.,vec2(110.,15.));
    float alpha = smoothstep(.10,.74,uScene.y);
    float shade = bell(length((point+vec2(0.,103.))/vec2(130.,56.)));
    color *= 1. - .39*shade*alpha;
    return mix(color,vec3(.94,.95,1.),chinese*alpha) +
           english*alpha*vec3(.65,.73,.87);
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
    int label = int(floor(uLabel.x + .5));
    if (label >= 0 && label < 5 && label != scene) bodies[label].z *= 1.+.14*uLabel.y;
    vec2 disk = world - uSun.xy;
    vec2 relativeSun = world - uSun.xy;
    float arcd = length(relativeSun / vec2(1.0, .96));
    float arcMist = bell((arcd - .202) / .033) * (1.0 - bell(disk.y / .039));
    float sideMist = bell((disk.y + .024 * sin(disk.x * 4.7)) / .054) * bell(disk.x / .60);
    color += vec3(.12, .15, .27) * (.47 * arcMist + .13 * sideMist) * (1.0 - uCamera.w) * skyLight;
    color += atlasDial(world, time);
    int hovered = int(floor(uScene.z + .5));
    if (uCamera.w < .63) {
        for (int i = 1; i < 5; ++i) {
            color += planetDial(world, bodies[i], i, time, i == hovered);
        }
    }

    for (int i = 0; i < 5; ++i) {
        if (i == scene) continue;
        float appear = (1.0 - smoothstep(.05, .76, uCamera.w)) * planetLight(i, time);
        color = bodyLayer(color, world, pointer, bodies[i], i, appear, false, time);
    }
    if (scene >= 0) color = bodyLayer(color, world, pointer, bodies[scene], scene, 1.0, true, time);
    // Near-side grains cross the center of the solar disk.
    float foreground = bell(disk.y * 34.0) * bell(disk.x * 4.65) * (1.0 - uCamera.w);
    color += (motes.b * vec3(.85,.89,1.0) + motes.r * vec3(.17,.37,.76)) * foreground * (.95 * skyLight);
    color += openingSignal(relativeSun, time) * (1.0 - uCamera.w);

    if (hovered >= 0) {
        vec4 body = bodies[hovered];
        float d = (length(world - body.xy) - body.z) * FRAME_SIZE.y * uCamera.z;
        float guide = bell((d - 6.0) * .73) * .41;
        color += (hotTint(hovered) + .22) * guide * (1.0 - smoothstep(.10, .69, uCamera.w));
    }
    color *= 1.0 - .30 * smoothstep(.43, 1.05, length(screen));
    color = instrument(color, screen, pointer);
    if (uView.z > .5 && scene >= 0) color = detailTitle(color,uv,scene);
    if (uView.z < .5 && label >= 0 && label < 5 && uLabel.y > .015 && uCamera.w < .35) {
        color += planetCaption(screen, bodies[label], label) * (1.-smoothstep(.02,.35,uCamera.w));
    }
    color += (hash21(floor(uv * FRAME_SIZE)) - .5) * .005;
    color = min(color, .82) + .18 * (1.0 - exp(-max(color - .82, 0.0) / .18));
    fragColor = TDOutputSwizzle(vec4(clamp(color, 0.0, 1.0), 1.0));
}
