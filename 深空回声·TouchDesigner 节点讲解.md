# 深空回声 TouchDesigner 节点讲解

打开 [深空回声-彩雾交互版.toe](深空回声-彩雾交互版.toe)，进入 `/project1`。作品的交互由一份 Python 状态脚本统一管理。五路 TOP 图像汇入一个 GLSL Multi TOP，六路立体声通过各自的音量节点合成。球体、星云、星尘和标题在同一张 720 × 1280 的画面中渲染。

[完整交互演示](深空回声·完整交互演示.mp4)有可见的指针、点击波纹和滚轮方向标记。下面用工程里的原节点名讲搭建顺序，附录列出保存于工程中的节点、连线和常用参数引用。

## 先看整条链

```text
鼠标进入 viewport → left_click / wheel_zoom / escape_to_overview
键盘 Esc → return_key → return_key_callbacks1
clock → orbit_engine → 镜头与交互状态、粒子像素、材质参数、音量与频段

particles             ── 输入 0 ┐
nebula_field          ── 输入 1 │
planet_names          ── 输入 2 ├→ solar_atlas → out_image → viewport → /perform
feedback_material/out1 ─ 输入 3 │
closeup_feedback/out1 ── 输入 4 ┘

audio_各场景 → volume_各场景 → music_mix → audio_device
```

图像线接 TOP，音频线接 CHOP。点击脚本、GLSL 源码、Feedback Target 和窗口显示的来源通过参数引用设置。读网络时，可以先看右侧参数页，再判断有哪些依赖没有画成连线。

## 1. 窗口、鼠标和键盘

| 节点 | 怎么搭、接到哪里 |
| --- | --- |
| `/project1` Base COMP | 放入作品的图像、音频和控制节点。内部 VFS 嵌入六段 MP3 和名称图集，参数中用 `vfs:/project1:文件名` 读取。 |
| `out_image` Null TOP | 接 `solar_atlas`。这是供窗口、预览和录制共用的最终画面口。 |
| `viewport` Container COMP | 宽 720、高 1280，背景 TOP 指向 `out_image`。启用 **Use Mouse Wheel**。脚本从这里读 `inside` 和 `insideu/insidev`，点击时取 `u/v`。TD 的 V 轴从下往上。 |
| `/perform` Window COMP | 将 **Window Operator** 设为 `/project1/viewport`，窗口水平、垂直居中。关闭窗口的 **Close on Escape**，让 Esc 交给作品的返回事件。 |
| `clock` Execute DAT | 启动后让时间轴播放。启用 **Frame Start**，每帧调用 `orbit_engine.module.tick()`。 |
| `left_click` Panel Execute DAT | **Panels** 指向 `viewport`，**Panel Value** 设 `lselect`，开启 **Off to On**。按下左键时执行 `orbit_engine.module.click()`。总览负责进入，近景按点击位置区分返回和星尘扩散。 |
| `wheel_zoom` Panel Execute DAT | 同样指向 `viewport`，监听 `wheel` 并开启 **Value Change**。在 `onValueChange(panelValue, oldValue=None)` 将 `panelValue.val` 传入 `scroll()`。滚轮值回到零时不改变缩放目标。 |
| `escape_to_overview` Panel Execute DAT | 监听 `viewport` 的 `key`，把键值交给 `go_back()`。 |
| `return_key` Keyboard In DAT | 开启 Perform 输入，登记 `esc escape`，**Callbacks** 指向 `return_key_callbacks1`。它是 Perform 窗口的键盘返回入口。 |
| `return_key_callbacks1` Text DAT | 接收 Keyboard In DAT 的键盘与快捷键回调，识别 Esc 后调用同一个 `go_back()`。 |
| `return_key_callbacks` Text DAT | 保存早期键盘脚本。当前 `return_key` 的 Callbacks 指向带数字 1 的节点。 |

