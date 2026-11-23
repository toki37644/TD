"""Lay out the source references and proposed looks for visual approval."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


here = Path(__file__).resolve().parent
work = here.parent
root = work.parent
regular = "C:/Windows/Fonts/msyh.ttc"
bold = "C:/Windows/Fonts/msyhbd.ttc"
board = Image.new("RGB", (1744, 1328), "#0A101B")
draw = ImageDraw.Draw(board)
foreground = "#F3F5FA"
secondary = "#BECBDD"
muted = "#8498AE"
divider = "#28374C"
blue = "#A0C5F3"


def line(x, y, value, size, color=foreground, strong=False):
    font = ImageFont.truetype(bold if strong else regular, size, index=0)
    draw.text((x, y), value, font=font, fill=color, anchor="lt")


def photo(file, x, y, width, height, *, crop=None, position=(.5, .5), contain=False):
    with Image.open(file) as source:
        picture = source.convert("RGB")
        if crop:
            picture = picture.crop(crop)
        if contain:
            picture = ImageOps.contain(picture, (width, height), Image.Resampling.LANCZOS)
            draw.rectangle((x, y, x + width - 1, y + height - 1), fill="#080C14")
            board.paste(picture, (x + (width - picture.width) // 2, y + (height - picture.height) // 2))
        else:
            picture = ImageOps.fit(picture, (width, height), Image.Resampling.LANCZOS, centering=position)
            board.paste(picture, (x, y))


looks = (
    (
        "太阳", "日珥回环", ("#FFF0C2", "#F4B347", "#EA5939"), "炽白 · 琥珀金 · 橙红",
        "球体  亮核清楚，外缘起伏，少量炽亮颗粒脱离。",
        "星云  两道日珥弧离开球缘再落回，重拍向外扩散。",
        "粒子参考  Simon David Ryden · Exploding Star",
        here / "particle-sphere.jpg", (142, 200, 1142, 658), (.5, .5),
    ),
    (
        "水星", "陨坑放射", ("#495263", "#B1ADAE", "#B9CCF4"), "石墨灰 · 冷银 · 淡蓝紫",
        "球体  背光面压暗，碎银从几处陨坑向外放射。",
        "星云  单侧斜切的细碎尘屑，高频来时短促飞散。",
        "陨坑参考  NASA / JHU APL / Carnegie",
        here / "mercury.jpg", None, (.5, .52),
    ),
    (
        "金星", "卷曲云层", ("#5C456C", "#CF929A", "#F0D7AC"), "灰紫 · 雾粉 · 香槟",
        "球体  两三股半透明云褶包住部分球面，边缘有细点。",
        "星云  球外两侧厚云反向卷曲，中频推动云层翻卷。",
        "层云参考  ISAS / JAXA · Akatsuki",
        here / "venus.jpg", (177, 250, 609, 483), (.5, .5),
    ),
    (
        "地球", "极光薄幕", ("#2446A0", "#4AC9BC", "#DFF9FF"), "深钴蓝 · 孔雀青 · 冰白",
        "球体  海蓝暗面和冰白薄边分开，青色极光贴着球缘。",
        "星云  保留参考录屏的斜向流动，叠加薄幕与细星尘。",
        "星云参考  一粒六元 ·《TD 星际环游 003／宇宙诞生》",
        work / "reference-galaxy.jpg", (142, 39, 501, 455), (.5, .63),
    ),
    (
        "火星", "扇形沙暴", ("#6E2927", "#BF6645", "#E9A66A"), "铁锈红 · 焦褐 · 沙金",
        "球体  粗颗粒显出暗裂纹，迎光侧浮着细金色扬尘。",
        "星云  疏密交错的沙尘扇向外翻滚，鼓点掀起新一波。",
        "尘暴参考  ESA / DLR / FU Berlin · CC BY-SA 3.0 IGO",
        here / "mars.jpg", (114, 176, 1008, 498), (.55, .53),
    ),
)

line(64, 48, "深空回声", 57, strong=True)
line(335, 65, "天体视觉确认板", 34, blue)
line(64, 119, "首页构图与五个天体的粒子、配色和运动", 23, secondary)
draw.line((64, 166, 1680, 166), fill=divider, width=2)

left = 64
line(left, 198, "首页 · 开场构图", 32, strong=True)
line(left, 247, "参照原图线位的立体仰视", 21, blue)
photo(work / "stock" / "star-chart.jpg", left, 283, 404, 466, contain=True)
line(left, 768, "参考图由你提供", 16, muted)
line(left, 801, "太阳偏下，同心轨道接近正圆。", 21, secondary)
line(left, 837, "四颗行星持续公转、自转。", 21, secondary)

line(left, 905, "共同的颗粒质感", 28, strong=True)
photo(work / "ref-planet.jpg", left, 954, 404, 177,
      crop=(5, 37, 605, 246), position=(.42, .5))
line(left, 1146, "球体参考来自你提供的录屏。", 16, muted)
line(left, 1179, "暗面能看出深度，亮边能分辨细颗粒。", 19, secondary)

draw.line((501, 192, 501, 1215), fill=divider, width=1)
x = 531
for index, (body, title, palette, color_names, surface, field, credit, path, crop, position) in enumerate(looks):
    top = 197 + 203 * index
    photo(path, x, top, 390, 181, crop=crop, position=position)
    tx = x + 415
    line(tx, top + 2, body, 33, strong=True)
    line(tx + 82, top + 9, title, 25, color=palette[2])
    line(tx, top + 55, surface, 21, secondary)
    line(tx, top + 87, field, 21, secondary)
    for j, color in enumerate(palette):
        sx = tx + 26 * j
        draw.rounded_rectangle((sx, top + 124, sx + 19, top + 142), radius=3, fill=color)
    line(tx + 87, top + 123, color_names, 17, secondary)
    line(tx, top + 158, credit, 16, muted)
    if index < 4:
        draw.line((x, top + 191, 1680, top + 191), fill=divider, width=1)

draw.line((64, 1229, 1680, 1229), fill=divider, width=2)
line(64, 1255, "悬停  推近镜头，星名浮现并消散", 20, secondary)
line(604, 1255, "点击  球体散成星尘，再聚回特写", 20, secondary)
line(1200, 1255, "特写  音乐与鼠标驱动星云", 20, secondary)

board.save(root / "深空回声·天体视觉确认板.png", optimize=True)
