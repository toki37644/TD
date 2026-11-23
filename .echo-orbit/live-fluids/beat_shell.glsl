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
