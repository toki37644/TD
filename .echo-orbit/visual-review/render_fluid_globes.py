"""Render smooth volume-colored spheres and a separate particle release preview."""

import argparse
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from render_abstract_planets import ROOT, SCENES, SHARES, font, rgb, splat
from render_bundle_planets import Bundles, FFMPEG


OUT = ROOT / "流体色束星球"
BG = rgb("030408")
GRID = 76
LIMIT = 1.27
LIGHT = np.array([-.55, .49, .67], dtype=np.float32)
LUMA = np.array([.2126,.7152,.0722],dtype=np.float32)


def smooth(value):
    t = np.clip(value, 0, 1)
    return t*t*(3-2*t)


def saturation(color, amount):
    luminance = (color[...,0]*LUMA[0]+color[...,1]*LUMA[1]+color[...,2]*LUMA[2])[...,None]
    return np.maximum(0,luminance+(color-luminance)*amount[...,None])


def contour(index, angle):
    phase = (0.7, 2.1, 3.3, 1.8, 5.4)[index]
    amplitude = (.041,.039,.059,.041,.053)[index]
    shoulder = .064*np.exp(13*(np.cos(angle-.89*phase)-1))
    hollow = .035*np.exp(8*(np.cos(angle-.89*phase-1.2)-1))
    return (
        .99 + amplitude*np.sin(3*angle+phase)
        + .016*np.cos(5*angle+.6*phase) + .009*np.sin(8*angle+phase)
        + .038*np.sin(angle*2-.72*phase) + shoulder-hollow
    )


def volume(index):
    clouds = Bundles(index, 480_000)
    points, _ = clouds.points(.22)
    # Accumulate whole bundles in a volume. The five density masses follow the
    # same fixed proportions, independent of the camera and lighting.
    freqs = np.fft.fftfreq(GRID)
    squared = freqs[:,None,None]**2 + freqs[None,:,None]**2 + freqs[None,None,:]**2
    # A wider, fainter copy carries one pigment across the edge of the next.
    kernel = .70*np.exp(-2*np.pi**2*1.38**2*squared)
    kernel += .30*np.exp(-2*np.pi**2*3.65**2*squared)
    channels = []
    for p, weight in zip(points, SHARES):
        x,y,z = p.T.copy()
        # A coherent shear curls the bundle borders without adding grain.
        p[:,0] += .043*np.sin(8*y+3.2*x-3*z+.6*index)+.013*np.sin(18*y+4*z)
        p[:,1] += .033*np.sin(9*x-2.8*z+4.4*y)+.017*np.sin(17*x+12*y)
        p[:,2] += .021*np.sin(7*x-5*y+3*z)
        cells = np.clip(((p+LIMIT)*(GRID-1)/(2*LIMIT)+.5).astype(int), 0, GRID-1)
        flat = (cells[:,0]*GRID+cells[:,1])*GRID+cells[:,2]
        distribution = np.bincount(flat, minlength=GRID**3).reshape((GRID,)*3)
        field = np.fft.ifftn(np.fft.fftn(distribution)*kernel).real
        field = np.maximum(0,field) * ((weight/10)*GRID**3/len(p))
        channels.append(field.astype(np.float32))
    pigments = np.stack(channels, axis=-1)
    colors = pigments@clouds.palette
    density = pigments.sum(axis=-1,keepdims=True)
    strongest = pigments.max(axis=-1,keepdims=True)
    return np.concatenate((colors,density,strongest),axis=-1).reshape(-1,5)


def sample(field, x, y, z):
    scale = (GRID-1)/(2*LIMIT)
    a, b, c = ((v+LIMIT)*scale for v in (x,y,z))
    ix, iy, iz = (v.astype(np.int32) for v in (a,b,c))
    dx, dy, dz = ((v-i.astype(v.dtype))[:,None] for v,i in ((a,ix),(b,iy),(c,iz)))
    offset = (ix*GRID+iy)*GRID+iz
    stride = GRID*GRID
    front = (field[offset]*(1-dz)+field[offset+1]*dz)*(1-dy)
    front += (field[offset+GRID]*(1-dz)+field[offset+GRID+1]*dz)*dy
    back = (field[offset+stride]*(1-dz)+field[offset+stride+1]*dz)*(1-dy)
    back += (field[offset+stride+GRID]*(1-dz)+field[offset+stride+GRID+1]*dz)*dy
    return front*(1-dx)+back*dx


