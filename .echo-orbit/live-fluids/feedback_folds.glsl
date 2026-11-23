layout(location = 0) out vec4 fragColor;
uniform vec4 uFlow;

mat2 turn(float angle) {
    float c = cos(angle), s = sin(angle);
    return mat2(c,s,-s,c);
}

float bell(float x) { return exp(-x*x); }

void main() {
    vec2 uv = vUV.st;
    vec2 scale = vec2(.188,.334);
    vec2 q = (uv-.5)/scale;
    float time = uFlow.x;
    float beat = smoothstep(.19,1.08,uFlow.y);
    vec2 p = turn(.66*sin(time*.32)+.46*time) * q;
    float angle = atan(p.y,p.x+.00001);
    float r = length(p);
    // A broad neck and a narrower opposing fold open and release at different times.
    float opening = .5+.5*sin(time*1.09+.25);
    float largeFold = bell(sin((angle-.45)*.5)/.29);
    float smallFold = bell(sin((angle+2.12)*.5)/.25);
    float boundary = .97+.099*sin(angle*2.-.46)+.044*sin(angle*3.+time*.57);
    boundary -= (.19+.38*opening+.12*beat)*largeFold;
    boundary -= (.065+.22*opening)*smallFold;
    boundary += .034*sin(5.*angle-time*.73)+.023*sin(7.*angle+time*.88);
    float ripple = .007*sin(21.*angle+3.4*sin(3.*angle-time));
    ripple += .004*sin(47.*angle-time*1.8)*sin(7.*angle+.46*time);
    boundary += ripple;
    float depth = boundary-r;

    vec2 eddy = turn(.52*sin(2.6*p.y-1.65*p.x+time*.80)) * p;
    float crease = eddy.x+.25*sin(3.25*eddy.y+.58*time)+.15*eddy.y;
    float poolA = bell(length((eddy-vec2(-.36,.15))*vec2(1.30,1.77)));
    float poolB = bell(length((eddy-vec2(.37,-.28))*vec2(1.75,1.20)));
    float trough = bell((crease-.05)/(.14+.12*opening));
    float chamber = .36+.55*max(poolA,poolB)-(.14+.11*opening)*trough;

    // Advect the previous field and admit fresh signal from the Palette feedback.
    vec2 shear = vec2(sin(3.7*p.y+.8*time),-sin(3.1*p.x-.65*time));
    vec2 historyUv = uv+shear*vec2(.0022,.0039)*(1.+beat*.46);
    vec4 previous = texture(sTD2DInputs[0],historyUv);
    vec3 seed = texture(sTD2DInputs[1],.5+eddy*scale*.89).rgb;
    float current = dot(seed,vec3(.30,.52,.18));
    float history = dot(previous.rgb,vec3(.30,.52,.18));
    float shoreWidth = .236+.115*sin(2.*angle+time*.61)+.043*sin(5.*angle-.44*time);
    float shore = smoothstep(-.114,shoreWidth,depth);
    float detail = sin(91.*(depth+.063*eddy.y+.028*sin(6.*eddy.x+time)));
    float fine = sin(194.*depth+11.*sin(4.4*angle-time));
    float banding = (.036*detail+.011*fine)*exp(-abs(depth-.057)*8.);
    float channels = sin((crease+.095*sin(7.2*eddy.y-time*.4))*40.);
    float filaments = .054*pow(.5+.5*channels,13.)*bell((crease-.15)/.42);
    filaments *= bell((eddy.y+.06)/.71)*smoothstep(.18,.75,poolA+poolB);
    float density = shore*(chamber+.091*current+.069*beat+filaments)+banding;
    density = mix(density,history,shore*(.15+.15*beat));
    float support = smoothstep(-.110,-.045,depth);
    float edgeGrain = fract(sin(dot(floor(vUV.st*vec2(960.,540.)),vec2(12.9898,78.233)))*43758.5453);
    density += .038*(edgeGrain-.30)*bell((depth+.022)/.048);
    fragColor = TDOutputSwizzle(vec4(vec3(max(0.,density)*support),support));
}
