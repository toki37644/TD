import ctypes as c, os,sys,pathlib,struct,zlib
p=next(pathlib.Path('C:/Users/toki/AppData/Local/Programs/Microsoft VS Code').glob('*/libEGL.dll')).parent
dep=os.add_dll_directory(str(p)); e=c.WinDLL(str(p/'libEGL.dll')); g=c.WinDLL(str(p/'libGLESv2.dll'))
I,U,P,F,S=c.c_int,c.c_uint,c.c_void_p,c.c_float,c.c_char_p
def register(lib,ns,decl):
 for spec in decl.split(';'):
  name,types=spec.split();f=getattr(lib,ns+name); r,*a=[{'i':I,'u':U,'p':P,'f':F,'s':S,'v':None}[x] for x in types]
  f.restype=r;f.argtypes=a;globals()[name]=f
register(e,'egl','GetDisplay pp;Initialize uppp;ChooseConfig upppip;CreatePbufferSurface pppp;CreateContext ppppp;MakeCurrent upppp;GetError i;BindAPI uu')
register(g,'gl','CreateShader uu;ShaderSource vuipp;CompileShader vu;GetShaderiv vuup;GetShaderInfoLog vuipp;CreateProgram u;AttachShader vuu;LinkProgram vu;GetProgramiv vuup;GetProgramInfoLog vuipp;UseProgram vu;Viewport viiii;DrawArrays vuii;ReadPixels viiiiuup;GetUniformLocation ius;Uniform4f viffff')
arr=lambda *x:(I*len(x))(*x)
d=GetDisplay(None);assert Initialize(d,None,None),hex(GetError());BindAPI(0x30a0)
co=P();n=I(); assert ChooseConfig(d,arr(0x3033,1,0x3040,0x40,0x3024,8,0x3023,8,0x3022,8,0x3038),c.byref(co),1,c.byref(n)) and n.value
w,h=1200,675
s=CreatePbufferSurface(d,co,arr(0x3057,w,0x3056,h,0x3038));ct=CreateContext(d,co,None,arr(0x3098,3,0x3038));assert MakeCurrent(d,s,s,ct),hex(GetError())
def shader(ty,src):
 sh=CreateShader(ty);dat=S(src.encode());ShaderSource(sh,1,c.byref(dat),None);CompileShader(sh);q=I();GetShaderiv(sh,0x8b81,c.byref(q))
 if not q.value:
  log=c.create_string_buffer(4096);GetShaderInfoLog(sh,4096,None,log);raise Exception(log.value)
 return sh
pr=CreateProgram();AttachShader(pr,shader(0x8b31,'#version 300 es\nout vec2 vUV;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);vUV=p;gl_Position=vec4(p*2.-1.,0.,1.);}'))
AttachShader(pr,shader(0x8b30,'#version 300 es\nprecision highp float;precision highp int;in vec2 vUV;\n#define TDOutputSwizzle(x) x\n'+pathlib.Path('.echo-work/deep_echo.frag').read_text()))
LinkProgram(pr);q=I();GetProgramiv(pr,0x8b82,c.byref(q))
if not q.value:
 log=c.create_string_buffer(4096);GetProgramInfoLog(pr,4096,None,log);raise Exception(log.value)
UseProgram(pr); vals=[('uClockPointer',(2.,.75,.54,0.)),('uPulse',(0.,0.,0.,0.)),('uFlags',(0.,0.,0.,0.)),('uRoute',(-1.,-1.,-1.,0.))]
if len(sys.argv)>1: vals=[('uClockPointer',(4.,.70,.68,1.)),('uPulse',(.63,.66,.27,.85)),('uFlags',(1.,1.,1.,.7)),('uRoute',(1.,0.,2.,.34)),('uMusic',(.6,0.,0.,0.))]
for n,v in vals:Uniform4f(GetUniformLocation(pr,n.encode()),*v)
Viewport(0,0,w,h);DrawArrays(4,0,3);buf=c.create_string_buffer(w*h*4);ReadPixels(0,0,w,h,0x1908,0x1401,buf);raw=buf.raw
def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b))
out=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+raw[k*w*4:(k+1)*w*4] for k in reversed(range(h)))))+chunk(b'IEND',b'')
pp=pathlib.Path('.echo-work')/('deep-echo-visual'+('-active' if len(sys.argv)>1 else '')+'.png');pp.write_bytes(out);print(pp)
