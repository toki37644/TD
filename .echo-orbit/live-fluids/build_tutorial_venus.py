"""Build the editable Venus study in a dedicated TouchDesigner staging project.

Reference: mrxccc, https://www.bilibili.com/video/BV1pkRiYpEZh/
02:35 circle and noise, 04:51 Feedback Edge, 06:32–08:33 slope feedback,
10:31 color lookup, 15:03 edge treatment, 19:07 audio modulation.
"""

from functools import partial
from pathlib import Path


WIDTH, HEIGHT = 1280, 720
PALETTE = (
    (0.00, .000, .000, .000),
    (0.035, .006, .015, .080),
    (0.075, .026, .14, .53),
    (0.108, .017, .35, .89),
    (0.140, .035, .73, .96),
    (0.182, .105, .91, .98),
    (0.205, .29, .93, .99),
    (0.228, .94, .80, .96),
    (0.248, 1.00, .29, .72),
    (0.278, .95, .034, .40),
    (0.335, .88, .014, .22),
    (0.495, 1.00, .19, .025),
    (0.76, 1.00, .33, .036),
    (1.00, 1.00, .40, .049),
)


def place(node, x, y):
    node.nodeX, node.nodeY = x, y
    return node


def make_node(scene, kind, name, x, y, *inputs, **settings):
    node = place(scene.create(kind, name), x, y)
    for index, source in enumerate(inputs):
        node.inputConnectors[index].connect(source.outputConnectors[0])
    for parameter, value in settings.items():
        field = node.par[parameter]
        if field is None:
            raise AttributeError(f'{node.path} has no {parameter} parameter')
        if isinstance(value, tuple) and value[0] == 'expr':
            field.expr = value[1]
        else:
            field.val = value
    return node


def build_feedback_material(scene, power, harmonics, resolution):
    make = partial(make_node, scene)
    width, height = resolution
    size = dict(outputresolution='custom', resolutionw=width, resolutionh=height)
    # Circle → grain displacement → animated noise mask → Palette Feedback Edge.
    circle = make(circleTOP, 'circle1', -1080, 160, **size,
                  radiusx=.188, radiusy=.188, borderalpha=0, bgalpha=0)
    grain = make(noiseTOP, 'noise1', -1080, -55, **size,
                 type='random', mono=False, seed=13)
    seed = make(displaceTOP, 'displace1', -850, 160, circle, grain,
                displaceweight1=.002, displaceweight2=.0035, extend='zero')
    mask = make(noiseTOP, 'noise2', -850, -55, **size,
                period=1.70, harmon=2, spread=2, gain=.70, amp=.41, offset=.66,
                tz=('expr', 'absTime.seconds * .29'), sx=.72, sy=.72)
    mask_level = make(levelTOP, 'level1', -635, -55, mask, gamma1=1.13, contrast=1.0)
    masked = make(compositeTOP, 'comp1', -410, 160, seed, mask_level, operand='multiply')
    palette_file = Path(app.samplesFolder) / 'Palette' / 'ImageFilters' / 'feedbackEdge.tox'
    palette_wrapper = scene.loadTox(str(palette_file))
    feedback_edge = place(scene.copy(palette_wrapper.op('feedbackEdge')), -185, 160)
    palette_wrapper.destroy()
    feedback_edge.inputConnectors[0].connect(masked)
    feedback_edge.par.Scale = 1.006
    feedback_edge.par.Sourcegain = .57
    feedback_edge.par.Feedbackgain = 1.025
    feedback_edge.par.Blursource = 2
    feedback_edge.par.Blurfeedback = 3
    feedback_edge.par.Edgestrength = .62
    rotation = make(transformTOP, 'transform1', 70, 160, feedback_edge,
                    rotate=('expr', 'absTime.seconds * 8.0'), extend='zero')
    source = make(nullTOP, 'null1', 290, 160, rotation)

    # The two Slope TOPs and displaced previous frame produce the fluid folds.
    feedback = make(feedbackTOP, 'feedback1', 505, 320, source)
    slope_x = make(slopeTOP, 'slope1', 740, 130, feedback,
                   red='hluminance', green='neutral', blue='neutral', alpha='one', method='prevnext')
    slope_y = make(slopeTOP, 'slope2', 740, -30, feedback,
                   red='neutral', green='neutral', blue='vluminance', alpha='one', method='prevnext')
    flow_noise = make(noiseTOP, 'noise3', 740, 315, feedback,
                      period=.49, harmon=7, spread=2.0, amp=.34, mono=False,
                      gain=('expr', f'.38 + .22 * ({harmonics} - .50)'),
                      tz=('expr', 'absTime.seconds * .22'))
    flow = make(compositeTOP, 'comp2', 970, 160, flow_noise, slope_x, slope_y,
                operand='average')
    displaced = make(displaceTOP, 'displace2', 1185, 320, feedback, flow, extend='zero',
                     displaceweight1=('expr', f'.102 + .202 * {power}'),
                     displaceweight2=('expr', f'.145 + .318 * {power}'))
    feedback_level = make(levelTOP, 'level2', 1360, 320, displaced, brightness2=1.009)
    # Refresh a little of the input every frame so bright folds do not accumulate to solid red.
    refresher = make(crossTOP, 'feedback_refresh', 1535, 320, feedback_level, source, cross=.052)
    matte = make(blurTOP, 'soft_outline', 1380, 10, source, size=28)
    combine = make(compositeTOP, 'comp3', 1620, 160, refresher, matte, operand='multiply')
    feedback.par.top = refresher.path
    keyboard = make(keyboardinCHOP, 'keyboardin1', 505, 510, keys='r')
    feedback.par.reset.expr = "op('keyboardin1')[0]"

    colors = make(tableDAT, 'venus_colors', 1620, -195)
    for position, r, g, b in PALETTE:
        colors.appendRow([position, r, g, b, 1])
    ramp = make(rampTOP, 'ramp1', 1840, -195, dat=colors.path, type='horizontal',
                outputresolution='custom', resolutionw=1024, resolutionh=1)
    smooth = make(blurTOP, 'smooth_lookup_input', 1770, 160, combine, size=2.25)
    palette = make(lookupTOP, 'lookup1', 1935, 160, smooth, ramp)
    vivid = make(hsvadjustTOP, 'hsvadj1', 2100, 160, palette, saturationmult=1.03)
    grade = make(levelTOP, 'level3', 2280, 160, vivid, gamma1=.88)
    color = make(nullTOP, 'null3', 2490, 160, grade)
    edges = make(edgeTOP, 'edge1', 2710, 340, color, select='luminance',
                 strength=.29, edgecolorr=.48, edgecolorg=.62, edgecolorb=1.0)
    combined_edges = make(compositeTOP, 'comp4', 2930, 160, color, edges, operand='add')
    texture = make(noiseTOP, 'noise4', 2710, -155, **size, period=.41, harmon=5,
                   tz=('expr', 'absTime.seconds * .116'))
    texture_level = make(levelTOP, 'level6', 2930, -155, texture, opacity=.128)
    finish = make(compositeTOP, 'comp6', 3150, 160, combined_edges, texture_level,
                  operand='outsideluminance')
    return make(transformTOP, 'transform2', 3370, 160, finish, sx=1.03, sy=1.03,
                 bgcolora=1, compover=True, extend='zero')