def solar_arch(width, height, radius, center_y, palette):
    # A broad return flow and a narrower strand emerge from the same rim.
    paths = (
        ((-.956,.20),(-1.19,.98),(-.60,1.63),(-.205,.87)),
        ((-.916,.24),(-1.11,.90),(-.54,1.47),(-.256,.89)),
        ((-.938,.24),(-1.03,.66),(-.87,1.21),(-.66,.88)),
    )
    left, right = np.array(palette[1]),np.array(palette[2])
    ras = np.zeros((height,width,3),dtype=np.float32)
    ts = np.linspace(0,1,152,dtype=np.float32)
    for level,path in enumerate(paths):
        a,b,c,d = np.asarray(path)
        u = 1-ts
        xy = u[:,None]**3*a+3*(u*u*ts)[:,None]*b+3*(u*ts*ts)[:,None]*c+ts[:,None]**3*d
        for t,(x,y) in zip(ts[1:-1],xy[1:-1]):
            fade = np.sin(np.pi*t)**.71
            cx, cy = width/2+x*radius,center_y-y*radius
            spread = (.012+.014*np.sin(np.pi*t)**2)*radius*(.94-.17*level)
            margin = int(3.6*spread+1)
            i0,i1 = max(0,int(cx)-margin),min(width,int(cx)+margin+1)
            j0,j1 = max(0,int(cy)-margin),min(height,int(cy)+margin+1)
            gx,gy = np.ogrid[j0:j1,i0:i1]
            d2 = ((gy-cx)**2+(gx-cy)**2)/spread**2
            chroma = .16+.65*fade*(.77+.23*np.sin(5*t+.4))
            color = (left*(1-chroma)+right*chroma)*.68 + .32*palette[0]
            lamp = (.068-.015*level)*fade*np.exp(-.54*d2)
            ras[j0:j1,i0:i1] += lamp[...,None]*color
    return (1-np.exp(-1.26*ras))


