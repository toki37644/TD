Add-Type -AssemblyName System.Drawing

$bitmap = [Drawing.Bitmap]::new(1200, 675, [Drawing.Imaging.PixelFormat]::Format32bppArgb)
$drawing = [Drawing.Graphics]::FromImage($bitmap)
$drawing.SmoothingMode = [Drawing.Drawing2D.SmoothingMode]::AntiAlias
$drawing.TextRenderingHint = [Drawing.Text.TextRenderingHint]::AntiAliasGridFit

function Paint-Text($value, $face, $size, $style, $color, $x, $y) {
    $font = [Drawing.Font]::new($face, $size, [Drawing.FontStyle]$style, [Drawing.GraphicsUnit]::Pixel)
    $brush = [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml($color))
    $point = [Drawing.PointF]::new($x, $y)
    $drawing.DrawString($value, $font, $brush, $point, [Drawing.StringFormat]::GenericTypographic)
    $font.Dispose()
    $brush.Dispose()
}

function Paint-Rule($x1, $y1, $x2, $y2, $tone, $opacity) {
    $pen = [Drawing.Pen]::new([Drawing.Color]::FromArgb($opacity, [Drawing.ColorTranslator]::FromHtml($tone)))
    $drawing.DrawLine($pen, $x1, $y1, $x2, $y2)
    $pen.Dispose()
}

$chinese = 'Microsoft YaHei'
$mono = 'Consolas'
$white = '#ECF7F4'
$mint = '#9DE7D8'
$muted = '#A3BEBD'
$rule = '#7EAEAB'
$amber = '#FFBA76'

Paint-Rule 48 46 116 46 $mint 230
Paint-Rule 116 46 1152 46 $rule 70
Paint-Text 'DEEP ECHO' $mono 13 'Bold' $mint 48 57
Paint-Text '/  星际探索' $chinese 13 'Regular' $muted 125 55
Paint-Text '星球观测窗口' $chinese 13 'Regular' $muted 1071 56

Paint-Text '深空回声' $chinese 62 'Bold' $white 44 139
Paint-Text '观测星球，寻找信标' $chinese 20 'Regular' $muted 49 224
Paint-Text '把你找到的坐标连成旋律' $chinese 20 'Regular' $muted 49 257

Paint-Rule 49 333 282 333 $rule 88
Paint-Text '01' $mono 14 'Bold' $mint 49 358
Paint-Text '旋转星球' $chinese 19 'Bold' $white 82 352
Paint-Text '移动鼠标，星球转动，光影随之变化' $chinese 14 'Regular' $muted 83 380
Paint-Text '指针经过的星尘也会偏移' $chinese 14 'Regular' $muted 83 399

Paint-Text '02' $mono 14 'Bold' $mint 49 429
Paint-Text '扫描信标' $chinese 19 'Bold' $white 82 423
Paint-Text '在星云中央按住，松开发出回波' $chinese 14 'Regular' $muted 83 451

Paint-Text '03' $mono 14 'Bold' $amber 49 500
Paint-Text '航线旋律' $chinese 19 'Bold' $white 82 494
Paint-Text '依次点击已亮的信标，试听并连线' $chinese 14 'Regular' $muted 83 522

Paint-Rule 48 606 1152 606 $rule 75
Paint-Text 'A  C4     B  E4     C  G4' $mono 14 'Regular' $mint 48 628
Paint-Rule 1087 619 1152 619 $rule 124
Paint-Rule 1152 619 1152 648 $rule 124
Paint-Rule 1152 648 1087 648 $rule 124
Paint-Rule 1087 648 1087 619 $rule 124
Paint-Text '重置' $chinese 12 'Regular' $muted 1097 624
Paint-Text 'R' $mono 14 'Bold' $white 1131 626

$bitmap.Save((Join-Path (Get-Location) '.echo-work/hud.png'), [Drawing.Imaging.ImageFormat]::Png)
$drawing.Dispose()
$bitmap.Dispose()