def build(audio_file, *, rotation_source=None):
    scene = op('/project1')
    make = partial(make_node, scene)
    size = dict(outputresolution='custom', resolutionw=WIDTH, resolutionh=HEIGHT)
    scene.vfs.addFile(str(audio_file), overrideName='venus-demo.mp3')
    audio = make(audiofileinCHOP, 'audiofilein1', -1080, -430,
                 file='vfs:/project1:venus-demo.mp3', playmode='sequential', repeat=True)
    make(audiodeviceoutCHOP, 'audiodevout1', -855, -580, audio)
    analysis = make(analyzeCHOP, 'analyze1', -855, -430, audio, function='rmspower')
    drive = make(mathCHOP, 'math1', -630, -370, analysis, chanop='avg')
    detail = make(mathCHOP, 'math2', -630, -510, analysis, chanop='avg')
    drive.par.torange1, drive.par.torange2 = .12, 1.86
    detail.par.torange1, detail.par.torange2 = .50, 2.0
    make(nullCHOP, 'null4', -415, -370, drive)
    make(nullCHOP, 'null5', -415, -510, detail)
    power = "float(op('null4')[0])"
    harmonics = "float(op('null5')[0])"

    final = build_feedback_material(scene, power, harmonics, (WIDTH, HEIGHT))
    keyboard = scene.op('keyboardin1')
    if rotation_source is not None:
        scene.vfs.addFile(str(rotation_source.with_name('nebula-test.png')),
                          overrideName='venus-nebula.png')
        nebula = make(moviefileinTOP, 'nebula_texture', 3370, -195,
                      file='vfs:/project1:venus-nebula.png')
        pixel = make(textDAT, 'rotation_fragment', 3600, -195)
        pixel.text = rotation_source.read_text(encoding='utf-8')
        globe = make(glslTOP, 'rotating_venus', 3600, 160, final, nebula,
                     pixeldat=pixel.path, **size)
        globe.seq.vec.numBlocks = 1
        globe.par.vec0name = 'uMotion'
        globe.par.vec0valuex.expr = 'absTime.seconds'
        globe.par.vec0valuey.expr = 'absTime.seconds * .61'
        globe.par.vec0valuez.expr = f'min(1., max(0., ({power} - .12) * 1.65))'
        globe.par.vec0valuew = .89
        final = globe
    output = make(nullTOP, 'out_image', 3830, 160, final)
    output.viewer = True
    panel = make(containerCOMP, 'viewport', 3830, -80, w=WIDTH, h=HEIGHT,
                 top=output.path, topfill='off')
    panel.viewer = True
    scene.par.top = output.path
    op('/perform').par.winop = panel.path
    op('/perform').par.title = '深空回声 · 金星'
    project.performOnStart = False
    root.time.play = True
    return output, audio, keyboard
