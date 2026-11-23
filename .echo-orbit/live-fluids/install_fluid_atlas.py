"""Executed once in the staged TouchDesigner network."""

from pathlib import Path
from time import monotonic
from traceback import format_exc

HERE = Path(project.folder)
LOG = HERE/"install.log"
OUTPUT = HERE/"Atlas-fluid-final.toe"
SHOW_CLOCK = '''def onStart():
    root.time.play = True

def onFrameStart(frame):
    op("/project1/orbit_engine").module.tick()
'''


def log(message):
    with LOG.open("a",encoding="utf-8") as out:
        print(message,file=out)


def check_native_views(engine_module, output):
    folder=HERE/"native"
    folder.mkdir(exist_ok=True)
    app=engine_module.atlas()
    engine_module.testing=True
    try:
        for index,name in enumerate(engine_module.SCENES):
            state=engine_module.CameraState(0.)
            state.advance(4.,(.5,.5),False)
            if index:
                target=state.center_uv(index-1)
                for frame in range(1,72):
                    state.advance(4+frame/60.,target,True)
                assert state.focus==index-1
                state.click(target)
                for frame in range(72,209):
                    state.advance(4+frame/60.,(.41,.65),True)
                assert state.entered and state.arrival==1.
                state.energy[:]=(.38,.29,.24,.14)
            app.state=state
            app.apply(force=True)
            output.cook(force=True)
            assert not output.errors(), output.errors()
            output.save(str(folder/(name+".png")))
        engine_module.testing=False
        key=op("/project1/return_key_callbacks1")
        key.module.onShortcut(op("/project1/return_key"),"escape",0)
        assert not app.state.entered
        log("PASS six native views and Escape callback")
    finally:
        app.state=engine_module.CameraState(monotonic())
        engine_module.testing=False


def proof():
    try:
        log("VALIDATING RENDER")
        parent = op("/project1")
        shader = parent.op("solar_atlas")
        module=parent.op("orbit_engine").module
        engine=module.atlas()
        engine.apply(force=True)
        output = parent.op("out_image")
        output.cook(force=True)
        for name in ("solar_atlas","body_volumes","planet_names","nebula_footage","particles","out_image"):
            node=parent.op(name)
            if node.errors():
                raise RuntimeError(f"{name}: {node.errors()}")
            log(f"{name} {node.width}x{node.height}")
        assert (shader.width,shader.height)==(1200,675)
        assert (parent.op("body_volumes").width,parent.op("body_volumes").height)==(800,1200)
        assert (parent.op("planet_names").width,parent.op("planet_names").height)==(128,280)
        assert len(parent.vfs)==9, len(parent.vfs)
        assert parent.op("viewport").par.top.eval()==output
        clock=parent.op("clock")
        clock.par.start=True
        clock.text=SHOW_CLOCK
        root.time.play=True
        log("TIMELINE PLAY "+str(root.time.play))
        project.performOnStart=True
        log("WRITING "+str(OUTPUT))
        if not project.save(str(OUTPUT)):
            raise RuntimeError("TouchDesigner could not save the project")
        log("SAVED "+str(OUTPUT))
        check_native_views(module,output)
        source=HERE.parent/"check_orbit.py"
        def schedule(script,*args,**params):
            params.setdefault("delayRef",op.TDResources)
            return run(script,*args,**params)
        scope=dict(globals(),run=schedule)
        exec(compile(source.read_text(encoding="utf-8"),str(source),"exec"),scope)
    except Exception:
        log(format_exc())


def install():
    parent=op("/project1")
    clock=parent.op("clock")
    clock.par.framestart=False
    parent.op("orbit_engine").text=(HERE.parent/"orbit_runtime.py").read_text(encoding="utf-8")
    parent.op("atlas_pixel").text=(HERE/"live_atlas.frag").read_text(encoding="utf-8")
    previous=parent.op("solar_atlas")
    previous.name="atlas_previous"
    shader=parent.create(glslmultiTOP,"solar_atlas")
    shader.nodeX,shader.nodeY=previous.nodeX,previous.nodeY
    shader.color=previous.color
    shader.par.outputresolution="custom"
    shader.par.resolutionw,shader.par.resolutionh=1200,675
    shader.par.pixeldat=parent.op("atlas_pixel").path
    names=("uCamera","uPointer","uAudio","uScene","uSun","uMercury",
           "uVenus","uEarth","uMars","uLabel","uTransition")
    shader.seq.vec.numBlocks=len(names)
    for i,name in enumerate(names):
        getattr(shader.par,f"vec{i}name").val=name
    for name in ("particles","nebula_footage"):
        parent.op(name).outputConnectors[0].connect(shader)
    for input_index,name,path in (
        (2,"planet_names",HERE.parent/"stock"/"body-names.png"),
        (3,"body_volumes",HERE/"body-volumes.png"),
    ):
        parent.vfs.addFile(str(path),overrideName=path.name)
        image=parent.create(moviefileinTOP,name)
        image.nodeX=210
        image.nodeY=100-(input_index-1)*155
        image.color=(.16,.25,.36)
        image.par.file=f"vfs:/project1:{path.name}"
        image.outputConnectors[0].connect(shader)
        if len(shader.inputs)<=input_index or shader.inputs[input_index]!=image:
            raise RuntimeError(f"Could not attach {name} on GLSL input {input_index}")
    parent.op("out_image").inputConnectors[0].connect(shader)
    previous.destroy()
    op("/perform").par.title="深空回声"
    clock.text=SHOW_CLOCK
    clock.par.framestart=True
    log("NETWORK INSTALLED")
    proof()


LOG.write_text("START\n",encoding="utf-8")
try:
    install()
except Exception:
    log(format_exc())
