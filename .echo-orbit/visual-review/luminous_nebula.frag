#version 300 es
precision highp float;
precision highp sampler3D;

uniform sampler3D uVolume;
uniform vec4 uFrame;
uniform vec4 uView;
uniform vec4 uPrimary;
uniform vec4 uAccent;
uniform vec4 uStage;
uniform vec4 uSolarGreen;
uniform vec4 uSolarCyan;
uniform vec4 uSolarBlue;
uniform vec4 uTrail;
uniform vec4 uHistory[36];
in vec2 uv;
out vec4 fragColor;

const vec3 KEY = vec3(-.47,.58,.66);
const vec3 BLACK = vec3(.004,.006,.012);

mat2 rotate(float t) {
    float c=cos(t), s=sin(t);
    return mat2(c,s,-s,c);
}

vec2 eddy(vec2 v, vec2 origin, float radius, float phase) {
    vec2 d = v-origin;
    return origin + rotate(phase*exp(-dot(d,d)/(radius*radius)))*d;
}

vec4 coloredCloud(vec3 p, float time, float phase, float release) {
    vec3 warp = p;
    float motion=.78*time+phase;
    warp.xz = rotate(.18*sin(motion*.6)+.133*time)*warp.xz;
    float handed=mod(uFrame.w,2.)*2.-1.;
    warp.xy = eddy(warp.xy,vec2(-.31,.19),.58+.067*sin(phase),
                  handed*(1.31+.65*sin(motion))*(.9+.22*p.z));
    warp.xy = eddy(warp.xy,vec2(.38,-.32),.44,-handed*(1.17+.54*cos(motion+.53)));
    vec3 fold = vec3(
        sin(6.3*warp.y+4.2*warp.z+.70*motion),
        sin(5.2*warp.x-3.1*warp.z-.58*motion),
        sin(5.9*warp.y-2.6*warp.x+.67*motion)
    );
    warp += (.064+.090*release)*fold;
    warp += .024*sin(warp.yzx*15.3 + warp.zxy*5.3 + motion);
    vec3 cell=warp/2.54+.5;
    vec4 dye=texture(uVolume,cell);
    float radius=length(p);
    float swell = .43+.57*release;
    float billow = 1.+swell*(.061*sin(4.8*p.x+4.5*p.y+2.7*p.z+phase) +
                      .034*sin(9.1*p.y-5.1*p.z-.51*motion));
    float edge = radius/billow;
    float falloff=1.-smoothstep(.905-.12*release,1.115+.14*release,edge);
    float channel = sin(6.5*warp.x+3.4*warp.y+2.1*warp.z+.5*motion);
    channel += .58*sin(7.1*warp.y-4.4*warp.z+phase);
    falloff *= mix(1.,mix(.12,.75,smoothstep(-.65,.70,channel)),release*.94);
    return dye*falloff;
}

vec3 thermalColor(float r) {
    vec3 color=mix(uPrimary.rgb,uAccent.rgb,smoothstep(.34,.51,r));
    color=mix(color,uSolarGreen.rgb,smoothstep(.545,.705,r));
    color=mix(color,uSolarCyan.rgb,smoothstep(.69,.86,r));
    return mix(color,uSolarBlue.rgb,smoothstep(.865,1.07,r));
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
    rayFalloff*=1.-uTrail.a*smoothstep(1.12,2.05,r);
    float spectrum=.27+.57*r;
    vec3 rayColor=thermalColor(spectrum);
    rayColor=mix(rayColor,uSolarCyan.rgb,.59*smoothstep(.93,1.65,r));
    energy+=(beam+scattering)*rayFalloff*strength*.52*rayColor;
    vec2 drift=p+vec2(.065,-.042);
    float halo=exp(-1.27*dot(drift,drift));
    float fog=halo*(.068+.033*sin(2.*angle+.45)*smoothstep(.2,.7,r));
    vec3 atmospheric=mix(uSolarBlue.rgb,uSolarCyan.rgb,exp(-5.8*(r-.73)*(r-.73))*.50);
    energy+=fog*atmospheric;
    float peak=max(energy.r,max(energy.g,energy.b));
    vec3 corona=energy/(.83+.30*peak);
    float ripple=.017*sin(5.*angle+.67*time)*smoothstep(.10,.38,r);
    float core=1.-smoothstep(.21,.54,r+ripple);
    float heat=.93+.043*cos(5.3*p.x+3.9*p.y-.66*time);
    return BLACK+mix(corona,heat*uPrimary.rgb,.86*core);
}