参考 [Panel Execute DAT 官方手册](https://derivative.ca/UserGuide/Panel_Execute_DAT)和 [Panel COMP 鼠标滚轮设置](https://docs.derivative.ca/COMP_Panel_Page)。

### orbit_engine 里的交互是怎么写的

- **总览。** `orbit_positions()` 算出五颗天体的横向坐标、半径和自转角。指针靠近四边时，`explore_axis()` 把横纵坐标换成镜头偏移。鼠标停在某颗天体上约 120 毫秒后锁定。此时锁定目标接管镜头，原悬停点和球体移动经过的窄区域可继续保持悬停。镜头用带速度的阻尼更新，约 1 秒滑到中央。英文名随 `label_alpha` 浮现，球体放大约 14%。离开时会短暂确认，然后混合回边缘平移的目标位置，名称以粒子消散。
- **进入。** 左键记录当时的中心和半径，设置 `focus` 及 `shown`，启动 1.52 秒聚散进度。点位、镜头和粒子从总览的位置衔接到近景。着色器只在进入状态显示顶部中英文标题。
- **球体比例。** 总览基础半径依次是 0.065、0.015、0.023、0.027、0.020。首次进入各近景共用一个镜头倍率，所以仍能看出大小差异。鼠标横向位置映射偏航角，纵向位置映射俯仰角。两个角度都平滑更新。
- **缩放。** 每个向上的轮格把缩放目标乘以 1.18，向下则除以 1.18。最小值是该天体的比例近景，最大目标约为画面宽度的 1.35 倍直径，便于靠近看球面。脚本逐帧逼近目标，鼠标旋转仍可继续。
- **近景点击和返回。** 左上角箭头有固定触发范围。点击其余区域会记录星尘扩散的中心和起始时间。箭头和 Esc 都执行 `leave()`，并重置缩放、尾迹和场景状态。

[Python 源码](.echo-orbit/orbit_runtime.py)

## 2. 五路画面怎么进主着色器

在 `solar_atlas` 上把输出分辨率设为 720 × 1280，**Pixel Shader** 指向 `atlas_pixel`。按下表从编号 0 起接入 TOP。输入编号会决定 GLSL 代码从哪一张纹理取样。

| 输入 | 节点与来源 | 在画面里的作用 |
| --- | --- | --- |
| 0 | `particles` Script TOP，`orbit_engine` 用 numpy 算出粒子位置和亮度，再用 `copyNumpyArray()` 写入 540 × 960 的纹理 | 总览轨道粒子、入场聚散、各天体的近处星尘、指针尾迹和点击喷散。颜色通道用于区分几组粒子。 |
| 1 | `nebula_field` GLSL TOP，Pixel Shader 为 `nebula_pixel` | 直接生成 720 × 1280 的气体云带和远处星点。按天体在着色器里设置太阳环流、水星尾流、金星双弧、地球双带和火星分叉。 |
| 2 | `planet_names` Movie File In TOP，加载 `body-names-bilingual.png` | 嵌入的 256 × 720 图集。每颗天体占 144 像素高的区域，包含总览英文大写、近景中文、近景英文三行。GLSL 按场景和用途取字。 |
| 3 | `feedback_material/out1` | 提供总览球面和近景主材质。近景沿用旧版金星的前后半球映射、固定方向光与球缘光。 |
| 4 | `closeup_feedback/out1` | 提供第二套反馈色束。展示页在相同球面坐标下叠入约 12% 的细节，并按不同天体调色。 |

`atlas_pixel` 先把 UV 变成 9∶16 的等比例坐标，再换算到镜头所在的世界坐标。近景用圆形覆盖率和球面法线绘制球体，边缘做像素级抗锯齿。之后叠入星尘、日冕、返回箭头和文字，最后送给 `out_image`。这里的球面、日冕和 UI 都在同一 GLSL 渲染流程完成。

| 向量参数 | Python 每帧传给 GLSL 的内容 |
| --- | --- |
| `uCamera` | 镜头中心 X/Y、放大倍率、进入近景的混合进度。 |
| `uPointer` | 时间、指针 U/V、附近星尘的牵引强度。 |
| `uAudio` | 低频、中频、高频、瞬态。也传给 `nebula_field`。 |
| `uScene` | 当前图像场景、近景锁定渐变、总览悬停对象、返回键高亮。前两项随运行状态变化。 |
| `uSun` 至 `uMars` | 每颗天体的 X/Y、基础半径、自转相位。 |
| `uLabel` | 英文悬停标签的天体、透明度、文字方位、是否正在消散。 |
| `uTransition` | 聚散进度、出发位置和出发半径。 |
| `uView` | 近景球体的偏航、俯仰和近景开关。 |

`particle_callbacks` 是 `particles` 当前引用的回调 DAT。主流程由 `orbit_engine` 将粒子纹理写入锁定的 TOP。另一个 `particles_callbacks` 是保存的旧脚本。`solar_atlas_pixel1`、`nebula_field_pixel` 是 GLSL 节点生成的模板。实际 Pixel Shader 引用见上表。`solar_atlas_compute1` 和 `nebula_field_compute` 保留在各自的 Compute Shader 参数，实际运行用 Pixel Shader 模式。`solar_atlas_info1` 和 `nebula_field_info` 用来查看编译信息。

[GLSL Multi TOP 手册](https://derivative.ca/UserGuide/GLSL_Multi_TOP) · [星云 GLSL](.echo-orbit/live-fluids/atlas_nebula.glsl) · [场景底稿](.echo-orbit/live-fluids/live_atlas.frag) · [球面着色](.echo-orbit/live-fluids/atlas_feedback.glsl)

## 3. feedback_material 旧版金星材质

进入 `/project1/feedback_material`。主链可以按下面五段搭建，两处分岔的输入顺序见附录。

| 步骤 | 节点与操作 |
| --- | --- |
| 做原始形状 | `circle1` 是 1280 × 720 的透明圆，半径 0.188。`noise1` 生成随机颗粒，接 `displace1` 的位移输入，数值约 0.002、0.0035。另开 `noise2 → level1` 做随时间变化的亮度遮罩。位移圆和遮罩接 `comp1`，用 **Multiply** 合成。 |
| 先做细边与旋转 | `comp1 → feedbackEdge1 → transform1 → null1`。`feedbackEdge1` 来自 Palette 的 Feedback Edge。其 Scale 设 1.006、Source Gain 0.57、Feedback Gain 1.025，源/历史模糊设 2/3，Edge Strength 0.62。`transform1` 每秒旋转约 8°。 |
| 让前一帧流动 | `null1` 接 `feedback1` 作为初始画面。上帧分别送进 `slope1`、`slope2` 提取横纵亮度变化，以及 `noise3` 做噪声流场。三路在 `comp2` 取平均。上帧画面和流场同时接 `displace2`，位移权重按自定义参数 `Drive` 变化。`level2` 微调历史亮度。 |
| 回灌与柔边 | `level2` 与 `null1` 接 `feedback_refresh` Cross TOP，Cross 为 0.052，并把它填为 `feedback1` 的 **Target TOP**。`soft_outline` 对种子做尺寸 28 的 Blur，和刷新结果在 `comp3` 相乘，再用 `smooth_lookup_input` 轻柔化色带输入。`keyboardin1` 监听 R，驱动 Feedback 的 Reset。 |
| 着色与输出 | `venus_colors` Table DAT 记录色标，`ramp1` 引用它生成 1024 × 1 的查找纹理。`lookup1 → hsvadj1 → level3 → null3` 映射色彩并做饱和度、亮度修正。`edge1` 从 `null3` 抽边，`comp4` 将颜色与细边相加。`noise4 → level6` 做低透明度噪声，送入 `comp6` 的 Outside Luminance 合成。末尾 `transform2` 整理画布并接 `out1`。 |

`ramp1_keys` 是 Ramp 的编辑辅助表。实际色标由 `ramp1` 的 DAT 参数读取 `venus_colors`。近景时 `Drive` 和 `Detail` 更多随音频 RMS 变化，总览时主要使用低频、中频与瞬态。

[旧版材质搭建源码](.echo-orbit/live-fluids/build_tutorial_venus.py) · [Feedback TOP 手册](https://derivative.ca/UserGuide/Feedback_TOP)

## 4. closeup_feedback 近景细节层

进入 `/project1/closeup_feedback`。它和上一套同名节点各自在自己的 Base 中运行，回灌目标和边缘处理尤其值得分开看。

| 步骤 | 节点与操作 |
| --- | --- |
| 做带缺口的形状 | `circle1` 半径 0.2，`noise1` 生成细噪声，`displace1` 做约 −0.02 的双轴位移。把 `noise2 → level1` 接到 `comp1` 的第二输入，第一输入接 `displace1`，模式选 **Outside Luminance**。 |
| 导入 Feedback Edge | `comp1 → feedbackEdge1 → transform1 → null1`。Feedback Edge 的 Dry/Wet 为 0.946。这里的 `null1` 同时给 Feedback 做起始纹理、给回灌端补新画面。 |
| 回灌上一帧 | `feedback1` 的前一帧分给 `noise3`、`slope1` 和 `slope2`。两 Slope 的 Zero Point 分别为 0.3、0.5。三路 `comp2` Average 后给 `displace2`，位移约 0.01。经 `level2` 把旧帧透明度降到 0.90。将旧帧和 `null1` 送入 `comp3`，用 **Maximum**，再把 **Target TOP** 指向 `comp3`。`keyboardin1` 按 1 触发 Reset。 |
| 做 Lookup 和双边 | `ramp_keys` Table DAT 给 `ramp1` 生成色带。`lookup1` 取 `comp3` 和 Ramp，两输入依次接图像和查找纹理。`hsvadj1 → level3 → null2` 给出主颜色，Gamma 0.7。`edge1 → level4` 是第一道边，`comp4` 加回主颜色。`edge2 → level5` 是第二道边，`comp5` 再叠回第一轮结果。 |
| 输出细节纹理 | `comp5` 也喂给 `noise4 → level6`，噪声透明度约 0.10，配合 `comp6` Outside Luminance 丰富边缘。`level7` 对比度 1.11。结尾 `transform2 → null3 → out1` 输出给 `solar_atlas` 输入 4。 |

`ramp1_keys` 是辅助表，`ramp_keys` 是当前引用的色标。`Harmonicgain` 从 `orbit_engine` 得到约 `0.5 + 1.5 × RMS`，运行为 `noise3` 的 Gain。两套材质都可直接在各自的 `out1` 预览，再回到总场景看球面映射。

[近景细节层搭建源码](.echo-orbit/live-fluids/rebuild_tutorial_graph.py)

## 5. 两个 feedbackEdge1 的内部接线

两个 Base 里的 `feedbackEdge1` 都是 TouchDesigner Palette 中的 Feedback Edge。输入画面从外层 `comp1` 进入，内部再做一层亮边反馈。

| 节点 | 接线与用途 |
| --- | --- |
| `in1`、`moviefilein1` | `in1` 接外部图像。内连的 `moviefilein1` 是 Palette 自带的预览影片入口，搭建工程时把外部 `comp1` 接到组件输入。 |
| `blur2 → level2` | 处理当前帧，分别读取组件上的 **Blur Source** 和 **Source Gain**。 |
| `feedback → level1 → transform1 → blur1 → hsvadj1 → edge1` | 接上帧，调亮后按 **Scale** 稍微放大，按 **Blur Feedback** 模糊，再调色、提取边缘。Feedback 的种子来自 `level2`。 |
| `comp1 → null1` | 把 `level2` 和 `edge1` 用 **Screen** 合成。`null1` 是 `feedback` 的 **Target TOP**，以保留历史边缘。 |
| `dryWetMix → out1` | 组件的原图和处理结果分别来自 `in1` 与 `null1`。混合输出通过 `dryWetMix/out1` 接给外层 `out1`。 |
| `pattern2 → function1 → pattern1`、`lookupOverload` | CHOP 生成一条曲线，`lookupOverload` 接 `edge1` 并将 `pattern1` 作为 Lookup 曲线。当前 `comp1` 直接接 `edge1`。 |
| `docsHelper` | Palette 附带的帮助组件，内含 `DocsHelper`、`parexec1` 与 `parexec_PaletteComp`。它们管理组件帮助和界面参数。 |

进入 `feedbackEdge1/dryWetMix`。图像口由 `in2` 和 `in3` 分别承接原图和湿信号。二者进入 `cross1`，`switch5` 在原图与混合图之间切换，最后到 `out1`。控制部分用 `par2` 把组件的 `Drywet` 转成 CHOP 通道，`math9` 做向上取整以供开关使用，`merge2 → null1` 集合开关值和混合量。旁边的 `null1_export` 存放参数导出关系。

## 6. 六路音频和频段怎么接

| 场景 | Audio File In CHOP | Math CHOP | 内置音轨 |
| --- | --- | --- | --- |
| 总览 | `audio_overview` | `volume_overview` | Computations in a Snowstorm |
| 太阳 | `audio_sun` | `volume_sun` | Aphelion |
| 水星 | `audio_mercury` | `volume_mercury` | Machina |
| 金星 | `audio_venus` | `volume_venus` | Petrichor |
| 地球 | `audio_earth` | `volume_earth` | Childhood |
| 火星 | `audio_mars` | `volume_mars` | Resonance |

每条 Audio File In 读取 VFS 里的 MP3，并给对应的 Math CHOP。六个 Math 接入 `music_mix`，用 **Combine CHOPs = Add** 做立体声相加，再接 `audio_device` Audio Device Out。切场景时脚本 cue 新音轨，渐入到约 0.52，旧音轨逐渐淡出后停止。回总览时也走同一套淡入淡出。

音频分析在 `orbit_engine` 内完成。它读取当前音轨的时间切片，双声道取平均后算 RMS。2048 点滑动缓冲配合 Hann 窗再做 FFT，取 28–160 Hz、160–1700 Hz、1700–7200 Hz 三段，并用频谱的正向变化量估计瞬态。分析结果经过平滑后给 `uAudio`、星尘速度和反馈材质。项目的六路 Math 是音量包络，分析参数在 Python 里改。

## 7. 按实际工程复搭的顺序

1. **先跑通画面。** 建 `viewport`、`out_image` 和 `/perform`，先接一张简单 TOP 测试窗口。确认分辨率和 V 轴方向，再换成 `solar_atlas`。
2. **单独跑通两套材质。** 先验证每个 `feedback1` 的目标、反馈重置和 Ramp 输入，再在两个 `out1` 检查连续几帧。两套回灌分别指向 Cross 和 Maximum。
3. **按编号接五路图像。** 配好 GLSL 的 Pixel Shader、名称图集及 12 组向量参数，让 `clock` 逐帧写入并确认开头能显示横轴星图。
4. **接面板事件。** 先测悬停和点击，再测滚轮两个方向，以及箭头、Esc 返回。滚轮是瞬时值，所以用 Panel Execute DAT 监听变化。
5. **接声音并验收。** 六路音源各过一个 Math，合到 `music_mix`。依次进入五颗天体，确认音轨交换、星尘受指针牵引、再次进入时恢复基础倍率。
6. **录制。** 用 Movie File Out TOP 接 `out_image`。短录制可将 **Audio CHOP** 指向 `music_mix` 同时录音。这次完整版将原工程画面和六段原声分开处理，按同一场景切换和音量包络混音，再叠加录下的指针坐标、动作标记和字幕。 [录制脚本](.echo-orbit/live-fluids/record_full_demo.py) · [Movie File Out TOP 手册](https://derivative.ca/UserGuide/Movie_File_Out_TOP)

## 演示视频定位

| 时间 | 画面 |
| --- | --- |
| 00:00–00:15 | 开场与总览四向平移 |
| 00:15–00:23 | 悬停居中、放大、英文名、移开复位 |
| 00:23–00:31 | 金星入场、双语标题、水平和垂直旋转 |
| 00:31–00:39 | 滚轮放大球面、查看色带、缩回原比例 |
| 00:39–00:46 | 指针牵引星尘、点击扩散、箭头返回 |
| 00:46–01:28 | 太阳、水星、地球、火星及专属音轨，演示 Esc 返回 |

## 附录 全部工程节点和连线

同一组表里的短名称相对于小节路径。第三列按输入顺序列出连线，跨组件连线写成绝对 OP 路径。第四列记录画布上看不到的关键引用。表中包括两套 Palette 助手，以及文件随带的时间轴、映射和 MIDI 模板。

- **`/local` 根工具。** `set_variables → variables` 提供本地变量表，`shortcuts` 读取安装目录的面板快捷键表，`master_beat` 提供默认节拍工具。
- **`/local/time`。** `time1` 的时间通道经 `resample2 → math10 → math11 → syncframe` 送到 `hold1`。另一支由 `rate → pausemath → cframe` 推进帧数。`independent` 与 `scrubber` 在时间来源之间取值，最终送 `clock`。表、常量和参数回调负责状态、范围或覆盖参数。
- **`/local/maps`。** `master` 保存映射组件，`select1 → select2` 是两级选取，`replicator1` 和其回调处理映射实例。
- **`/local/midi`。** `device`、`midi_inputs`、`midi_outputs` 和 `userdevices` 管理默认 MIDI 配置。`template` 内的表定义按钮、滑块和属性。进入 `mapmaster1` 后，`midiinmap → out1` 提供输入映射，`collect_buttons → buttons` 与 `collect_sliders → sliders` 提供默认控制通道，另有 `midiout` 和 CHOP Execute。作品的播放和音频分析从 `/project1/audio_*` 取得。


共 **234 个节点**。标记为「运行时」的条目由 TouchDesigner 模板或 Palette 帮助组件展开。

### `/`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `local` | COMP · `base` | — | — |
| `perform` | COMP · `window` | — | Window Operator `/project1/viewport` |
| `project1` | COMP · `container` | — | TOP `/project1/out_image` |

### `/project1`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `atlas_pixel` | DAT · `text` | — | — |
| `audio_device` | CHOP · `audiodevout` | `music_mix` | — |
| `audio_earth` | CHOP · `audiofilein` | — | File `vfs:/project1:earth.mp3` |
| `audio_mars` | CHOP · `audiofilein` | — | File `vfs:/project1:mars.mp3` |
| `audio_mercury` | CHOP · `audiofilein` | — | File `vfs:/project1:mercury.mp3` |
| `audio_overview` | CHOP · `audiofilein` | — | File `vfs:/project1:overview.mp3` |
| `audio_sun` | CHOP · `audiofilein` | — | File `vfs:/project1:sun.mp3` |
| `audio_venus` | CHOP · `audiofilein` | — | File `vfs:/project1:venus.mp3` |
| `clock` | DAT · `execute` | — | — |
| `closeup_feedback` | COMP · `base` | — | — |
| `escape_to_overview` | DAT · `panelexec` | — | Panels `/project1/viewport` · Panel Value `key` |
| `feedback_material` | COMP · `base` | — | — |
| `left_click` | DAT · `panelexec` | — | Panels `/project1/viewport` · Panel Value `lselect` |
| `music_mix` | CHOP · `math` | `volume_overview`, `volume_sun`, `volume_mercury`, `volume_venus`, `volume_earth`, `volume_mars` | — |
| `nebula_field` | TOP · `glsl` | — | Pixel Shader `/project1/nebula_pixel` · Compute Shader `/project1/nebula_field_compute` |
| `nebula_field_compute` | DAT · `text` | — | — |
| `nebula_field_info` | DAT · `info` | — | — |
| `nebula_field_pixel` | DAT · `text` | — | — |
| `nebula_pixel` | DAT · `text` | — | — |
| `orbit_engine` | DAT · `text` | — | — |
| `out_image` | TOP · `null` | `solar_atlas` | — |
| `particle_callbacks` | DAT · `text` | — | — |
| `particles` | TOP · `script` | — | Callbacks `/project1/particle_callbacks` |
| `particles_callbacks` | DAT · `text` | — | — |
| `planet_names` | TOP · `moviefilein` | — | File `vfs:/project1:body-names-bilingual.png` |
| `return_key` | DAT · `keyboardin` | — | Callbacks `/project1/return_key_callbacks1` |
| `return_key_callbacks` | DAT · `text` | — | — |
| `return_key_callbacks1` | DAT · `text` | — | — |
| `solar_atlas` | TOP · `glslmulti` | `particles`, `nebula_field`, `planet_names`, `/project1/feedback_material/out1`, `/project1/closeup_feedback/out1` | Pixel Shader `/project1/atlas_pixel` · Compute Shader `/project1/solar_atlas_compute1` |
| `solar_atlas_compute1` | DAT · `text` | — | — |
| `solar_atlas_info1` | DAT · `info` | — | — |
| `solar_atlas_pixel1` | DAT · `text` | — | — |
| `viewport` | COMP · `container` | — | TOP `/project1/out_image` |
| `volume_earth` | CHOP · `math` | `audio_earth` | — |
| `volume_mars` | CHOP · `math` | `audio_mars` | — |
| `volume_mercury` | CHOP · `math` | `audio_mercury` | — |
| `volume_overview` | CHOP · `math` | `audio_overview` | — |
| `volume_sun` | CHOP · `math` | `audio_sun` | — |
| `volume_venus` | CHOP · `math` | `audio_venus` | — |
| `wheel_zoom` | DAT · `panelexec` | — | Panels `/project1/viewport` · Panel Value `wheel` |

### `/project1/closeup_feedback`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `circle1` | TOP · `circle` | — | Operation `over` |
| `comp1` | TOP · `comp` | `displace1`, `level1` | Operation `outsideluminance` |
| `comp2` | TOP · `comp` | `noise3`, `slope1`, `slope2` | Operation `average` |
| `comp3` | TOP · `comp` | `level2`, `null1` | Operation `maximum` |
| `comp4` | TOP · `comp` | `level4`, `null2` | Operation `add` |
| `comp5` | TOP · `comp` | `level5`, `comp4` | Operation `add` |
| `comp6` | TOP · `comp` | `comp5`, `level6` | Operation `outsideluminance` |
| `displace1` | TOP · `displace` | `circle1`, `noise1` | — |
| `displace2` | TOP · `displace` | `feedback1`, `comp2` | — |
| `edge1` | TOP · `edge` | `null2` | — |
| `edge2` | TOP · `edge` | `comp4` | — |
| `feedback1` | TOP · `feedback` | `null1` | TOP `/project1/closeup_feedback/comp3` · Reset `keyboardin1`（1） |
| `feedbackEdge1` | COMP · `base` | `comp1` | — |
| `hsvadj1` | TOP · `hsvadj` | `lookup1` | — |
| `keyboardin1` | CHOP · `keyboardin` | — | — |
| `level1` | TOP · `level` | `noise2` | — |
| `level2` | TOP · `level` | `displace2` | — |
| `level3` | TOP · `level` | `hsvadj1` | — |
| `level4` | TOP · `level` | `edge1` | — |
| `level5` | TOP · `level` | `edge2` | — |
| `level6` | TOP · `level` | `noise4` | — |
| `level7` | TOP · `level` | `comp6` | — |
| `lookup1` | TOP · `lookup` | `comp3`, `ramp1` | — |
| `noise1` | TOP · `noise` | — | — |
| `noise2` | TOP · `noise` | `displace1` | — |
| `noise3` | TOP · `noise` | `feedback1` | — |
| `noise4` | TOP · `noise` | `comp5` | — |
| `null1` | TOP · `null` | `transform1` | — |
| `null2` | TOP · `null` | `level3` | — |
| `null3` | TOP · `null` | `transform2` | — |
| `out1` | TOP · `out` | `null3` | — |
| `ramp1` | TOP · `ramp` | — | Operation `multiply` · DAT `ramp_keys` |
| `ramp1_keys` | DAT · `table` | — | — |
| `ramp_keys` | DAT · `table` | — | — |
| `slope1` | TOP · `slope` | `feedback1` | — |
| `slope2` | TOP · `slope` | `feedback1` | — |
| `transform1` | TOP · `transform` | `/project1/closeup_feedback/feedbackEdge1/out1` | — |
| `transform2` | TOP · `transform` | `level7` | — |

### `/project1/closeup_feedback/feedbackEdge1`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `blur1` | TOP · `blur` | `transform1` | — |
| `blur2` | TOP · `blur` | `in1` | — |
| `comp1` | TOP · `comp` | `level2`, `edge1` | Operation `screen` |
| `docsHelper` | COMP · `container` | — | — |
| `dryWetMix` | COMP · `base` | `in1`, `null1` | — |
| `edge1` | TOP · `edge` | `hsvadj1` | — |
| `feedback` | TOP · `feedback` | `level2` | TOP `/project1/closeup_feedback/feedbackEdge1/null1` |
| `function1` | CHOP · `function` | `pattern2` | — |
| `hsvadj1` | TOP · `hsvadj` | `blur1` | — |
| `in1` | TOP · `in` | `moviefilein1` | — |
| `level1` | TOP · `level` | `feedback` | — |
| `level2` | TOP · `level` | `blur2` | — |
| `lookupOverload` | TOP · `lookup` | `edge1` | CHOP `/project1/closeup_feedback/feedbackEdge1/pattern1` |
| `moviefilein1` | TOP · `moviefilein` | — | File `TouchDesigner/Samples/Map/Nature/Movie.2.mp4` |
| `null1` | TOP · `null` | `comp1` | — |
| `out1` | TOP · `out` | `/project1/closeup_feedback/feedbackEdge1/dryWetMix/out1` | — |
| `pattern1` | CHOP · `pattern` | `function1` | — |
| `pattern2` | CHOP · `pattern` | — | — |
| `transform1` | TOP · `transform` | `level1` | — |

### `/project1/closeup_feedback/feedbackEdge1/docsHelper`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `DocsHelper` | 运行时 · `text` | — | — |
| `parexec1` | 运行时 · `parexec` | — | — |
| `parexec_PaletteComp` | 运行时 · `parexec` | — | — |

### `/project1/closeup_feedback/feedbackEdge1/dryWetMix`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `cross1` | TOP · `cross` | `in2`, `in3` | — |
| `in2` | TOP · `in` | — | — |
| `in3` | TOP · `in` | — | — |
| `math9` | CHOP · `math` | `par2` | — |
| `merge2` | CHOP · `merge` | `math9`, `par2` | — |
| `null1` | CHOP · `null` | `merge2` | — |
| `null1_export` | DAT · `table` | — | — |
| `out1` | TOP · `out` | `switch5` | — |
| `par2` | CHOP · `par` | — | — |
| `switch5` | TOP · `switch` | `in2`, `cross1` | — |

### `/project1/feedback_material`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `circle1` | TOP · `circle` | — | Operation `over` |
| `comp1` | TOP · `comp` | `displace1`, `level1` | Operation `multiply` |
| `comp2` | TOP · `comp` | `noise3`, `slope1`, `slope2` | Operation `average` |
| `comp3` | TOP · `comp` | `feedback_refresh`, `soft_outline` | Operation `multiply` |
| `comp4` | TOP · `comp` | `null3`, `edge1` | Operation `add` |
| `comp6` | TOP · `comp` | `comp4`, `level6` | Operation `outsideluminance` |
| `displace1` | TOP · `displace` | `circle1`, `noise1` | — |
| `displace2` | TOP · `displace` | `feedback1`, `comp2` | — |
| `edge1` | TOP · `edge` | `null3` | — |
| `feedback1` | TOP · `feedback` | `null1` | TOP `/project1/feedback_material/feedback_refresh` · Reset `keyboardin1`（R） |
| `feedbackEdge1` | COMP · `base` | `comp1` | — |
| `feedback_refresh` | TOP · `cross` | `level2`, `null1` | — |
| `hsvadj1` | TOP · `hsvadj` | `lookup1` | — |
| `keyboardin1` | CHOP · `keyboardin` | — | — |
| `level1` | TOP · `level` | `noise2` | — |
| `level2` | TOP · `level` | `displace2` | — |
| `level3` | TOP · `level` | `hsvadj1` | — |
| `level6` | TOP · `level` | `noise4` | — |
| `lookup1` | TOP · `lookup` | `smooth_lookup_input`, `ramp1` | — |
| `noise1` | TOP · `noise` | — | — |
| `noise2` | TOP · `noise` | — | — |
| `noise3` | TOP · `noise` | `feedback1` | — |
| `noise4` | TOP · `noise` | — | — |
| `null1` | TOP · `null` | `transform1` | — |
| `null3` | TOP · `null` | `level3` | — |
| `out1` | TOP · `out` | `transform2` | — |
| `ramp1` | TOP · `ramp` | — | Operation `multiply` · DAT `venus_colors` |
| `ramp1_keys` | DAT · `table` | — | — |
| `slope1` | TOP · `slope` | `feedback1` | — |
| `slope2` | TOP · `slope` | `feedback1` | — |
| `smooth_lookup_input` | TOP · `blur` | `comp3` | — |
| `soft_outline` | TOP · `blur` | `null1` | — |
| `transform1` | TOP · `transform` | `/project1/feedback_material/feedbackEdge1/out1` | — |
| `transform2` | TOP · `transform` | `comp6` | — |
| `venus_colors` | DAT · `table` | — | — |

### `/project1/feedback_material/feedbackEdge1`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `blur1` | TOP · `blur` | `transform1` | — |
| `blur2` | TOP · `blur` | `in1` | — |
| `comp1` | TOP · `comp` | `level2`, `edge1` | Operation `screen` |
| `docsHelper` | COMP · `container` | — | — |
| `dryWetMix` | COMP · `base` | `in1`, `null1` | — |
| `edge1` | TOP · `edge` | `hsvadj1` | — |
| `feedback` | TOP · `feedback` | `level2` | TOP `/project1/feedback_material/feedbackEdge1/null1` |
| `function1` | CHOP · `function` | `pattern2` | — |
| `hsvadj1` | TOP · `hsvadj` | `blur1` | — |
| `in1` | TOP · `in` | `moviefilein1` | — |
| `level1` | TOP · `level` | `feedback` | — |
| `level2` | TOP · `level` | `blur2` | — |
| `lookupOverload` | TOP · `lookup` | `edge1` | CHOP `/project1/feedback_material/feedbackEdge1/pattern1` |
| `moviefilein1` | TOP · `moviefilein` | — | File `TouchDesigner/Samples/Map/Nature/Movie.2.mp4` |
| `null1` | TOP · `null` | `comp1` | — |
| `out1` | TOP · `out` | `/project1/feedback_material/feedbackEdge1/dryWetMix/out1` | — |
| `pattern1` | CHOP · `pattern` | `function1` | — |
| `pattern2` | CHOP · `pattern` | — | — |
| `transform1` | TOP · `transform` | `level1` | — |

### `/project1/feedback_material/feedbackEdge1/docsHelper`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `DocsHelper` | 运行时 · `text` | — | — |
| `parexec1` | 运行时 · `parexec` | — | — |
| `parexec_PaletteComp` | 运行时 · `parexec` | — | — |

### `/project1/feedback_material/feedbackEdge1/dryWetMix`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `cross1` | TOP · `cross` | `in2`, `in3` | — |
| `in2` | TOP · `in` | — | — |
| `in3` | TOP · `in` | — | — |
| `math9` | CHOP · `math` | `par2` | — |
| `merge2` | CHOP · `merge` | `math9`, `par2` | — |
| `null1` | CHOP · `null` | `merge2` | — |
| `null1_export` | DAT · `table` | — | — |
| `out1` | TOP · `out` | `switch5` | — |
| `par2` | CHOP · `par` | — | — |
| `switch5` | TOP · `switch` | `in2`, `cross1` | — |

### `/local`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `maps` | COMP · `base` | — | — |
| `master_beat` | CHOP · `beat` | — | — |
| `midi` | COMP · `base` | — | — |
| `set_variables` | DAT · `table` | — | — |
| `shortcuts` | DAT · `filein` | — | File `TouchDesigner/Config/PanelShortcuts.txt` |
| `time` | COMP · `time` | — | — |
| `variables` | DAT · `null` | `set_variables` | — |

### `/local/maps`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `master` | COMP · `base` | — | — |
| `replicator1` | COMP · `replicator` | — | Callbacks `/local/maps/replicator1_callbacks` |
| `replicator1_callbacks` | DAT · `text` | — | — |
| `select1` | DAT · `select` | — | — |
| `select2` | DAT · `select` | `select1` | — |

### `/local/midi`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `device` | 运行时 · `table` | — | — |
| `midi_inputs` | 运行时 · `table` | — | — |
| `midi_outputs` | 运行时 · `table` | — | — |
| `template` | 运行时 · `base` | — | — |
| `userdevices` | 运行时 · `base` | — | — |

### `/local/midi/template`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `attributes` | 运行时 · `table` | — | — |
| `buttons` | 运行时 · `table` | — | — |
| `icon` | 运行时 · `null` | `text1` | — |
| `mapmaster1` | 运行时 · `base` | — | — |
| `sliders` | 运行时 · `table` | — | — |
| `text1` | 运行时 · `text` | — | Operation `over` |

### `/local/midi/template/mapmaster1`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `buttons` | 运行时 · `null` | `collect_buttons` | — |
| `chopexec1` | 运行时 · `chopexec` | — | CHOP `[type:nullCHOP path:/local/midi/template/mapmaster1/sliders, type:nullCHOP path:/local/midi/template/mapmaster1/buttons, type:nullCHOP path:/local/midi/template/mapmaster1/sliders, type:nullCHOP path:/local/midi/template/mapmaster1/buttons]` |
| `collect_buttons` | 运行时 · `constant` | — | — |
| `collect_sliders` | 运行时 · `constant` | — | — |
| `midiinmap` | 运行时 · `midiinmap` | — | — |
| `midiout` | 运行时 · `midiout` | — | File `untitled.midi` |
| `out1` | 运行时 · `out` | `midiinmap` | — |
| `sliders` | 运行时 · `null` | `collect_sliders` | — |

### `/local/time`

| 节点 | 类型 | 输入连线 | 关键参数引用 |
| --- | --- | --- | --- |
| `ableton` | 运行时 · `select` | — | — |
| `cframe` | 运行时 · `speed` | `pausemath` | — |
| `clock` | 运行时 · `null` | `scrubber` | — |
| `eval1` | 运行时 · `eval` | `set_state` | — |
| `forcecook_override` | 运行时 · `parexec` | — | — |
| `get_state` | 运行时 · `constant` | — | — |
| `getscrub` | 运行时 · `select` | — | CHOP `/ui/dialogs/timeline/scrubframe` |
| `hold1` | 运行时 · `hold` | `syncframe`, `get_state` | — |
| `independent` | 运行时 · `switch` | `hold1`, `cframe` | — |
| `limit` | 运行时 · `table` | — | — |
| `math10` | 运行时 · `math` | `resample2` | — |
| `math11` | 运行时 · `math` | `math10` | — |
| `override` | 运行时 · `null` | `properties` | — |
| `pausemath` | 运行时 · `math` | `rate` | — |
| `properties` | 运行时 · `table` | — | — |
| `rate` | 运行时 · `constant` | — | — |
| `resample1` | 运行时 · `resample` | `getscrub` | — |
| `resample2` | 运行时 · `resample` | `time1` | — |
| `scrubber` | 运行时 · `switch` | `independent`, `resample1` | — |
| `set_state` | 运行时 · `table` | — | — |
| `state` | 运行时 · `switch` | `eval1`, `ableton` | — |
| `syncframe` | 运行时 · `limit` | `math11` | — |
| `time1` | 运行时 · `timeline` | — | — |
