"""Embed the planet introduction texture and its reveal in an existing atlas."""

from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import sys


HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / '.venus-build' / 'planet-intros'
ASSET = 'planet-intros.png'
INTRO_LINES = (
    (
        '太阳是太阳系的中心恒星，为地球带来光和热。',
        '日全食时，月球遮住明亮的日面，向外伸展的',
        '白色日冕便显露出来。',
    ),
    (
        '水星是离太阳最近的行星，岩石表面布满',
        '大大小小的撞击坑。它几乎没有能留住热量的大气，',
        '白昼灼热，入夜后却极为寒冷。',
    ),
    (
        '金星常在清晨或黄昏的天空中格外明亮。',
        '云层下，富含二氧化碳的大气留住了大量热量，',
        '使它成为太阳系最热的行星。',
    ),
    (
        '从太空望去，白色云层掠过蓝色海洋，',
        '海洋覆盖了地球约七成的表面。这里也是我们目前',
        '唯一知道有生命存在的地方。',
    ),
    (
        '尘土里的铁矿物发生氧化，让火星呈现出铁锈般的',
        '红色。干涸的河谷和古老的湖床至今还保留着',
        '液态水曾在这里流动、汇聚的痕迹。',
    ),
)

STARTUP = '''from pathlib import Path
from traceback import format_exc

def onStart():
    folder = Path(project.folder)
    source = folder.parent.parent / 'live-fluids' / 'add_planet_intros.py'
    try:
        scope = dict(globals(), __file__=str(source), __name__='touchdesigner_intros')
        exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'), scope)
        scope['install']()
    except Exception:
        (folder / 'build-error.txt').write_text(format_exc(), encoding='utf-8')
    run('project.quit(force=True)', delayFrames=4)
'''


def build_texture(output):
    from PIL import Image, ImageDraw, ImageFont

    cell_width, line_height = 24, 34
    width = 24 * cell_width
    height = 3 * line_height * len(INTRO_LINES)
    coverage = Image.new('L', (width, height))
    order = Image.new('L', (width, height))
    ink = ImageDraw.Draw(coverage)
    timing = ImageDraw.Draw(order)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 21)
    for body, lines in enumerate(INTRO_LINES):
        index = 0
        last_index = sum(map(len, lines)) - 1
        for row, line in enumerate(lines):
            if len(line) * cell_width > width:
                raise ValueError(f'Introduction line is too wide: {line}')
            y = (body * 3 + row) * line_height
            for column, character in enumerate(line):
                x = column * cell_width
                ink.text((x + 1, y + 25), character, font=font, fill=255, anchor='ls')
                timing.rectangle((x, y, x + cell_width - 1, y + line_height - 1),
                                 fill=round(255 * index / last_index))
                index += 1
    Image.merge('RGB', (coverage, order, Image.new('L', (width, height)))).save(output)


def install():
    sys.path.insert(0, str(HERE))
    from build_interactive_revision import RELEASE_CLOCK, revision_shader

    scene = op('/project1')
    solar = scene.op('solar_atlas')
    source = scene.op('planet_intros')
    if source is None:
        source = scene.create(moviefileinTOP, 'planet_intros')
        names = scene.op('planet_names')
        source.nodeX, source.nodeY = names.nodeX, names.nodeY - 135
        solar.inputConnectors[5].connect(source)

    for asset in list(scene.vfs):
        if asset.name == ASSET:
            asset.destroy()
    scene.vfs.addFile(str(BUILD / ASSET), overrideName=ASSET)
    source.par.file = f'vfs:/project1:{ASSET}'
    color_space = getattr(source.par, 'inputcolorspace', None)
    if color_space is not None:
        color_space.val = 'passthrough'
    scene.op('atlas_pixel').text = revision_shader()
    scene.op('orbit_engine').text = (HERE.parent / 'orbit_runtime.py').read_text(encoding='utf-8')
    clock = scene.op('clock')
    clock.text = RELEASE_CLOCK
    clock.par.framestart = True
    root.time.play = True
    output = BUILD / 'Intro-release.toe'
    if not project.save(str(output)):
        raise RuntimeError('TouchDesigner could not save the project.')
    (BUILD / 'release.txt').write_text(str(output), encoding='utf-8')


def stage(source):
    from build_interactive_revision import TD_BIN
    from prepare_install import dat

    BUILD.mkdir(parents=True, exist_ok=True)
    build_texture(BUILD / ASSET)
    for filename in ('release.txt', 'build-error.txt'):
        (BUILD / filename).unlink(missing_ok=True)

    target = BUILD / 'Intro-stage.toe'
    with TemporaryDirectory(dir=BUILD) as temporary:
        directory = Path(temporary)
        packed = directory / target.name
        shutil.copyfile(source, packed)
        subprocess.run([str(TD_BIN / 'toeexpand.exe'), packed.name], cwd=directory)
        clock = packed.with_suffix('.toe.dir') / 'project1' / 'clock.text'
        dat(clock, STARTUP)
        parameters = clock.with_suffix('.parm')
        body = parameters.read_text(encoding='ascii')
        body = body.replace('framestart 67108864 on', 'start 67108864 on')
        parameters.write_text(body, encoding='ascii')
        subprocess.run([str(TD_BIN / 'toecollapse.exe'), packed.with_suffix('.toe.toc').name],
                       cwd=directory, check=True)
        shutil.copyfile(packed, target)
    print(target)


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Existing stable TouchDesigner project')
    stage(parser.parse_args().source)