def globe(index, width, height, radius, yaw=0):
    material = volume(index)
    colors = np.array([rgb(c) for c in SCENES[index][2]],dtype=np.float32)
    center_y = height*(.542 if index==0 else .5)
    x, y = np.meshgrid((np.arange(width)+.5-width/2)/radius,
                       (center_y-np.arange(height)-.5)/radius)
    theta = np.arctan2(y,x)
    profile = contour(index,theta)
    x,y = x/profile, y/profile
    rr = np.hypot(x,y)
    feather = .018+.032*(.5+.5*np.sin(3*theta+.84*index))**2
    alpha = 1-smooth((rr-1+.46*feather)/feather)
    visible = alpha>0
    sx, sy = x[visible].astype(np.float32),y[visible].astype(np.float32)
    flow = np.sin(7.5*sy+3.1*sx+1.2*np.sin(5.1*sx+.4*index))
    front = np.sqrt(np.clip(1-sx*sx-sy*sy,0,1))
    half_width = np.maximum(.010,front)
    steps = 46
    softness = 1/steps
    through = np.ones(len(sx), np.float32)
    radiance = np.zeros((len(sx),3),np.float32)
    cs, sn = np.float32(np.cos(yaw)), np.float32(np.sin(yaw))
    for step in range(steps):
        z = half_width*(1-2*(step+.5)*softness)
        q = sample(material,cs*sx+sn*z,sy,-sn*sx+cs*z)
        density = q[:,3]
        fill = 1-np.exp(-density*half_width*(2.7*softness))
        divisor = np.maximum(density,1.e-7)
        color = q[:,:3]/divisor[:,None]
        dominant = q[:,4]/divisor
        core = smooth((density-.60)/5)
        tint = .59+.43*core+.15*dominant-.11*smooth((z+.1)/.94)
        color = saturation(color,tint)
        local_light = np.clip(.79+.24*sy-.21*sx+.14*z+.10*flow*(.43+.57*core),.40,1.12)
        radiance += color*(through*fill*local_light)[:,None]
        through *= 1-fill
    dot = LIGHT[0]*sx+LIGHT[1]*sy+LIGHT[2]*front
    light = .18+.75*smooth((dot+.61)/1.60)+.12*np.maximum(dot,0)
    matte = BG*.5 + colors[0]*.13+colors[1]*.048
    main = (radiance + (through*.82+.18)[:,None]*matte)*light[:,None]
    # Light rises toward the bundle shoulders, with a softer roll-off in the highlights.
    peak = main.max(axis=-1)
    main *= (1/(.88+.22*peak))[:,None]
    haze = np.exp(-((front-.153)/.165)**2) * (.08+.175*np.clip(dot+.38,0,1))
    horizon = (.51*colors[0]+.29*colors[1]+.20*colors[3])
    main += horizon*haze[:,None]
    # A broad illumination lobe gives the fluid sphere a rounded highlight.
    sheen = np.exp(-((sx+.48)**2+(sy-.48)**2)/.16)*.059
    main += np.array([.83,.87,1.0])*sheen[:,None]
    exterior = np.exp(-np.maximum(rr-1,0)/(feather*.94)) * (1-alpha)
    exterior *= np.clip(.48-.25*x+.31*y,.14,.92) * .13
    result = BG + exterior[...,None]*horizon
    result[visible] += np.clip(main,0,1)**.90*alpha[visible,None]
    if index==0:
        arch = solar_arch(width,height,radius,center_y,colors)
        result += arch*(1-result)
    return Image.fromarray(np.uint8(255*np.clip(result,0,1)))


