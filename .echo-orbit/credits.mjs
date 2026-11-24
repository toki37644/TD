import fs from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const workspace = process.cwd();
const work = path.join(workspace, '.echo-orbit');
const scratch = path.join(work,'.venus-build','sphere-revision','credits');
await fs.mkdir(scratch,{recursive:true});
const runtime = 'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1119-907-0_26.1119.907.0_x64__3k8sg7r9htsxt/dependencies';
const skill = 'C:/Users/toki/.codex/plugins/cache/openai-primary-runtime/presentations/26.1119.11507/skills/presentations';
const modules = path.join(runtime, 'node/node_modules');
process.env.RUNTIME_NODE_MODULES = modules;
const { Presentation, PresentationFile } = await import(pathToFileURL(path.join(modules, '@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const { finalizePresentation } = await import(pathToFileURL(path.join(skill, 'container_tools/artifact_tool_utils.mjs')).href);
const presentation = Presentation.create({slideSize: {width: 1280, height: 720}});
const slide = presentation.slides.add();
slide.background.fill = '#12101C';
const font = 'Microsoft YaHei';
const ink = '#F4EFFF';
const subtle = '#BCB7CF';
const lavender = '#CCB4F3';

const visual = [
  {title:'TD 星际环游 003／宇宙诞生', artist:'一粒六元。', use:'星云运动与星尘构图参考', file:'reference-galaxy.jpg', url:'https://xhslink.cn/o/4iQnld9ohQ6'},
  {title:'TD 实时流体艺术', artist:'BIBIMOO_任任', use:'流体卷曲与颗粒边缘', file:'reference-flow.jpg', url:'https://xhslink.cn/o/8PmEOGMYmdJ'},
];

const tracks = [
  ['总览', 'Computations in a Snowstorm', '00:15–00:39', 'computations'],
  ['太阳', 'Aphelion', '01:46–02:10', 'aphelion'],
  ['水星', 'Machina', '01:59–02:23', 'machina'],
  ['金星', 'Petrichor', '02:35–02:59', 'petrichor'],
  ['地球', 'Childhood', '00:02–00:26', 'childhood'],
  ['火星', 'Resonance', '00:14–00:38', 'resonance'],
];

function type(name, value, x, y, width, height, size, color = ink, bold = false, link) {
  const box = slide.shapes.add({name, geometry:'textbox', position:{left:x,top:y,width,height},
    fill:'none',line:{fill:'none',width:0}});
  box.text = value;
  box.text.style = {typeface:font,fontSize:size,color,bold,verticalAlignment:'middle',
    insets:{left:0,top:0,right:0,bottom:0}};
  if (link) box.hyperlink = {uri:link,isExternal:true};
}

type('标题', '深空回声 · 素材来源', 62, 52, 1130, 74, 51, ink, true);
type('视觉参考', '视觉参考', 65, 158, 465, 41, 29, lavender, true);
type('音乐栏标题', '音乐 / Scott Buckley', 562, 158, 648, 41, 29, lavender, true);

for (const [i, ref] of visual.entries()) {
  const y = 222 + i * 152;
  const image = await fs.readFile(path.join(work, ref.file));
  slide.images.add({name:ref.title,blob:image.buffer.slice(image.byteOffset,image.byteOffset+image.byteLength),
    contentType:'image/jpeg',alt:ref.title,fit:'cover',position:{left:65,top:y,width:168,height:119},
    hyperlink:{uri:ref.url,isExternal:true}});
  type('参考标题 '+i, ref.title, 251, y+4, 283, 33, 21, ink, true, ref.url);
  type('参考作者 '+i, ref.artist, 251, y+45, 272, 31, 18, subtle);
  type('参考用途 '+i, ref.use, 251, y+82, 278, 29, 17, subtle);
}
type('音乐星球教程', '天体材质  mrxccc《音乐星球节奏互动》', 65, 500, 472, 30, 17, lavender, false,
  'https://www.bilibili.com/video/BV1pkRiYpEZh/');
type('音画构思参考', '音画笔记  Vivi S《TD 宇宙回响》', 65, 532, 472, 30, 17, lavender, false,
  'https://xhslink.cn/o/7NuVmtgTRWx');
type('首页参考', '首页构图  用户提供的横轴星图、暗色星图与录屏', 65, 564, 472, 30, 17, lavender);
type('背景星云视频', '高清星云  Colin Jones / Pexels', 65, 596, 472, 30, 17, lavender, false,
  'https://www.pexels.com/video/digital-animation-of-a-spinning-galaxy-15562120/');

for (const [i, [scene, title, range, id]] of tracks.entries()) {
  const y = 221 + i * 54;
  const url = `https://www.scottbuckley.com.au/library/${id}/`;
  type('场景 '+i, scene, 563, y, 66, 39, 20, lavender, true);
  type('曲目 '+i, title, 646, y, 365, 39, 21, ink, false, url);
  type('片段 '+i, range, 1046, y, 155, 39, 18, subtle);
}
type('总览混音', '总览使用 No Cello 混音。曲名与参考标题可点击。', 563, 551, 650, 31, 17, subtle);
type('使用说明', '音乐按 CC BY 4.0 署名。星云视频来自 Pexels。球面、星尘与交互由 TouchDesigner 实时运行。',
  65, 632, 1130, 42, 19, subtle, false, 'https://www.scottbuckley.com.au/library/using-this-music/');

slide.speakerNotes.text = [
  ...visual.map(ref=>`${ref.title}，${ref.artist}，小红书。${ref.url}。图截自用户提供的录屏。`),
  '近景天体反馈链参考 mrxccc《TouchDesigner 教程｜音乐星球节奏互动》。按公开画面重建 Outside Luminance 底图、Maximum 回灌和双 Edge 合成，金星色标按成品画面调配。太阳、水星、地球和火星在同一套实时材质上使用各自的配色。https://www.bilibili.com/video/BV1pkRiYpEZh/',
  '音画构思参考，Vivi S《TD 宇宙回响》。https://xhslink.cn/o/7NuVmtgTRWx',
  '新版近景星云使用 Colin Jones 的 Digital Animation of a Spinning Galaxy，1920×1080。按天体重新取景、调色并叠加实时星尘。https://www.pexels.com/video/digital-animation-of-a-spinning-galaxy-15562120/ 。Pexels 许可 https://www.pexels.com/license/ 。',
  '竖版总览的横向天体排列参考用户提供的侧视星图，原作者未标注。长条尘带、太阳粒子弧和特写粒子参考用户提供的图片与录屏。',
  '粒子实现参考，Bileam Tschepe《粒子扭曲效果》（授权中文教程）。https://www.bilibili.com/video/BV1ye4y1m7iv/ 。音乐频段映射参考《Audioreactive Particle Cloud》。https://www.elekktronaut.com/tutorials/audioreactive-particle-cloud-new 。',
  ...tracks.map(([scene, title, range, id])=>`${scene}：${title} by Scott Buckley (CC BY 4.0), ${range}. https://www.scottbuckley.com.au/library/${id}/`),
  '总览使用 Computations in a Snowstorm 的 No Cello 混音。所有片段均为 24 秒，做了截取、淡入淡出和音量调整。CC BY 4.0 https://creativecommons.org/licenses/by/4.0/ 。作者使用说明 https://www.scottbuckley.com.au/library/using-this-music/ 。',
].join('\n');

const preview = await presentation.export({slide,format:'png',scale:1});
await fs.writeFile(path.join(scratch, 'credits-preview.png'), new Uint8Array(await preview.arrayBuffer()));
const candidate = path.join(scratch, 'credits-candidate.pptx');
await (await PresentationFile.exportPptx(presentation)).save(candidate);
const filename = '深空回声·素材来源.pptx';
const validationDir = await fs.mkdtemp(path.join(scratch, 'sources-validated-'));
const stagedDeck = path.join(validationDir, filename);
const link = fs.link;
fs.link = async (from, to) => {
  if (to !== stagedDeck || path.dirname(from) !== validationDir) return link(from, to);
  // Hard links are disabled in this Windows workspace. Preserve exclusive creation.
  return fs.copyFile(from, to, constants.COPYFILE_EXCL);
};
let result;
try {
result = await finalizePresentation({
  workspaceDir:workspace,
  candidatePath:candidate,
  finalPath:stagedDeck,
  pythonExecutable:path.join(runtime,'python/python.exe'),
  integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],
  explicitTotalSlideCount:1, requiredNativeTableOwnerSlides:[], requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:'design',families:[font]}, verifyArtifactToolImport:true,
  receiptPath:validationDir + '.json'
});
} finally {
  fs.link = link;
}
const output = path.join(process.argv.includes('--draft') ? scratch : workspace, filename);
await fs.copyFile(result.finalPath, output, process.argv.includes('--replace') ? 0 : constants.COPYFILE_EXCL);
if (createHash('sha256').update(await fs.readFile(output)).digest('hex') !== result.finalSha256) {
  throw new Error('Delivered slide differs from the validated file');
}
console.log(output);
