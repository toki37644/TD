import fs from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const base = process.cwd();
const qa = path.join(base, '.echo-orbit', '.venus-build', 'wheel-revision');
const tmp = path.join(qa, 'slides');
const stock = path.join(base, '.echo-orbit', 'stock');
await fs.mkdir(tmp,{recursive:true});
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
const cap=(name)=>path.join(qa,'frames',name+'.png');
const cover=slide('#020308');
await img(cover,cap('0_overview'),'沿横向主轴排列的五颗天体',414,71,866,576,'contain');
text(cover,'课题','星际探索',65,163,565,60,39,C.mint);
text(cover,'作品标题','深空回声',57,225,577,128,103,C.ink,true);
text(cover,'简介','从轨道总览进入五颗天体。\n让音乐和指针带动星云。',66,408,495,114,28,C.ink);
text(cover,'制作工具','TouchDesigner 交互视听作品',67,636,475,35,20,C.soft);
note(cover,'封面使用 TouchDesigner 总览实机截图。竖版视窗中的横线从左到右依次经过太阳、水星、金星、地球和火星。');

if (process.argv.includes('--cover')) {
  const preview=await deck.export({slide:cover,format:'png',scale:1});
  await fs.writeFile(path.join(tmp,'cover.png'),new Uint8Array(await preview.arrayBuffer()));
  process.exit(0);
}

const refs=slide(C.paper);
header(refs,'灵感板',C.black);
const references=[
  {file:path.join(stock,'star-chart.jpg'),title:'暗色密轨星图',caption:'以太阳为视觉中心。\n参考侧视星图的水平主轴与刻度。',x:66,w:365},
  {file:path.join(base,'.echo-orbit','reference-flow.jpg'),title:'实时流体色束',caption:'明亮色束沿形态交叠。\n不同宽度的色带形成卷曲和余光。',x:456,w:365},
  {file:path.join(base,'.echo-orbit','reference-galaxy.jpg'),title:'星云与星尘',caption:'丝状星云构成底层。\n细颗粒与少量亮点补足深度。',x:846,w:365}];
for(const r of references){
  await img(refs,r.file,r.title,r.x,153,r.w,290,'cover');
  text(refs,r.title,r.title,r.x,465,r.w,50,30,C.black,true);
  text(refs,r.title+'注',r.caption,r.x,522,r.w,85,21,C.muted);
}
note(refs,'星图为用户提供的构图参考。色束参考 BIBIMOO_任任的流体录屏。星云参考一粒六元《宇宙诞生》。音乐驱动成形参考 mrxccc 的《音乐星球节奏互动》。完整链接与音乐署名见独立素材来源。');

const idea=slide();
header(idea,'作品简介');
text(idea,'作品思路标题','从星图进入\n五颗天体',65,156,460,161,55,C.ink,true);
text(idea,'作品思路','靠近画面边缘可平移总览。\n悬停时天体移到中央。点击后，\n天体经粒子聚散进入近景。',67,351,470,130,26,C.soft);
text(idea,'作品力学','移动指针转动球体。\n使用滚轮查看球面细节。',67,515,475,85,24,C.mint);
await img(idea,cap('interaction-328'),'金星锁定近景',551,169,665,374,'contain');
text(idea,'图注','金星近景',551,554,665,38,18,C.soft);
note(idea,'总览、太阳和四颗行星各有一段音乐。进入近景后顶部显示中英文名称。移动鼠标转动球体并吸引粒子，点击近景可以散开局部粒子。Esc 或返回图标回到总览。');

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
text(vis,'视觉对象','近景把实时反馈映射到旧版金星的球面材质。\n程序星云、远星和交互星尘分层叠加。',67,125,1150,92,28,C.soft);
const pointer=node(vis,'实时参数','orbit_engine\n轨道、镜头与频段',344,237,200,70,C.amber);
const shSrc=node(vis,'色束输入','feedback_material\ncloseup_feedback',66,345,210,84);
const sh=node(vis,'场景渲染','solar_atlas\nGLSL Multi TOP',344,345,200,84);
const hud=node(vis,'星云图层','particles / nebula_field\n实时星尘与程序星云',66,232,210,82);
const over=node(vis,'画法切换','总览自转 / 近景球体\n粒子聚散与名称显示',660,345,251,84);
const out=node(vis,'输出','out_image\n最终图像',1004,345,209,84);
edge(vis,pointer,sh,'bottom','top','straight',C.amber);edge(vis,shSrc,sh);edge(vis,sh,over);edge(vis,hud,sh,'right','top','elbow');edge(vis,over,out);
const steps=['Noise2 / Comp1\n扣出明暗轮廓','Feedback Edge\n保留边缘历史','Slope / Displace\n沿亮度坡度位移','Maximum\n与新帧叠合回灌','Lookup / 双 Edge\n着色与细亮边'];
const flow=steps.map((step,i)=>node(vis,'近景步骤 '+(i+1),step,66+i*238,500,194,70));
for(let i=1;i<flow.length;i++) edge(vis,flow[i-1],flow[i]);
text(vis,'像素实现','太阳保留放射日冕。四颗行星沿用各自的主色和冷暖关系。',67,611,1140,51,23,C.soft);
note(vis,'feedback_material 提供旧版金星的原生反馈纹理，closeup_feedback 提供补充细节。Comp1 以 Outside Luminance 扣出轮廓，Feedback1 回读 Comp3 Maximum，Level2 令旧帧衰减。solar_atlas 沿用金星演示中的球面投影与光照。nebula_field 在竖屏原生分辨率生成云层和远星，particles 单独更新可互动的近处星尘。');

