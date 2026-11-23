"""Offline look-development plates. World space is in planet radii."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "天体粒子样张"
OUT.mkdir(exist_ok=True)
W, H, R = 1160, 820, 252
CX, CY = 558, 415
PI = np.pi
sin, cos = np.sin, np.cos
clip = lambda x: np.clip(x, 0, 1)


def rgb(hexcode):
    return np.array([int(hexcode[i:i+2], 16) / 255 for i in (0, 2, 4)])


def mix(first, second, t):
    t = clip(np.asarray(t))[..., None]
    return first * (1-t) + second*t


def unit(vec):
    return vec / np.maximum(np.linalg.norm(vec, axis=-1, keepdims=True), 1e-9)


def sph(u, v, radius=1):
    return np.column_stack((sin(u)*cos(v), sin(v), cos(u)*cos(v))) * np.asarray(radius)[...,None]


def tilt(p, a):
    x,y,z = p.T
    return np.column_stack((x*cos(a)-y*sin(a), x*sin(a)+y*cos(a), z))


def sample_shell(rng, n):
    u = rng.uniform(-PI, PI, n)
    v = np.arcsin(rng.uniform(-1, 1, n))
    return u, v, sph(u, v)


def waves(x,y,z):
    a=2.6*x+1.1*sin(3*y-2*z)
    b=3.1*y+.8*sin(3*z+.8*x)
    return .5*sin(2.3*a+1.4*b+1.6*z)+.28*sin(4.1*b-2.4*a+1.7*z)+.16*sin(4*a+4*b+3*z)


class Field:
    def __init__(self, seed):
        self.r = np.random.default_rng(seed)
        self.buf = np.zeros((H*W, 3), np.float32)
        self.xx, self.yy = np.meshgrid((np.arange(W)-CX)/R, (CY-np.arange(H))/R)
        self.rr = np.hypot(self.xx,self.yy)

    def dots(self, px, py, color, power):
        px, py, power = np.broadcast_arrays(px, py, power)
        color = np.broadcast_to(color, (px.size,3))
        px, py, power = px.ravel(), py.ravel(), power.ravel()
        i = (px>1)&(px<W-2)&(py>1)&(py<H-2)&(power>.001)
        px,py,col = px[i],py[i], color[i]*power[i,None]
        ix,iy = px.astype(int),py.astype(int)
        dx,dy = px-ix,py-iy
        n = iy*W+ix
        for off,wt in ((0,(1-dx)*(1-dy)),(1,dx*(1-dy)),(W,(1-dx)*dy),(W+1,dx*dy)):
            np.add.at(self.buf, n+off, (wt[:,None]*col).astype(np.float32))

    def at(self, p, color, power, buried=.07):
        x,y,z = p.T
        cover = (z<0) & (x*x+y*y<.985)
        self.dots(CX+R*x,CY-R*y,color, power*np.where(cover,buried,1))

    def sky(self, tint, direction):
        r=self.r
        h=self.rr
        bg=np.zeros((H,W,3),float)+rgb('04060b')
        rim=np.exp(-((h-1.01)/.21)**2) * (.65+.25*self.yy)
        bg+=np.maximum(0,rim)[...,None]*tint*.026
        bg+=np.exp(-((self.xx*.42)**2+(self.yy*.56)**2))[...,None]*rgb('05080c')
        bg*=1-.45*np.minimum(1,h/3)[...,None]
        self.bg=bg
        n=4200
        x=r.uniform(2,W-3,n); y=r.uniform(2,H-3,n)
        visible=np.hypot((x-CX)/R,(y-CY)/R)>1
        self.dots(x,y,mix(rgb('7998ba'),tint,r.uniform(0,.38,n)),r.pareto(4.2,n)*.52*visible)
        # Suspended ambient dust, with most of the frame left unlit.
        n=18500
        t=r.uniform(-2.6,2.6,n)
        e=r.normal(0,1,n)
        y=(.18*sin(2.3*t+direction)+.15*t+.46+e*(.12+.10*cos(3*t)**2))
        p=tilt(np.column_stack((t,y,np.zeros(n)-1)),direction)
        self.at(p,tint,(.014+r.random(n)**4*.16)*clip(abs(t)*.85),0)

    def base(self, col, lum=.4, radius=1, rough=.002, n=98000):
        u,v,p=sample_shell(self.r,n)
        x,y,z=p.T
        w=waves(x,y,z)
        light=clip(.58+.43*(-.72*x+.63*y+.28*z))
        rim=(1-np.abs(z))**3
        rad=radius+rough*(self.r.normal(0,.5,n)+w)
        self.at(p*rad[:,None], col,lum*(.14+light**2+.9*rim)*(.18+self.r.random(n)**3*2.5)*(.8+.58*w),.055)

    def image(self):
        lum=self.buf.reshape(H,W,3)
        photons=1-np.exp(-lum)
        raw=Image.fromarray(np.uint8(255*clip(photons)))
        near=np.asarray(raw.filter(ImageFilter.GaussianBlur(2.3)))/255
        far=np.asarray(raw.filter(ImageFilter.GaussianBlur(12)))/255
        wide=np.asarray(raw.filter(ImageFilter.GaussianBlur(29)))/255
        hdr=lum + .42*near + .53*far + .28*wide
        col=self.bg+(1-self.bg)*(1-np.exp(-hdr))**.92
        return Image.fromarray(np.uint8(255*clip(col)))


def sun(f):
    r=f.r; yellow=rgb('ffd781'); orange=rgb('ec5718'); red=rgb('b12f1d')
    f.sky(rgb('f18838'),-.55)
    u,v,p=sample_shell(r,270000)
    x,y,z=p.T
    # Distorted convection cells generate fronts of concentrated granules.
    u3=p*5.6
    u3+=.29*np.column_stack((sin(6*y+2*z),sin(5*z-3*x),sin(5*x+4*y)))
    a=np.floor(u3).astype(int); b=u3-a
    d1=np.full(len(p),30.); d2=d1.copy()
    for i in (-1,0,1):
        for j in (-1,0,1):
            for k in (-1,0,1):
                c=a+[i,j,k]
                h0=c[:,0]*127.1+c[:,1]*311.7+c[:,2]*74.7
                jitter=np.stack([(sin(h0+offset)*43758.5453)%1 for offset in (1,7,22)],axis=1)
                diff=np.array([i,j,k])+.22+.56*jitter-b
                dist=np.sum(diff**2,axis=1)
                d2=np.minimum(d2,np.maximum(d1,dist)); d1=np.minimum(d1,dist)
    network=np.exp(-((d2-d1)/.15)**2)
    w=waves(x,y,z)
    hot=clip(.55+.55*y-.35*x+.50*w)
    col=mix(mix(red,orange,hot),yellow,clip(.75*network+.38*hot**2))
    f.at(p*(1+.0025*w)[:,None],col,(.16+.4*hot+1.15*network)*(.17+r.random(len(p))**2*1.8)*(.58+.45*(1-abs(z))**2),.045)
    # Magnetic coronal loops have two anchored feet and an open pocket beneath.
    for ang,size,height,skew in [(2.22,.36,.36,-.08),(1.98,.19,.18,-.06),(.52,.18,.14,.04),(-.78,.22,.23,.05),(-2.54,.13,.10,-.03)]:
        n=int(28000*height/.32)
        t=r.random(n)*PI; bundle=r.normal(size=n)
        normal=np.array([cos(ang),sin(ang)]); tangent=np.array([-sin(ang),cos(ang)])
        h=.975+(height+.035*bundle)*sin(t)**1.02
        along=(size+.026*bundle)*cos(t)+skew*sin(t)+.028*sin(3*t)
        turb=(.003+.014*sin(t))*(r.normal(size=n)+.6*sin(14*t+bundle))
        xy=(h+turb)[:,None]*normal+along[:,None]*tangent
        core=np.exp(-1.4*(bundle+.36*sin(5*t))**2)
        f.at(np.column_stack((xy,.22*cos(t))),mix(red,yellow,.18+.71*core),(.18+.79*core)*(.16+1.25*r.random(n)**2))
    n=12000; a=r.uniform(-PI,PI,n); dist=1+r.exponential(.055,n)
    f.at(np.column_stack((cos(a)*dist,sin(a)*dist,np.ones(n)*.1)),orange,(.14+r.pareto(3,n)*.75)*clip(2-dist))


def mercury(f):
    r=f.r; ice=rgb('dce9ff'); silver=rgb('9bb0c8'); stone=rgb('7d6f76')
    f.sky(rgb('98accc'),.88)
    craters=[(-.48,.19,.275),(.31,.51,.13),(.45,-.21,.205),(-.19,-.49,.089),(-.92,-.23,.17),
             (.98,.22,.105),(-.08,.82,.10),(.13,.0,.065),(-.89,.55,.083),(.59,-.62,.067),
             (-.45,-.20,.046),(.05,.38,.054),(-.10,-.14,.045),(.53,.16,.049),(.83,-.17,.075)]
    centers=[(unit(np.array([x,y,np.sqrt(max(.02,1-x*x-y*y))])),rad) for x,y,rad in craters]
    u,v,p=sample_shell(r,205000)
    x,y,z=p.T; light=clip(.43-.68*x+.55*y+.12*z); w=waves(x,y,z)
    dust=(.16+.84*light)*(.33+.74*clip(.48+w))*(.24+r.random(len(p))**3*1.9)
    for c,rad in centers:
        sep=np.sqrt(np.maximum(0,2-2*(p@c)))
        dust*=.62+.38*clip((sep-rad*.78)/(rad*.25))
    f.at(p,mix(stone,silver,clip(.53+w)),dust,.06)
    for j,(c,rad) in enumerate(centers):
        east=unit(np.cross(c,[0.,1.,0.])); north=unit(np.cross(east,c))
        n=int(48000*rad)
        ang=r.uniform(-PI,PI,n); e=r.normal(size=n)
        warp=1+.034*sin(5*ang+j)+.033*sin(3*ang-j)+.018*sin(11*ang)
        ring=rad*warp*(1+.079*e)
        tangent=cos(ang)[:,None]*east+sin(ang)[:,None]*north
        p=unit(c+ring[:,None]*tangent)*(1+.009*rad/.21*np.exp(-e**2))[:,None]
        light=clip(.40-.46*tangent[:,0]+.52*tangent[:,1])
        broken=clip(.46+.36*sin(3*ang+j)+.22*sin(9*ang-j)+.17*sin(22*ang))
        importance=.26+.72*min(1,rad/.24)
        f.at(p,mix(stone,ice,light),importance*(.10+.95*light**2)*(.16+1.35*r.random(n)**2)*(.08+.92*broken))
        # Gravel washes into the bowl, revealing a sloping crater floor.
        n=int(40000*rad)
        a=r.uniform(-PI,PI,n); q=np.sqrt(r.random(n))
        tan=cos(a)[:,None]*east+sin(a)[:,None]*north
        inside=unit(c+rad*q[:,None]*tan)
        floorlight=clip(.32+.53*tan[:,0]-.52*tan[:,1])
        f.at(inside,mix(stone,silver,.66*floorlight),(.03+.49*floorlight*q*q)*(.12+r.random(n)**4*1.65))
        # Impact ejecta break into small splinters and diverge radially.
        rays=r.uniform(-PI,PI,38)
        n=int(rad*27000); a=r.choice(rays,n)+r.normal(0,.026,n)
        q=r.exponential(.24,n); q=np.minimum(q,1.5)
        rad2=rad*(1+q); tangent=cos(a)[:,None]*east+sin(a)[:,None]*north
        p=unit(c+rad2[:,None]*tangent)*(1.007+.012*q)[:,None]
        f.at(p,silver,(1-q*.65)*(.11+r.random(n)**4*.8))
    # A little vaporized rock peels off the sunward edge.
    n=6700;t=r.random(n)*1.38; lane=r.integers(0,8,n)
    x=-.76-.67*t; y=.60+.08*t+.035*lane*t+.043*sin(4*t+lane*.43)
    y+=r.normal(0,.018+.075*t,n)
    f.at(np.column_stack((x,y,np.ones(n)*.32)),silver,(.09+r.random(n)**4*.8)*np.exp(-1.6*t))


def venus(f):
    r=f.r; plum=rgb('935d98'); rose=rgb('ed918c'); silk=rgb('ffdda7')
    f.sky(plum,-.32); f.base(plum,.36,n=108000)
    for index,(lat,width,phase,amp) in enumerate([(-.61,.37,-1.2,.26),(.00,.43,.8,.35),(.61,.29,2.0,.23)]):
        n=131000; u=r.uniform(-PI,PI,n); s=r.uniform(-1,1,n)
        v=lat+amp*sin(1.65*u+phase)+.12*sin(3*u-.9+phase)+width*s
        roll=3.0*u+3.4*s+phase+1.1*sin(1.9*u-2*s)
        radial=.944+.101*sin(roll)+.036*cos(2*roll+u)+.035*s
        v+=.105*sin(roll+1.3*s)
        p=tilt(sph(u,v,radial+r.normal(0,.004,n)),.24)
        edge=np.exp(-((s+.90-.06*sin(3*u+phase))/.088)**2)
        crest=clip(.45+.55*cos(roll+.5))
        ribs=(.5+.5*cos(29*s+.45*sin(4*u)))**8
        light=clip(.72-.27*p[:,0]+.17*p[:,1])
        vcolor=mix(plum,rose,.22+.54*crest+.28*(s+1)/2)
        col=mix(vcolor,silk,.82*edge+.24*crest**3)
        intensity=(.17+.48*crest**2+.85*edge+.20*ribs)*(.18+1.6*r.random(n)**2)*light
        f.at(p,col,intensity,.12)
    # Detached silk threads follow the direction of the surface pleats.
    for side in (-1,1):
        n=14000;t=r.random(n); v=r.normal(0,1,n)
        x=side*(.73+.76*t); y=side*(.12+.13*t+.16*sin(4.6*t))+.002*v+.045*v*t
        y+=.05*sin(5*t+v*.7)*t
        f.at(np.column_stack((x,y,np.zeros(n)-.25)),mix(plum,rose,r.random(n)),(.13+.7*r.random(n)**3)*(1-t)**.8,.01)


def earth(f):
    r=f.r; blue=rgb('355bd2'); lilac=rgb('9880ce'); sea=rgb('30cdae'); ice=rgb('b8f9f4')
    f.sky(rgb('747eb9'),.36); f.base(blue,.45,rough=.004,n=175000)
    # Broken coast-like chains become visible on the dark cobalt globe.
    u,v,p=sample_shell(r,168000); x,y,z=p.T; g=waves(x,y,z)+.09*sin(22*x+13*y+7*z)
    fil=np.exp(-((g-.22)/.088)**2)
    f.at(p*1.002,mix(blue,sea,.12+.56*fil),(.035+.83*fil)*(.15+r.random(len(p))**2*1.6),.03)
    # Polar curtain. Each column has a fixed foot, a luminous lower hem and a fading upper end.
    for j,(lat,offset,phase) in enumerate([(.28,0.,.4),(.44,.016,1.1)]):
        n=154000 if j==0 else 91000
        strand=r.integers(0,1270,n); u=strand/1270*2*PI-PI+r.normal(0,.0014,n)
        h=r.beta(.66,1.36,n)
        base=lat+.25*sin(2.7*u+phase)+.085*sin(5.1*u-.4)
        top=.32+.18*sin(4*u+1.6)**2+.15*clip(sin(7*u+.7))
        v=base+h*top+.012*r.normal(size=n)
        rad=1.012+offset+h*(.09+.17*sin(2.2*u+phase)**2)
        p=tilt(sph(u+.10*h,v,rad),-.49)
        hem=np.exp(-(h/.11)**2)
        rib=(.5+.5*cos(strand*.38+1.8*sin(u*11)))**4
        col=mix(mix(sea,lilac,clip((h-.44)*1.85)),ice,hem*.56+.21*rib)
        f.at(p,col,(.24+.88*hem+.64*rib)*(1-.75*h)*(.2+r.random(n)**2*1.46),.1)
    # A thin broken atmospheric rim catching cool light.
    n=27000; a=r.uniform(-PI,PI,n); h=r.normal(1.002,.005,n)
    lit=clip(.32+.45*sin(a)-.28*cos(a))
    f.at(np.column_stack((h*cos(a),h*sin(a),np.ones(n)*.05)),mix(blue,ice,lit),lit**2*(.25+r.random(n)))


def mars(f):
    r=f.r; clay=rgb('af302b'); ember=rgb('f46a39'); sand=rgb('ffa76b')
    f.sky(rgb('b37366'),-.7)
    u,v,p=sample_shell(r,203000); x,y,z=p.T
    w=waves(x,y,z); light=clip(.56-.52*x+.45*y)
    channel=v+.23*sin(2.6*u+.6)-.12*sin(5.2*u-.6)+.1
    subchannel=channel-.12-.09*sin(3.5*u)
    valley=np.minimum(1-np.exp(-(channel/.086)**2),.2+.8*(1-np.exp(-(subchannel/.041)**2)))
    dune=clip(.5+.5*cos(20*v+4*sin(3.3*u)+5*w))**8
    c=mix(clay,ember,clip(.22+.45*w+.38*dune))
    c=mix(c,sand,.35*light*dune)
    # The coarse grains are little asymmetric chips with their own lit tip.
    power=(.12+.94*light)*(.21+r.random(len(p))**4*2.2)*(.52+.75*dune)*valley
    f.at(p,c,power,.06)
    large=(r.random(len(p))<.115)&(z>0)
    for dx,dy,atten in [(1.1,.25,.53),(-.55,-.8,.48),(.15,.75,.34)]:
        f.dots(CX+R*x[large]+dx,CY-R*y[large]+dy,c[large],power[large]*atten)
    # An oblique dust storm peels away in separate ballistic fans.
    for j,(x0,y0,length,bend,fan) in enumerate([(-.55,-.19,2.44,.17,.48),(-.36,-.31,2.13,.22,.27),(-.11,-.36,1.74,.32,.16)]):
        n=61500 if j==0 else 29000
        t=r.beta(1.55,1.73,n); lane=r.integers(0,37,n)
        k=lane/36+r.normal(0,.012,n)
        spread=.012+.018*sin(PI*t)**2+.064*t**2
        x=x0+length*t+.035*r.normal(size=n)+.13*(k-.5)
        y=y0+bend*t+fan*k*(.23+.90*sin(PI*t)**1.7)+.20*sin(2.4*PI*t-.9)-.05*t*t
        y+=.029*sin(9*t+.24*lane)+r.normal(0,1,n)*spread
        col=mix(clay,sand,clip(.18+.46*(1-k)+.25*sin(9*t+j)))
        power=(.09+r.random(n)**3*1.09)*(.24+.84*sin(PI*t)**1.35)*(.4+.64*(.5+.5*cos(.62*lane+j))**2)
        f.at(np.column_stack((x,y,np.ones(n)*.65)),col,power)
        big=r.random(n)<.14
        f.dots(CX+R*x[big]+1,CY-R*y[big]-.4,col[big],power[big]*.59)


NAMES=['太阳','水星','金星','地球','火星']
FORMS=['日珥弧环','陨坑与溅射','卷曲云褶','极光帘幕','风蚀沙尘']
COLORS=['f7bf77','b8c9db','f0b6ae','7bd4c2','efa676']
CROPS=[(328,83),(332,265),(348,319),(478,194),(663,354)]


def build():
    imgs=[]
    for i,render in enumerate((sun,mercury,venus,earth,mars)):
        f=Field(9847+i*101)
        render(f)
        im=f.image()
        im.save(OUT/(NAMES[i]+'.png'))
        imgs.append(im)
    board(imgs)


def font(name,sz):
    return ImageFont.truetype('C:/Windows/Fonts/'+name,sz)


def board(imgs):
    # Each right panel is an actual crop from its adjacent full view.
    w,h=1952,904; bg='#090d14'; muted='#9caab9'
    sheet=Image.new('RGB',(w,h),bg); d=ImageDraw.Draw(sheet)
    regular=font('msyh.ttc',23); bold=font('msyhbd.ttc',46)
    d.text((45,28),'天体粒子形态',font=bold,fill='#e8edf1')
    d.text((1544,55),'深空回声  /  粒子近景研究',font=regular,fill=muted)
    d.line((46,112,w-46,112),fill='#303b48',width=2)
    d.text((46,592),'局部放大',font=regular,fill=muted)
    for i,im in enumerate(imgs):
        left=46+i*376
        d.text((left,143),NAMES[i],font=font('msyhbd.ttc',34),fill='#edf1f2')
        d.text((left+91,156),FORMS[i],font=regular,fill='#'+COLORS[i])
        # Lock projected diameter across all five looks.
        overview=im.crop((157,0,977,820)).resize((356,356),Image.Resampling.LANCZOS)
        sheet.paste(overview,(left,207))
        x,y=CROPS[i]
        detail=im.crop((x,y,x+236,y+150)).resize((356,226),Image.Resampling.LANCZOS)
        sheet.paste(detail,(left,640))
    sheet.save(OUT/'五体形态与局部.png',optimize=True)


if __name__=='__main__':
    build()
