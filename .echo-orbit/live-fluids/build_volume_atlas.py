"""Pack the procedural dye volumes into a TOP-friendly 2D slice sheet."""

from pathlib import Path
import sys

import numpy as np
from PIL import Image

WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(WORK.parent / "visual-review"))
from render_flame_globes import make_volume


def main():
    size = 48
    pitch = size+2
    columns, rows = 16, 24
    sheet = np.zeros((rows*pitch, columns*pitch, 3), np.uint8)
    for planet in range(1,5):
        raw = make_volume(planet, size).astype(np.float32)
        density = raw[...,3]
        pigment = raw[...,:3]/np.maximum(density[...,None],1e-7)
        depth = np.broadcast_to(np.sqrt(density[...,None]/(5+density[...,None])),pigment.shape)
        for channel, section in enumerate((pigment,depth)):
            for layer, image in enumerate(section):
                number=layer+(planet-1+channel*4)*size
                y,x=divmod(number,columns)
                tile=np.pad(image,((1,1),(1,1),(0,0)),mode="edge")
                sheet[y*pitch:(y+1)*pitch,x*pitch:(x+1)*pitch]=np.uint8(255*np.clip(tile,0,1)+.5)
    Image.fromarray(sheet).save(WORK/"body-volumes.png",optimize=True)


if __name__=="__main__":
    main()