const planet=slide();
header(planet,'总览与天体近景');
text(planet,'操控说明','五颗天体沿横轴排列。悬停时居中并放大，点击后进入球体近景。',67,125,1150,68,27,C.soft);
const planetViews=[
  {file:'interaction-75',title:'轨道总览',caption:'五颗天体从左到右沿同一条线排列。'},
  {file:'hover-sun',title:'悬停居中',caption:'镜头约 1 秒移到天体中央，显示英文名。'},
  {file:'interaction-328',title:'球体近景',caption:'顶部显示中英文名，移动指针转动球体。'},
];
for(const [i,view] of planetViews.entries()){
  const width=365;
  const height=274;
  const x=66+i*390;
  const y=203;
  await img(planet,cap(view.file),view.title+'的实机画面',x,y,width,height,'contain');
  text(planet,view.title,view.title,x,y+height+11,width,42,27,C.mint,true);
  text(planet,view.title+'说明',view.caption,x,y+height+60,width,62,20,C.soft);
}
note(planet,'所有图片均为 TouchDesigner 原生渲染。近景分别表现太阳的盘旋日珥、水星的窄尾流、金星的双向弯曲尘幕、地球的极光带和火星的分叉尘流。');

const palette=slide();
header(palette,'五颗天体的近景');
text(palette,'近景说明','五颗天体沿用总览的直径比例，近景共用同一放大倍率。',67,126,1150,62,27,C.soft);
const bodies=[
 ['tour-sun','太阳','橙红核心与放射日冕'],
 ['tour-mercury','水星','冷蓝断层与窄尾流'],
 ['interaction-328','金星','橙粉色束与双向尘幕'],
 ['tour-earth','地球','青蓝双层云带与暗尘'],
 ['tour-mars','火星','锈红色束与分叉尘流'],
];
for(const [i,[frame,name,description]] of bodies.entries()){
 const x=66+i*238;
 await img(palette,cap(frame),name+'近景',x,205,194,344,'contain');
 text(palette,name,name,x,567,194,42,26,C.mint,true);
 text(palette,name+'特征',description,x,615,216,34,18,C.soft);
}
note(palette,'五幅画面来自同一次 TouchDesigner 实机录制。截图按同一画幅和相同比例展示，球体直径对应总览未悬停时的尺寸。');

const interact=slide(C.paper);
header(interact,'交互方案',C.black);
const acts=[
 {x:66,t:'居中并放大',p:'停稳后镜头约 1 秒滑向天体。\n移开后镜头复位，名称消散。',f:'hover-sun',s:'悬停天体'},
 {x:456,t:'聚散进入近景',p:'天体先散开，再聚合为球体。\n顶部显示双语名称。',f:'interaction-248',s:'点击天体'},
 {x:846,t:'旋转与查看细节',p:'移动指针转动球体，星尘跟随。\n滚轮上推放大，下滚缩回。',f:'wheel-zoomed',s:'移动指针与滚动'}];
for(const a of acts){
 await img(interact,cap(a.f),a.t+'画面细节',a.x,149,365,260,'cover');
 text(interact,a.s,a.s,a.x,421,365,32,19,C.muted);
 text(interact,a.t,a.t,a.x,471,365,50,31,C.black,true);
 text(interact,a.t+'说明',a.p,a.x,535,365,80,20,C.muted);
}
note(interact,'总览指针靠近任意边缘可平移视窗。停稳约 120 毫秒后锁定，镜头约 1 秒滑向天体，沿球体扫过的路径跟随也可维持悬停。移开时延续当前镜头速度，再恢复边缘平移。近景指针坐标映射到偏航和俯仰，速度改变星尘走向与力度。按 Esc 或左上角箭头返回。');