def stills(solar_only=False):
    width,height = 2128,1370
    board = Image.new("RGB",(width,height),"#0b1018")
    draw = ImageDraw.Draw(board)
    title = font("msyhbd.ttc",51)
    label = font("msyhbd.ttc",30)
    small = font("msyh.ttc",21)
    draw.text((51,25),"流体色束星球",font=title,fill="#eef2fa")
    draw.text((1780,60),"完整球体  /  五色配方",font=small,fill="#a5afc0")
    draw.line((51,107,2077,107),fill="#2a3344",width=2)
    images = []
    for i, (name,_,palette,*_) in enumerate(SCENES):
        path = OUT/(name+".png")
        if solar_only and i:
            with Image.open(path) as previous:
                image = previous.copy()
        else:
            image = globe(i,900,680,292 if i==0 else 282,yaw=(.15,-.08,.09,.18,-.12)[i])
            image.save(path)
        images.append(image)
        x,y = 51 + (i%3)*684,128+(i//3)*596
        draw.text((x,y),name,font=label,fill="#eef2fa")
        board.paste(image.resize((660,499),Image.Resampling.LANCZOS),(x,y+52))
        at = x
        for amount,color in zip(SHARES,palette):
            draw.rectangle((at,y+565,at+66*amount-1,y+575),fill="#"+color)
            at += 66*amount
    x,y = 1419,724
    draw.text((x,y),"球面局部",font=label,fill="#eef2fa")
    draw.text((x+145,y+7),"金星",font=small,fill="#a5afc0")
    patch = images[2].crop((162,95,560,396)).resize((660,499),Image.Resampling.LANCZOS)
    board.paste(patch,(x,y+52))
    board.save(OUT/"五颗天体·完整球体.png")


def render_release():
    index = 2
    width,height = 1056,720
    radius = 217
    fps, duration = 24,5.5
    planet = np.asarray(globe(index,width,height,radius,.09),np.float32)/255
    # Use the same colored volumes as sources for released particles.
    cloud = Bundles(index,104_000)
    initial, power = cloud.points(.22)
    p = np.concatenate(initial)
    base_power = np.concatenate(power)
    color = np.repeat(cloud.palette, cloud.size, axis=0)
    rng = np.random.default_rng(310)
    jitter = rng.normal(0,1,p.shape).astype(np.float32)
    rate = rng.uniform(.67,1.26,len(p)).astype(np.float32)
    seed = rng.random(len(p)).astype(np.float32)
    delay = np.clip(.22+.23*p[:,0]-.09*p[:,1]+.22*seed,0,.63)
    angle = np.arctan2(p[:,1],p[:,0])
    p[:, :2] *= contour(index,angle)[:,None]
    opening = .36*np.sin(angle*3+.4)+.25*np.cos(angle*5-1.6)
    xx,yy = np.meshgrid((np.arange(width)-width/2)/radius,(height/2-np.arange(height))/radius)
    key = .38+.23*xx-.12*yy + .085*np.sin(4.5*xx-2*yy+.8*np.sin(5*yy))
    key += .033*np.cos(11*xx+6*yy+3*np.sin(4*yy))
    key = np.clip(key,0,1).astype(np.float32)
    output = OUT/"金星·球体散为星云.webm"
    cmd = [str(FFMPEG),"-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
           "-s",f"{width}x{height}","-r",str(fps),"-i","-","-an","-c:v","libvpx-vp9",
           "-crf","17","-b:v","0","-cpu-used","5","-row-mt","1","-pix_fmt","yuv420p",str(output)]
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as encoder:
        for frame in range(round(duration*fps)):
            t = frame/fps
            time = np.clip((t-1.03)/3.55,0,1)
            release = np.clip((time-delay*.63)/.74,0,1)
            billow = np.sin(release*1.59)
            swivel = billow*(.58+.72*p[:,2]+.49*np.sin(angle*2))
            grow = 1+billow*(.58*rate+opening*.36+p[:,2]*.11)
            side = grow*(p[:,0]*np.cos(swivel)-p[:,1]*np.sin(swivel))
            rise = grow*(p[:,0]*np.sin(swivel)+p[:,1]*np.cos(swivel))
            side += jitter[:,0]*billow**1.12*.162
            rise += jitter[:,1]*billow**1.08*.114 + .05*billow
            in_view = (np.abs(side)<width/2/radius-.02)&(np.abs(rise)<height/2/radius-.02)
            px = width/2+radius*side[in_view]
            py = height/2-radius*rise[in_view]
            ignition = smooth(release/.13)
            glow = (ignition*(.36+.62*billow)*base_power*(.25+3.10*seed**10))[in_view]
            raster = np.zeros((height*width,3),np.float32)
            splat(raster,px,py,color[in_view]*glow[:,None],width,height)
            raw = raster.reshape(height,width,3)
            near = Image.fromarray(np.uint8(255*(1-np.exp(-raw))))
            cloudlight = np.asarray(near.filter(ImageFilter.GaussianBlur(11)),dtype=np.float32)/255
            haze = np.asarray(near.filter(ImageFilter.GaussianBlur(27)),dtype=np.float32)/255
            light = 2.12*raw+4.1*cloudlight+3.25*haze
            peak = light.max(axis=-1)
            energy = light/(.59+peak[...,None])
            energy = saturation(energy,.57+.46*smooth(peak/.85))
            coverage = 1-smooth((time-key+.13)/.36)
            solid = BG+(planet-BG)*coverage[...,None]
            picture = np.maximum(BG, solid)+energy**.82*(1-solid)
            encoder.stdin.write(np.uint8(255*np.clip(picture,0,1)).tobytes())
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("Video encoding failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode",choices=("stills","solar","release"))
    mode = parser.parse_args().mode
    OUT.mkdir(exist_ok=True)
    if mode=="release":
        render_release()
    else:
        stills(solar_only=(mode=="solar"))