vec3 withTrail(vec3 rendered,vec2 screen,vec2 centered,float time) {
    if (uTrail.a<.5) return rendered;
    float core=0.,mist=0.;
    vec2 ripple=vec2(
        sin(5.1*screen.y+3.*screen.x-1.8*time),
        cos(5.8*screen.x-3.4*screen.y+2.3*time)
    );
    ripple *= .067 + .124*smoothstep(.55,2.8,length(centered));
    for (int i=0;i<35;i++) {
        vec4 history=uHistory[i];
        vec2 point=screen-ripple-history.xy;
        if (dot(point,point)>history.z*history.z*13.) continue;
        vec2 travel=normalize(history.xy-uHistory[i+1].xy+vec2(.0001));
        vec2 across=vec2(-travel.y,travel.x);
        float axial=dot(point,travel), side=dot(point,across);
        float wave=sin(float(i)*.47+4.4*screen.y-2.1*time);
        float body=exp(-1.9*axial*axial/(history.z*history.z)
                       -1.21*side*side/(history.z*history.z));
        float fold=exp(-2.5*axial*axial/(history.z*history.z)
                       -8.2*pow(side/history.z-.34*wave,2.));
        float fog=exp(-.61*dot(point,point)/(history.z*history.z));
        core += history.w*(.58*body+.58*fold);
        mist += history.w*fog;
    }
    float tail=1.-exp(-(1.42*core+.132*mist));
    float visibility=smoothstep(.64,1.13,length(centered));
    float contrast=.84+.16*sin(4.8*screen.x+3.45*screen.y+.9*time);
    vec3 afterimage=uTrail.rgb*tail*visibility*contrast;
    return rendered+(1.-rendered)*afterimage;
}

void main() {
    float scene = uFrame.w, time=uFrame.z, release=uStage.x;
    float phase = scene*1.27 + uView.w;
    float aspect=uFrame.x/uFrame.y;
    vec2 screen = (uv-vec2(.5,uView.z))*vec2(aspect,1.)/uView.x;
    vec2 world=screen;
    if (uTrail.a>.5) world-=uHistory[0].xy;
    if (scene<.5) {
        world.y+=(uView.z-.5)/uView.x;
        vec3 star=clamp(solarCorona(world,time),0.,1.);
        fragColor=vec4(withTrail(star,screen,world,time),1.);
        return;
    }
    vec2 p = rotate(.14*release)*world;
    p.y=(p.y-.075*release)/(1.+.22*release);
    p.x-=release*(.29*sin(2.4*p.y+.71*time)+.21*p.y+.064*sin(7.*p.y));
    p.x /= 1.-.16*release;
    float bound=1.19+.11*release;
    float screenR2=dot(p,p);
    vec3 energy=vec3(0.);
    if (screenR2<bound*bound) {
        float halfDepth=sqrt(bound*bound-screenR2);
        int steps=uFrame.y<495.?35:46;
        float dz=2.*halfDepth/float(steps);
        float transmission=1.;
        for (int i=0; i<steps; i++) {
            float z=halfDepth-(float(i)+.5)*dz;
            vec3 pos=vec3(p,z);
            vec4 d = coloredCloud(pos,time,phase,release);
            if (d.a>.0007) {
                vec3 ink = d.rgb/max(d.a,.0001);
                float above=coloredCloud(pos+KEY*.12,time,phase,release).a;
                float broadShade=exp(-.35*above);
                float side=smoothstep(-.85,.89,dot(pos,KEY));
                float diffuse=.19+.62*broadShade+.37*side + .07*max(z,0.);
                float concentration=smoothstep(.43,4.6,d.a);
                float alpha=1.-exp(-d.a*dz*(1.40-.43*release));
                vec3 ray=ink*diffuse*(.92+.24*concentration);
                ray += .39*ink*ink*max(d.a-above,0.)/(1.+d.a);
                energy += transmission*alpha*ray;
                transmission*=1.-alpha;
                if (transmission<.017) break;
            }
        }
    }
    // An attached atmosphere fills the dim parts of a nearly spherical limb.
    float angle=atan(world.y,world.x);
    float outline=1.+.015*sin(3.*angle+phase)+.011*sin(2.*angle+.63*phase);
    float radius=length(world)/outline;
    float body=1.-smoothstep(.935,1.029,radius);
    float whole=1.-smoothstep(.04,.78,release);
    vec3 gathered=vec3(0.);
    if (whole>0. && radius<1.10) {
        vec3 normal=normalize(vec3(world,sqrt(max(.003,1.-radius*radius))));
        float lit=smoothstep(-.56,.96,dot(normal,KEY));
        vec4 vapor=coloredCloud(vec3(world*.91,.36),time,phase,0.);
        vec3 atmosphere=mix(uPrimary.rgb,vapor.rgb/max(vapor.a,.001),
                           .61*smoothstep(.025,1.4,vapor.a));
        float limb=exp(-pow((radius-.95)/.082,2.));
        vec3 fill=atmosphere*(.142+.110*lit+.11*limb);
        float existing=max(energy.r,max(energy.g,energy.b));
        gathered=energy*body + fill*body*(1.-smoothstep(.12,.56,existing));
        gathered += atmosphere*.034*limb*(1.-body)*(1.-smoothstep(1.02,1.10,radius));
    }
    energy=mix(energy,gathered,whole);
    float luminance=dot(energy,vec3(.2126,.7152,.0722));
    energy=max(vec3(0.),mix(vec3(luminance),energy,1.35));
    float peak=max(energy.r,max(energy.g,energy.b));
    energy *= (.95/(.80+.36*peak));
    vec3 rendered=clamp(BLACK+energy,0.,1.);
    fragColor=vec4(withTrail(rendered,screen,world,time),1.);
}