const logic=slide();
header(logic,'交互与声音节点图');
text(logic,'实现说明','点击切换场景与音轨。实时频段和指针共同驱动粒子与色束。',67,126,1170,53,26,C.soft);
const pane=node(logic,'操作面板','viewport\n鼠标位置与按键',64,291,187,85);
const ev=node(logic,'按键边沿','点击 / 滚轮 / Esc\n进入、缩放、返回',289,291,201,85);
const rt=node(logic,'交互状态','orbit_engine\n镜头、旋转与音频分析',568,291,215,85,C.amber);
const pic=node(logic,'视觉响应','solar_atlas\n星球、散逸与星云',937,291,271,85);
const timer=node(logic,'逐帧时钟','clock\n逐帧更新',568,189,215,66,C.amber);
edge(logic,pane,ev);edge(logic,ev,rt);edge(logic,rt,pic);edge(logic,timer,rt,'bottom','top','straight',C.amber);
const osc=node(logic,'六段音频','audio_*\n总览与五颗天体',62,521,246,80,C.amber);
const gain=node(logic,'独立包络','volume_*\n逐路淡入淡出',370,521,251,80,C.amber);
const mix=node(logic,'音频混合','music_mix\n合成立体声',704,521,188,80,C.amber);
const dev=node(logic,'音频输出','audio_device\n音频设备输出',984,521,225,80,C.amber);
edge(logic,rt,gain,'bottom','top','elbow',C.amber);
text(logic,'传递的参数','切换与交叉淡入',624,423,270,38,19,C.amber);
edge(logic,osc,gain,'right','left','straight',C.amber);edge(logic,gain,mix,'right','left','straight',C.amber);edge(logic,mix,dev,'right','left','straight',C.amber);
text(logic,'声音标注','音量驱动流体谐波增益，频段与瞬态带动雾流和星尘。',65,629,1170,44,22,C.soft);
note(logic,'orbit_engine 读取同一条送入音频输出的音源，把均方根音量映射到 Noise3 的谐波增益，同时分析低频、中频、高频及瞬态。坐标、速度和点击状态进入粒子场。音轨在场景之间交叉淡入淡出。');

const demo=slide(C.paper);
header(demo,'竖版交互演示',C.black);
text(demo,'演示重点','悬停居中、球体旋转与星尘',67,129,634,53,30,C.muted);
const cue=[
  ['0–3 秒','沿画面边缘平移总览。\n悬停金星，观察居中与英文名。'],
  ['3–6 秒','点击进入金星近景。\n看双语标题，听音轨切换。'],
  ['6–13 秒','滚轮放大查看金星，再缩回。\n点左上方箭头返回。'],
  ['13–35 秒','依次进入太阳、水星、地球、火星。\n对比球面配色、星云与音轨。']];
for(let i=0;i<cue.length;i++){
  const y=213+i*96;
  text(demo,'时间 '+i,cue[i][0],68,y,153,68,28,C.black,true);
  text(demo,'操作 '+i,cue[i][1],235,y,461,68,24,C.black);
}
await img(demo,cap('wheel-zoomed'),'滚轮放大后的金星球面',717,159,494,213,'contain');
text(demo,'第一轮截图图注','滚轮放大后的金星',717,377,494,30,20,C.muted);
await img(demo,cap('tour-earth'),'地球近景的极光带',717,419,494,213,'contain');
text(demo,'第二轮截图图注','地球极光带',717,637,494,30,20,C.muted);
text(demo,'讲解提示','留意每次切换后的音乐和粒子走向。',68,620,633,47,21,C.muted);
note(demo,'可以用同一组左右划动对比金星和地球的粒子轨迹。');

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
    receipt=await finalizePresentation({workspaceDir:base,candidatePath:candidate,finalPath:stagedDeck,pythonExecutable:path.join(runtime,'python/python.exe'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:9,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:[cn]},verifyArtifactToolImport:true,receiptPath:stage+'.json'});
  } finally {
    fs.link=link;
  }
  const dest=path.join(process.argv.includes('--draft') ? tmp : base,filename);
  if(process.argv.includes('--replace')) await fs.rename(receipt.finalPath,dest);
  else await fs.copyFile(receipt.finalPath,dest,constants.COPYFILE_EXCL);
  const hash=createHash('sha256').update(await fs.readFile(dest)).digest('hex');
  if(hash!==receipt.finalSha256) throw new Error('Delivered presentation differs from the validated file.');
  console.log(JSON.stringify({path:dest,receipt:receipt.receiptPath,sha256:hash}));
}
