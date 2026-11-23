from pathlib import Path

from PIL import Image


staging = Path(__file__).resolve().parent
captures = staging.parent / '.echo-work' / 'captures'


def crop(name, state, bounds):
    with Image.open(captures / f'{state}.png') as capture:
        capture.crop(bounds).save(staging / f'{name}.png')


crop('hover', '02_hover', (442, 160, 908, 492))
crop('scan', '04_scan', (372, 70, 1117, 601))
crop('route', '06_motif', (393, 78, 1132, 605))

if (captures / '08_alternate_route.png').is_file():
    route_bounds = (342, 86, 1162, 439)
    crop('ascending', '08_alternate_route', route_bounds)
    crop('descending', '06_motif', route_bounds)

planet_bounds = (816, 72, 1200, 360)
for name, state in (
    ('planet-left', '09_planet_left'),
    ('planet-right', '10_planet_right'),
    ('planet-scan', '11_planet_scanlight'),
):
    if (captures / f'{state}.png').is_file():
        crop(name, state, planet_bounds)
    elif (captures / f'{name}.png').is_file():
        crop(name, name, planet_bounds)
