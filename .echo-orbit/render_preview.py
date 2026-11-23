"""Render the native shader offscreen with the same particle field for visual QA."""
import cv2
import numpy as np
from pathlib import Path

from orbit_runtime import CameraState, ParticleField, SCENES


workspace = Path(__file__).resolve().parents[1]
work = Path(__file__).parent
legacy = (workspace / '.echo-work/shader_qa.py').read_text(encoding='utf-8')
exec(legacy.split('pr=CreateProgram()')[0])
register(g, 'gl', 'GenTextures vip;BindTexture vuu;TexParameteri vuui;TexImage2D vuiiiiiiup')
program = CreateProgram()
AttachShader(program, shader(0x8B31, '#version 300 es\nout vec2 vUV;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);vUV=p;gl_Position=vec4(p*2.-1.,0.,1.);}'))
AttachShader(program, shader(0x8B30, '#version 300 es\nprecision highp float;precision highp int;in vec2 vUV;\nuniform sampler2D sTD2DInputs[1];\n#define TDOutputSwizzle(x) x\n' + (work / 'solar_atlas.frag').read_text(encoding='utf-8')))
LinkProgram(program)
success = I()
GetProgramiv(program, 0x8B82, c.byref(success))
if not success.value:
    errors = c.create_string_buffer(8192)
    GetProgramInfoLog(program, len(errors), None, errors)
    raise RuntimeError(errors.value)

UseProgram(program)
texture = U()
GenTextures(1, c.byref(texture))
BindTexture(0x0DE1, texture.value)
TexParameteri(0x0DE1, 0x2801, 0x2601)
TexParameteri(0x0DE1, 0x2800, 0x2601)
field = ParticleField()
identifiers = [GetUniformLocation(program, name.encode()) for name in
               ('uCamera', 'uPointer', 'uAudio', 'uScene', 'uSun', 'uMercury', 'uVenus', 'uEarth', 'uMars')]
frames = []
out = work / 'offscreen'
out.mkdir(exist_ok=True)
for i, name in enumerate(SCENES):
    scene = CameraState(0.)
    scene.focus = scene.shown = i - 1
    scene.entered = i > 0
    scene.energy[:] = (.49, .42, .35, .38) if i else 0
    for frame in range(1, 121):
        scene.advance(frame / 60, (.73, .61), i > 0)
    for loc, values in zip(identifiers, scene.uniforms()):
        Uniform4f(loc, *values)
    rgba = field.render(scene)
    TexImage2D(0x0DE1, 0, 0x1908, rgba.shape[1], rgba.shape[0], 0, 0x1908, 0x1401, rgba.ctypes.data)
    Viewport(0, 0, w, h)
    DrawArrays(4, 0, 3)
    buffer = np.zeros((h, w, 4), np.uint8)
    ReadPixels(0, 0, w, h, 0x1908, 0x1401, buffer.ctypes.data)
    bgr = cv2.cvtColor(buffer[::-1], cv2.COLOR_RGBA2BGR)
    (out / f'{i}_{name}.jpg').write_bytes(cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, 93])[1].tobytes())
    frames.append(cv2.resize(bgr, (400, 225), interpolation=cv2.INTER_AREA))
grid = np.vstack((np.hstack(frames[:3]), np.hstack(frames[3:])))
(out / 'grid.jpg').write_bytes(cv2.imencode('.jpg', grid, [cv2.IMWRITE_JPEG_QUALITY, 93])[1].tobytes())
print(out)
