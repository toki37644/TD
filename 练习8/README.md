# 练习 8 · 橘猫转台

[打开 TouchDesigner 工程](td8-stage.toe) · [查看渲染预览](预览.png)

场景沿用练习素材里的 `cat.fbx`。原始模型经过轴向校正、缩放和居中，立在带铜色饰边的圆台上。`Cat_diffuse.jpg` 提供毛色和花纹，`Cat_bump.jpg` 经 Normal Map TOP 转成切线空间法线贴图。暖色主光投下软阴影，冷色补光和轮廓光勾出猫的侧面。

## 播放和查看

1. 在 TouchDesigner 中打开 `td8-stage.toe`。工程使用同目录下的 `cat.fbx` 和 `Cat` 文件夹，移动工程时请一并带上。
2. 按 **F1** 进入 Perform Mode。猫会自动转动，每 12 秒转一圈。按 **Shift+空格** 暂停或恢复，鼠标位于演出窗口时按 **Esc** 返回编辑界面。
3. 编辑界面可右键点击 `/project1/out_stage`，选择 **View…** 单独查看 1280×720 输出。也可拖动底部时间线检查任意帧。第 1、181、361、541 帧相隔约 90°。

## 编辑和对照

选择 `/project1` 容器，在参数窗的 **Stage** 页关闭 **Auto Rotate** 后，用 **Angle Offset** 手动转动猫。把 **Bump Strength** 调到 `0` 可对照关闭凹凸效果的画面，恢复到 `0.62` 即回到交付设置。相机位于 `stage_camera`，灯光可在 `warm_key`、`cool_fill`、`teal_rim` 和 `ambient` 上调节。

工程使用 TouchDesigner 2023.11600 制作。`Cat` 中的 OBJ 和 MTL 保留为原始备用素材，舞台的网格由 `fbx1` 提供。
