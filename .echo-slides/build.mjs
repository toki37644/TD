import fs from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const base = process.cwd();
const tmp = path.join(base, '.echo-slides');
const work = path.join(base, '.echo-work');
const runtime = 'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1119-907-0_26.1119.907.0_x64__3k8sg7r9htsxt/dependencies';
const skill = 'C:/Users/toki/.codex/plugins/cache/openai-primary-runtime/presentations/26.1119.11507/skills/presentations';
process.env.RUNTIME_NODE_MODULES = path.join(runtime,'node/node_modules');
const { Presentation, PresentationFile } = await import(pathToFileURL(path.join(process.env.RUNTIME_NODE_MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const deck=Presentation.create({slideSize:{width:1280,height:720}});
const C={dark:'#081519',ink:'#EFF3E9',paper:'#F0F0E7',black:'#0A2022',soft:'#B8C9C6',muted:'#536B6D',mint:'#95D8CF',amber:'#F4B374',line:'#476468'};
const cn='Microsoft YaHei';
function slide(color=C.dark){const s=deck.slides.add();s.background.fill=color;return s;}
function text(s,name,value,x,y,w,h,size,color=C.ink,bold=false,extra={}){
  const a=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  a.text=value;
  a.text.style={typeface:cn,fontSize:size,color,bold,verticalAlignment:'middle',insets:{left:0,right:0,top:0,bottom:0},...extra};
  return a;
}
async function img(s,file,alt,x,y,w,h,fit='cover'){
  const bytes=await fs.readFile(file);
  return s.images.add({blob:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),contentType:file.endsWith('.jpg')?'image/jpeg':'image/png',alt,fit,position:{left:x,top:y,width:w,height:h}});
}
function header(s,title,color=C.ink){text(s,'页标题',title,66,42,1150,68,49,color,true);}
function note(s,lines){s.speakerNotes.text=lines;}
const cover=slide();
await img(cover,path.join(work,'deep-echo-visual-active.png'),'青色星尘与琥珀色航线',0,0,1280,720);
text(cover,'课题','星际探索',65,163,565,60,39,C.mint);
text(cover,'作品标题','深空回声',57,225,577,128,103,C.ink,true);
text(cover,'简介','移动鼠标，转动星球，改变光影。\n扫描粒子星云，为航线谱曲。',66,408,520,114,28,C.ink);
text(cover,'制作工具','TouchDesigner 交互视听作品',67,636,475,35,20,C.soft);
note(cover,'移动鼠标可以转动星球并改变光照。观众在粒子星云中扫描三个信标，再按自己的顺序组成航线和旋律。封面为作品 GLSL 着色器输出。');

if (process.argv.includes('--cover')) {
  const preview=await deck.export({slide:cover,format:'png',scale:1});
  await fs.writeFile(path.join(tmp,'cover.png'),new Uint8Array(await preview.arrayBuffer()));
  process.exit(0);
}

const refs=slide(C.paper);
header(refs,'灵感板',C.black);
const references=[
  {file:'nebula.jpg',title:'船底座星云',caption:'明暗交错的尘埃边缘启发了画面里\n斜穿星场的青色雾带与星尘粒子。',x:66,w:365},
  {file:'echo.jpg',title:'麒麟座 V838 的光回声',caption:'由中心向外展开的光晕，启发了\n松开鼠标时扩散的扫描环。',x:456,w:365},
  {file:'map.jpg',title:'半人马座星图',caption:'用点标出星体，用细线连接位置。\n在作品里，点之间的连线由观众决定。',x:846,w:365}];
for(const r of references){
  await img(refs,path.join(tmp,r.file),r.title,r.x,153,r.w,290,'cover');
  text(refs,r.title,r.title,r.x,465,r.w,50,30,C.black,true);
  text(refs,r.title+'注',r.caption,r.x,522,r.w,85,21,C.muted);
}
note(refs,'左图为韦布望远镜的 NIRCam 图片 Cosmic Cliffs。图片署名 NASA, ESA, CSA, STScI。https://esawebb.org/images/weic2205a/\n中图为哈勃望远镜的 V838 Mon 光回声。图片署名 NASA, ESA and H. Bond (STScI)。https://esahubble.org/images/heic0617b/\n右图为半人马座星图。图片署名 ESO/IAU and Sky & Telescope。https://www.eso.org/public/images/eso1629g/\n三张参考图均为原始资料的局部裁切。');

const cap=(name)=>path.join(work,'captures',name+'.png');
const idea=slide();
header(idea,'作品简介');
text(idea,'作品思路标题','转动星球，\n再为航线谱曲',65,156,460,161,55,C.ink,true);
text(idea,'作品思路','鼠标移动时，星球转动，光照改变。\n观众在粒子星云中扫描三个信标，\n按自己的顺序连线并听见旋律。',67,351,470,130,26,C.soft);
text(idea,'作品力学','每个信标有固定音高，\n两种走法会奏出不同的旋律。',67,515,475,85,24,C.mint);
await img(idea,cap('07_route'),'项目运行画面，已完成的航线',551,169,665,374,'contain');
text(idea,'图注','完成一次探索后的星图',551,554,665,38,18,C.soft);
note(idea,'第一个反馈来自鼠标移动，观众可以立刻看到星球的地形、明暗分界和星尘发生变化。接着用扫描环找出信标。星图的连线顺序同时是谱序。');

function node(s,name,value,x,y,w,h,color=C.mint){
  const a=s.shapes.add({geometry:'rect',name,position:{left:x,top:y,width:w,height:h},fill:'#10262D',line:{fill:color,width:1.4}});
  a.text=value;a.text.style={typeface:cn,fontSize:19,color:C.ink,alignment:'center',verticalAlignment:'middle',insets:{left:3,right:3,top:0,bottom:0}};
  return a;
}
function edge(s,a,b,fromSide='right',toSide='left',kind='straight',color=C.mint){
  return s.shapes.connect(a,b,{fromSide,toSide,kind,line:{fill:color,width:2},tail:{type:'triangle',width:'med',length:'med'}});
}
const vis=slide();
header(vis,'视觉方案与节点图');
text(vis,'视觉对象','多层噪声和星尘粒子叠出星云。\nGLSL 根据鼠标坐标改变球体朝向和受光方向。',67,125,1150,92,28,C.soft);
const pointer=node(vis,'实时参数','uClockPointer\n时间与鼠标坐标',344,237,200,70,C.amber);
const shSrc=node(vis,'着色代码','nebula_pixel\n像素着色代码',66,345,210,84);
const sh=node(vis,'场景渲染','starfield\nGLSL TOP',344,345,200,84);
const hud=node(vis,'界面图层','hud_embedded\n内嵌界面文字',344,500,200,82);
const over=node(vis,'合成','instrument_overlay\nOver TOP',660,345,251,84);
const out=node(vis,'输出','final_image\n最终图像',1004,345,209,84);
edge(vis,pointer,sh,'bottom','top','straight',C.amber);edge(vis,shSrc,sh);edge(vis,sh,over);edge(vis,hud,over,'right','bottom','elbow');edge(vis,over,out);
text(vis,'像素实现','扫描波还会照亮经过的球面区域。星球、波纹、信标和航线都由着色器绘制。',67,611,1140,51,23,C.soft);
note(vis,'nebula_pixel 是 Text DAT。starfield 叠加多层噪声和星尘粒子，按鼠标坐标旋转球面采样空间，控制入射光、大气亮边和表面反射，并用距离函数绘制波纹、信标与航线。扫描波经过球面时带来短暂的琥珀色照明。hud_embedded 为锁定的 Null TOP，instrument_overlay 把透明界面叠加到星图上，送入 final_image。');

const planet=slide();
header(planet,'星球旋转与光影变化');
text(planet,'操控说明','横移改变星球的左右朝向，纵移改变俯仰。光照方向随指针移动。',67,125,1150,68,27,C.soft);
const planetViews=[
  {file:'planet-left',title:'指针移至左下',caption:'左侧受光，右半球进入阴影。'},
  {file:'planet-right',title:'指针移至右上',caption:'亮面向上移动，地表露出不同纹理。'},
  {file:'planet-scan',title:'扫描波经过',caption:'扫过的球面区域短暂泛起暖光。'},
];
const showScan=await fs.access(path.join(tmp,'planet-scan.png')).then(()=>true,()=>false);
const views=showScan?planetViews:planetViews.slice(0,2);
for(const [i,view] of views.entries()){
  const width=showScan?365:530;
  const height=showScan?274:398;
  const x=66+i*(showScan?390:618);
  const y=showScan?203:186;
  await img(planet,path.join(tmp,view.file+'.png'),view.title+'的实机画面',x,y,width,height,'contain');
  text(planet,view.title,view.title,x,y+height+11,width,42,27,C.mint,true);
  if(showScan) text(planet,view.title+'说明',view.caption,x,y+height+60,width,62,20,C.soft);
}
note(planet,'左、右的对比图取自相同的项目时间。鼠标的水平坐标对应绕 Y 轴旋转，垂直坐标对应绕 X 轴旋转。鼠标还改变入射光方向，因此地表亮度、昼夜交界和大气的亮边也随之移动。扫描波可短暂给经过的球面加一层暖光。');

const interact=slide(C.paper);
header(interact,'交互方案',C.black);
const acts=[
 {x:66,t:'旋转星球',p:'星球和光影随指针改变。\n指针附近的星尘也会偏移。',f:'planet-right',s:'移动鼠标'},
 {x:456,t:'扫描信标',p:'按住左键再松开。波纹经过信标时，\n信标显现，并留在星图上。',f:'scan',s:'左键长按并松开'},
 {x:846,t:'把航线弹出来',p:'依次短点三个信标，试听并连线。\n第三次选点后，探针出发，旋律回放。',f:'route',s:'依次短点信标'}];
for(const a of acts){
 await img(interact,path.join(tmp,a.f+'.png'),a.t+'画面细节',a.x,149,365,260,'cover');
 text(interact,a.s,a.s,a.x,421,365,32,19,C.muted);
 text(interact,a.t,a.t,a.x,471,365,50,31,C.black,true);
 text(interact,a.t+'说明',a.p,a.x,535,365,80,20,C.muted);
}
note(interact,'移动鼠标即可转动星球并改变光照。长按触发阈值为 0.32 秒，松开后发射扫描波。短点已发现的信标可重复试听，同一信标在航线中只记录一次。重置可点击右下角按钮或在操作窗口按 R。');

const logic=slide();
header(logic,'交互与声音节点图');
text(logic,'实现说明','鼠标位置驱动星球的旋转与光照。点击信标同时写入航线并触发声音包络。',67,126,1170,53,26,C.soft);
const pane=node(logic,'操作面板','viewport\n鼠标位置与按键',64,291,187,85);
const ev=node(logic,'按键边沿','button_edges\n按下与松开事件',289,291,201,85);
const rt=node(logic,'交互状态','runtime\n读指针、更新探索状态',568,291,215,85,C.amber);
const pic=node(logic,'视觉响应','starfield\n星球、光影、波纹与航线',937,291,271,85);
const timer=node(logic,'逐帧时钟','frame_clock\n逐帧更新时间',568,189,215,66,C.amber);
edge(logic,pane,ev);edge(logic,ev,rt);edge(logic,rt,pic);edge(logic,timer,rt,'bottom','top','straight',C.amber);
const osc=node(logic,'三个振荡器','tone_C4 / E4 / G4\n三路正弦振荡器',62,521,246,80,C.amber);
const gain=node(logic,'独立包络','envelope_C4 / E4 / G4\n逐路调节音量',370,521,251,80,C.amber);
const mix=node(logic,'音频混合','motif_mix\n合成三个音',704,521,188,80,C.amber);
const dev=node(logic,'音频输出','speaker_output\n音频设备输出',984,521,225,80,C.amber);
edge(logic,pic,gain,'bottom','top','elbow',C.amber);
text(logic,'传递的参数','uMusic 声音包络',783,423,270,38,19,C.amber);
edge(logic,osc,gain,'right','left','straight',C.amber);edge(logic,gain,mix,'right','left','straight',C.amber);edge(logic,mix,dev,'right','left','straight',C.amber);
text(logic,'声音标注','信标 A 对应 C4，B 对应 E4，C 对应 G4。三音按观众选择的顺序回放。',65,629,1170,44,22,C.soft);
note(logic,'viewport 提供鼠标 u/v 和按键。button_edges 捕捉按键的变化，frame_clock 逐帧触发 runtime 读取鼠标位置并更新探索状态。runtime 向 GLSL 写入 uClockPointer 和 uMusic。三个 Math CHOP 分别读取 uMusic 的对应分量，控制三个正弦振荡器的音量。混音后由 Audio Device Out CHOP 播放。');

const demo=slide(C.paper);
header(demo,'30 秒现场演示',C.black);
text(demo,'演示重点','星球光影和两种旋律',67,129,634,53,30,C.muted);
const cue=[
  ['0–7 秒','左右、上下移动鼠标，观察星球。\n在星云中央长按后松开，发出扫描波。'],
  ['7–15 秒','信标显现后依次点 A、B、C。\n听 C4、E4、G4 逐级升高。'],
  ['15–22 秒','点击右下角重置。\n回到星云中央，再扫描一次。'],
  ['22–30 秒','按 C、A、B 的顺序点击。\n听 G4 落到 C4，再回到 E4。']];
for(let i=0;i<cue.length;i++){
  const y=213+i*96;
  text(demo,'时间 '+i,cue[i][0],68,y,153,68,28,C.black,true);
  text(demo,'操作 '+i,cue[i][1],235,y,461,68,24,C.black);
}
await img(demo,path.join(tmp,'ascending.png'),'A、B、C 航线与亮起的 A 信标',717,159,494,213,'contain');
text(demo,'第一轮截图图注','第一轮  /  A、B、C',717,377,494,30,20,C.muted);
await img(demo,path.join(tmp,'descending.png'),'C、A、B 航线与亮起的 C 信标',717,419,494,213,'contain');
text(demo,'第二轮截图图注','第二轮  /  C、A、B',717,637,494,30,20,C.muted);
text(demo,'讲解提示','回放时，正在发声的信标会泛起光晕。',68,620,633,47,21,C.muted);
note(demo,'先以左右和上下的鼠标动作展示星球纹理和亮暗变化，接着扫描信标。两次试听时可以保持安静，让大家留意路线和信标发光的顺序。');

for(const [i,s] of deck.slides.items.entries()){
  const preview=await deck.export({slide:s,format:'png',scale:1});
  await fs.writeFile(path.join(tmp,'slide-'+(i+1)+'.png'),new Uint8Array(await preview.arrayBuffer()));
}
const candidate=path.join(tmp,'candidate.pptx');
await (await PresentationFile.exportPptx(deck)).save(candidate);
if(process.argv.includes('--validate')){
  const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
  const filename='深空回声·作品汇报.pptx';
  const stage=await fs.mkdtemp(path.join(tmp,'validated-'));
  const stagedDeck=path.join(stage,filename);
  const link=fs.link;
  let receipt;
  // The managed Windows workspace disallows hard links. Copy only this private,
  // exclusive finalizer publication, then let the finalizer verify its digest.
  fs.link=async (source,target)=>{
    if(target!==stagedDeck || path.dirname(source)!==stage) return link(source,target);
    return fs.copyFile(source,target,constants.COPYFILE_EXCL);
  };
  try {
    receipt=await finalizePresentation({workspaceDir:base,candidatePath:candidate,finalPath:stagedDeck,pythonExecutable:path.join(runtime,'python/python.exe'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:8,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:[cn]},verifyArtifactToolImport:true,receiptPath:stage+'.json'});
  } finally {
    fs.link=link;
  }
  const dest=path.join(base,filename);
  if(process.argv.includes('--replace')) await fs.rename(receipt.finalPath,dest);
  else await fs.copyFile(receipt.finalPath,dest,constants.COPYFILE_EXCL);
  const hash=createHash('sha256').update(await fs.readFile(dest)).digest('hex');
  if(hash!==receipt.finalSha256) throw new Error('Delivered presentation differs from the validated file.');
  console.log(JSON.stringify({path:dest,receipt:receipt.receiptPath,sha256:hash}));
}
