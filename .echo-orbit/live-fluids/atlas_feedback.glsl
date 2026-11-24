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

vec3 closeupInk(vec2 p, int id) {
    vec3 ink = texture(sTD2DInputs[4], .5 + p*vec2(.213,.379)).rgb;
    if (id == 2) return ink;
    // Recolor by original pigment so the different palettes keep the same
    // transparent membranes, interior folds and small edge highlights.
    vec3 core[5] = vec3[5](vec3(1.,.34,.055), vec3(.25,.34,.59), vec3(0.),
                           vec3(.02,.73,.48), vec3(.84,.19,.098));
    vec3 warm[5] = vec3[5](vec3(1.,.84,.19), vec3(.56,.71,.85), vec3(0.),
                           vec3(.49,.89,.19), vec3(1.,.58,.24));
    vec3 vein[5] = vec3[5](vec3(.96,.19,.075), vec3(.49,.40,.87), vec3(0.),
                           vec3(.10,.44,.94), vec3(.95,.11,.38));
    vec3 deep[5] = vec3[5](vec3(.10,.35,.72), vec3(.15,.23,.61), vec3(0.),
                           vec3(.12,.20,.64), vec3(.29,.12,.54));
    vec3 rim[5] = vec3[5](vec3(.22,.84,.68), vec3(.38,.83,.92), vec3(0.),
                           vec3(.21,.83,.91), vec3(.19,.73,.78));
    float peak = max(ink.r, max(ink.g, ink.b));
    float hot = smoothstep(-.16,.44,ink.r-ink.b);
    float gold = smoothstep(.17,.72,ink.g) * hot;
    float violet = smoothstep(.18,.63,ink.b-ink.g) * smoothstep(.39,.91,ink.r);
    float aqua = smoothstep(.04,.56,ink.g-ink.r*.66);
    float white = smoothstep(.50,.88,min(ink.r,min(ink.g,ink.b)));
    vec3 dye = mix(deep[id], rim[id], aqua);
    dye = mix(dye, core[id], hot);
    dye = mix(dye, warm[id], gold*.89);
    dye = mix(dye, vein[id], violet*.79);
    dye = mix(dye, whiteLight(id), white*.71);
    float light = dot(ink,vec3(.28,.60,.12));
    float shade = mix(.74,1.13,smoothstep(.16,.76,light));
    return dye * peak * shade;
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

vec3 closeupGlobe(vec2 q, int id, float beat) {
    // Use the projection and light from the standalone rotating Venus.
    vec3 normal = normalize(vec3(q,sqrt(max(0.,1.-dot(q,q)))));
    vec3 body = normal;
    body.xy = turn(.26) * body.xy;
    body.xz = turn(uView.x) * body.xz;
    body.yz = turn(uView.y-.18) * body.yz;
    vec2 front = vec2(.88*body.x + .20*body.y*body.z, .85*body.y + .20*body.z);
    vec2 rear = vec2(.84*body.x - .19*body.y*body.z,
                     .78*body.y - .28*body.z + .075*body.x);
    vec3 ink = mix(texture(sTD2DInputs[3],.5+rear*vec2(.169,.300)).rgb,
                   texture(sTD2DInputs[3],.5+front*vec2(.169,.300)).rgb,
                   smoothstep(-.30,.40,body.z));
    float fold = body.y+.38*body.x-.18*body.z+.135*sin(3.8*body.x+2.7*body.z)
                 +.064*sin(6.9*body.x-4.1*body.z);
    float warm = max(ink.r-ink.b*.72,0.);
    float belt = bell((fold-.04)/.285);
    float seam = bell((fold+.10)/.034)+.46*bell((fold-.08)/.052);
    ink = mix(ink,vec3(1.,.25,.093),belt*.25*warm);
    ink += vec3(.49,.12,.15)*seam*(.13+.27*warm);
    float longitude = dot(body,normalize(vec3(-.56,.19,.79)));
    float crest = smoothstep(.14,.88,longitude)*bell((fold-.09)/.067);
    ink = feedbackDye(mix(ink,vec3(.94,.52,.68),.48*crest),id);
    // Carry the later tutorial feedback as a light detail across the same surface.
    vec3 detail = mix(closeupInk(rear,id),closeupInk(front,id),smoothstep(-.30,.40,body.z));
    ink = mix(ink,detail,.12);

    vec3 light = normalize(vec3(-.63,.63,.59));
    float diffuse = smoothstep(-.62,.87,dot(normal,light));
    float fresnel = pow(1.-normal.z,2.75);
    float glint = pow(max(0.,dot(normal,normalize(light+vec3(0.,0.,1.)))),21.);
    vec3 air = id == 2 ? mix(vec3(.21,.14,.80),vec3(.14,.67,.97),diffuse) :
                        mix(coolTint(id),hotTint(id),.59*diffuse);
    return ink*(.25+.76*diffuse)*(1.+.06*beat) +
           whiteLight(id)*.084*glint + air*fresnel*(.27+.40*diffuse);
}

vec3 bodyLayer(vec3 background, vec2 world, vec2 cursor, vec4 body, int id,
               float visible, bool selected, float time) {
    if (visible < .002) return background;
    float transition = selected ? uTransition.x : 1.;
    float ease = smoothstep(0.,1.,transition);
    vec2 center = mix(uTransition.yz,(body.xy-uCamera.xy)*uCamera.z,ease);
    float radius = max(.001,mix(uTransition.w,body.z*uCamera.z,ease));
    vec2 q = ((world-uCamera.xy)*uCamera.z-center) / radius;
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
        float angle = atan(q.y,q.x);
        float ray = bell(r*sin(3.*angle+.04*sin(time))/.12);
        float flare = ray * smoothstep(.84,1.11,r) * bell((r-1.04)/.86);
        vec3 radiance = mix(vec3(1.,.66,.22),vec3(.15,.62,.87),smoothstep(1.,1.67,r));
        background += radiance * flare * visible * locked * (.18+.08*beat);
        if (locked < .002) return background;
    }
    if (r > 1.34) return background;
    float overviewWeight = id == 0 ? 0. : 1.-locked;
    vec3 sphere = overviewWeight > .002 ? rotateFeedback(q,id,body.w*8.5) : vec3(0.);
    // Antialias the projected sphere at a fixed pixel width on both axes.
    float edge = (r-1.)*radius*FRAME_SIZE.y;
    float silhouette = 1.-smoothstep(-.65,.65,edge);
    vec3 globe = locked*silhouette > .002 ? closeupGlobe(q,id,beat) : vec3(0.);
    float haze = bell(max(edge,0.)/max(1.35,.035*radius*FRAME_SIZE.y))*(1.-silhouette);
    background += visible*locked*mix(coolTint(id),hotTint(id),.46)*haze*(.075+.06*beat);
    float overviewMask = (1.-smoothstep(.974,1.015,r))*overviewWeight;
    float detailMask = locked*silhouette;
    return background*(1.-visible*(.94*overviewMask+detailMask)) +
           visible*(overviewWeight*sphere + detailMask*globe);
}
