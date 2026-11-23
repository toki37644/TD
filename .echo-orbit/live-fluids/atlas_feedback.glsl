vec3 feedbackDye(vec3 ink, int id) {
    if (id == 2) return ink;
    vec3 primary[5] = vec3[5](vec3(1.,.26,.035), vec3(.18,.41,1.), vec3(1.,.08,.46),
                              vec3(.02,.87,.56), vec3(1.,.21,.15));
    vec3 secondary[5] = vec3[5](vec3(1.,.77,.18), vec3(.41,.73,1.), vec3(.67,.21,.98),
                                vec3(.035,.36,.96), vec3(.97,.085,.39));
    vec3 accent[5] = vec3[5](vec3(.71,.99,.16), vec3(.37,.96,.86), vec3(.09,.79,.99),
                             vec3(.68,.99,.22), vec3(1.,.58,.21));
    vec3 cool[5] = vec3[5](vec3(.12,.75,.88), vec3(.41,.23,.99), vec3(.19,.30,1.),
                           vec3(.14,.68,.94), vec3(.54,.20,.88));
    vec3 gleam[5] = vec3[5](vec3(.53,.89,.89), vec3(1.,.64,.37), vec3(.98,.72,.87),
                            vec3(.64,.27,.95), vec3(.10,.84,.81));
    float peak = max(ink.r, max(ink.g, ink.b));
    float warm = smoothstep(-.26,.55,ink.r - ink.b);
    float warmDetail = smoothstep(.18,.66,ink.g) * warm;
    float cyan = smoothstep(.035,.65,ink.g - ink.r*.59);
    float chalk = smoothstep(.36,.85,min(ink.r,min(ink.g,ink.b)));
    vec3 dye = mix(cool[id], secondary[id], cyan);
    dye = mix(dye, primary[id], warm);
    dye = mix(dye, accent[id], warmDetail*.61 + cyan*(1.-warm)*.17);
    dye = mix(dye, gleam[id], chalk*.73);
    return dye * peak;
}

vec3 tutorialInk(vec2 p, int id) {
    return feedbackDye(texture(sTD2DInputs[3], .5 + p*vec2(.204,.362)).rgb, id);
}

vec3 rotateFeedback(vec2 q, int id, float angle) {
    float d = dot(q,q);
    if (d > 1.01) return vec3(0.);
    vec3 normal = normalize(vec3(q,sqrt(max(.001,1.-d))));
    vec3 body = normal;
    body.xy = turn(.24) * body.xy;
    body.xz = turn(angle) * body.xz;
    body.yz = turn(-.18) * body.yz;
    vec2 front = vec2(.85*body.x + .19*body.y*body.z, .80*body.y + .19*body.z);
    vec2 rear = vec2(.82*body.x - .19*body.y*body.z, .76*body.y - .25*body.z + .07*body.x);
    vec3 ink = mix(tutorialInk(rear,id),tutorialInk(front,id),smoothstep(-.3,.4,body.z));
    float mark = body.y + .38*body.x - .18*body.z + .14*sin(3.8*body.x+2.7*body.z);
    float band = bell((mark-.08)/.070) * smoothstep(.14,.89,dot(body,vec3(-.54,.18,.82)));
    ink = mix(ink,whiteLight(id),band*.35);
    float day = smoothstep(-.67,.91,dot(normal,normalize(vec3(-.60,.64,.61))));
    float rim = pow(1.-normal.z,2.68);
    return (ink*(.24+.80*day) + coolTint(id)*rim*(.16+.29*day)) *
           (1.-smoothstep(.965,1.003,sqrt(d)));
}

vec3 bodyLayer(vec3 background, vec2 world, vec2 cursor, vec4 body, int id,
               float visible, bool selected, float time) {
    if (visible < .002) return background;
    float transition = selected ? uTransition.x : 1.;
    float ease = smoothstep(0.,1.,transition);
    vec2 center = mix(uTransition.yz,(body.xy-uCamera.xy)*uCamera.z,ease);
    float radius = mix(uTransition.w,body.z*uCamera.z,ease);
    vec2 q = ((world-uCamera.xy)*uCamera.z-center) / max(radius,.015);
    float r = length(q);
    if (r > (id == 0 ? 2.48 : 1.42)) return background;
    float locked = selected ? uScene.y*smoothstep(.39,.85,transition) : 0.;
    float scatter = sin(3.14159265*transition);
    visible *= 1.-.97*smoothstep(.15,.89,scatter);
    float beat = uAudio.x * locked;
    background += visible * nearWake(q,body,id,time,beat) * (.74 + .26*locked);
    if (id == 0) {
        vec3 corona = solarCorona(q/(1.+.055*beat),time+body.w)-BLACK;
        float taper = 1.-smoothstep(1.86,2.44,r);
        float core = 1.-smoothstep(.68,1.08,r);
        background = background*(1.-visible*.58*core) + corona*taper*visible*(1.-.72*locked*core);
        if (locked < .002) return background;
    }
    if (r > 1.20) return background;
    float sphereAmount = id == 0 ? 0. : 1.-locked;
    vec3 sphere = sphereAmount > .002 ? rotateFeedback(q,id,body.w*8.5) : vec3(0.);
    vec2 flatPosition = q/(1.+.037*beat);
    vec3 sheet = locked > .002 ? tutorialInk(flatPosition,id) : vec3(0.);
    sheet *= 1.-smoothstep(1.085,1.18,length(flatPosition));
    float peak = max(max(sheet.r,sheet.g),sheet.b);
    float flatMask = smoothstep(.015,.24,peak);
    float sphereMask = (1.-smoothstep(.974,1.015,r))*sphereAmount;
    return background*(1.-visible*(.94*sphereMask+.82*locked*flatMask)) +
           visible*(sphereAmount*sphere + locked*sheet*(1.+.15*uAudio.w));
}
