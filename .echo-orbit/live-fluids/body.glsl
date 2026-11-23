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
