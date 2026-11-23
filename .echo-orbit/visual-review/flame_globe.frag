#version 300 es
precision highp float;
precision highp int;
precision highp sampler3D;

uniform sampler3D uVolume;
uniform vec4 uFrame; // width, height, seconds, scene
uniform vec4 uView;  // radius in height units, dark background, lift, start phase
uniform vec4 uPrimary;
uniform vec4 uAccent;
in vec2 uv;
out vec4 fragColor;

const vec3 LIGHT = vec3(-.52,.56,.65);

mat2 rotation(float t) {
    float c=cos(t),s=sin(t);
    return mat2(c,s,-s,c);
}

vec2 whirl(vec2 p, vec2 origin, float width, float spin) {
    vec2 q = p-origin;
    float influence = exp(-dot(q,q)/(width*width));
    return origin + rotation(spin*influence)*q;
}

vec3 spiralFlow(vec3 q, float scene, float t) {
    float phase = scene*1.37 + uView.w;
    float wave = .8*t+phase;
    q.xz = rotation(.13*sin(.62*t+phase)+.12*t) * q.xz;
    q.xy = rotation(.10*sin(.92*t+phase)) * q.xy;
    float side = mod(scene,2.)*2.-1.;
    q.xy = whirl(q.xy, vec2(-.34+.12*cos(phase),.21+.19*sin(phase)), .61+.10*sin(phase),
                 side*(2.65+.72*sin(wave+.94))*(.87+.17*q.z));
    q.xy = whirl(q.xy, vec2(.41,-.29+.14*sin(phase)), .44, -side*(2.25+.71*cos(wave+.12)));
    q.xy = whirl(q.xy, vec2(.31+.11*cos(phase),.61), .29, side*(1.38+.6*sin(wave-.55)));
    q.xz += .082*sin(4.3*q.y+vec2(2.4,-3.2)*q.z+phase+vec2(.76,-.64)*t);
    q.y += .058*sin(7.1*q.x+2.5*q.z-.40*t+phase)+.025*sin(12.*q.z-4.5*q.x+.6*t);
    return q;
}

vec4 material(vec3 p, float scene, float t) {
    vec3 q = spiralFlow(p,scene,t);
    return texture(uVolume, q/2.54+.5);
}

vec4 sunFlow(vec2 p, float t) {
    // Thin lips and a broad core describe an attached return flow.
    vec2 start=vec2(-.94,.29), ca=vec2(-1.15,.97);
    vec2 cb=vec2(-.52,1.56+.045*sin(t)), end=vec2(-.18,.91);
    float best=0.;
    vec3 dye=vec3(0.);
    for (int i=1;i<94;i++) {
        float s=float(i)/94.,r=1.-s;
        vec2 center=r*r*r*start+3.*r*r*s*ca+3.*r*s*s*cb+s*s*s*end;
        center.x+=.029*sin(17.*s-1.75*t)*sin(3.14159*s);
        float profile = sin(3.14159*s);
        float width=.022+profile*(.031+.018*sin(18.*s-1.7*t));
        vec2 d=p-center;
        float distance=dot(d,d);
        float plume=profile*(.70*exp(-distance/(width*width))+.24*exp(-distance/(width*width*3.)));
        if (plume>best) {
            best=plume;
            float hot = .35+.53*pow(profile,2.)*(.65+.35*sin(16.*s-t));
            dye=mix(uAccent.rgb,uPrimary.rgb,hot);
        }
    }
    return vec4(dye,best);
}

void main() {
    float scene = uFrame.w;
    float t=uFrame.z;
    vec2 p=(uv-vec2(.5,uView.z))*vec2(uFrame.x/uFrame.y,1.)/uView.x;
    float angle=atan(p.y,p.x),phase=scene*1.46;
    float edge = 1.+.028*sin(2.*angle-phase)+.015*sin(3.*angle+.6*phase);
    edge += .017*sin(4.*angle+.47*t+phase)*(.5+.5*sin(angle+.6*phase));
    vec2 xy=p/edge;
    float r=length(xy);
    float front=sqrt(max(0.,1.-r*r));
    vec3 bg=mix(vec3(.949,.942,.927),vec3(.015,.021,.035),uView.y);
    vec3 backdrop=bg;
    vec2 edgePoint=xy/max(r,.001);
    vec4 haze=material(vec3(edgePoint*.895,.29),scene,t);
    vec3 haloTone=haze.rgb/max(haze.a,.001);
    haloTone=mix(uPrimary.rgb,haloTone,.67);
    float halo=.18*exp(-8.8*pow(max(r-.86,0.),1.45))*(1.-smoothstep(.85,1.9,r));
    halo *= .51+.49*smoothstep(.0,2.,haze.a);
    backdrop=mix(backdrop,haloTone,halo*mix(.78,.65,uView.y));
    vec3 color=backdrop;
    if (r<1.010) {
        vec3 n=normalize(vec3(xy,front+.015));
        float ndl=dot(n,LIGHT);
        float lit=smoothstep(-.65,.93,ndl);
        int steps=uFrame.y<500.?35:45;
        float dz=2.*front/float(steps);
        float left=1.;
        vec3 light=vec3(0.);
        for (int j=0;j<steps;j++) {
            float z=front-(float(j)+.5)*dz;
            vec3 q = vec3(xy,z);
            vec4 density=material(q,scene,t);
            vec3 ink=density.rgb/max(density.a,.0001);
            vec4 ahead=material(q+.049*LIGHT,scene,t);
            float ridge=clamp((density.a-ahead.a)*.64,-.36,.82);
            float diffuse=.55+.33*lit+.21*z+ridge*.36;
            float a=1.-exp(-density.a*dz*2.06);
            light += left*a*ink*diffuse;
            left *= 1.-a;
            if (left<.012) break;
        }
        vec3 deep = mix(vec3(.038,.052,.086),uPrimary.rgb,.19);
        color=light + left*deep*(.57+.39*lit);
        float contrast = .68+.34*lit;
        color *= contrast;
        float luminous = max(max(color.r,color.g),color.b);
        float gloss = pow(max(0.,dot(n,normalize(vec3(-.43,.50,1.)))),16.);
        // Preserve vivid midtones; pale rims make room for colored shadows.
        float lum=dot(color,vec3(.2126,.7152,.0722));
        color=mix(vec3(lum),color,1.23+.15*(1.-lit));
        color=max(vec3(0.),color)*(1.11/(.73+.37*luminous));
        color += .040*gloss*mix(uPrimary.rgb,vec3(1.),.23);
        float fresnel=pow(max(0.,1.-front),2.8);
        color=mix(color,haloTone,(.13+.25*lit)*fresnel);
        float softness=.023+.035*pow(.5+.5*sin(3.0*angle+.6*t+phase),2.);
        float coverage=1.-smoothstep(1.-softness,1.011,r);
        color=mix(backdrop,color,coverage);
    }
    if (scene<.5 && p.x<-.10 && p.y>.17 && p.y<1.36) {
        vec4 arch=sunFlow(p,t);
        color = mix(color,arch.rgb*.92,arch.a*.98);
    }
    fragColor=vec4(clamp(color,0.,1.),1.);
}
