#!/usr/bin/env python3
"""make_og.py — 生成 Open Graph 社交分享图（1200x630）

求职垂类的冷启动很大程度依赖 Reddit / X / LinkedIn 分享。
分享时若没有 og:image，链接就是一条裸文本，点击率明显偏低。
本脚本为每个页面生成专属卡片图，配色沿用站点设计语言。

输出：source/og/<page>.png（index.html → home.png）
构建时 build.py 会连同其他静态资源一起复制到输出目录。

用法：
    python3 make_og.py
"""
import pathlib, re, textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "source"
OUT = SRC / "og"

W, H = 1200, 630
BG = "#faf9f7"
INK = "#1c1c1a"
MUTED = "#6b6a64"
ACCENT = "#185fa5"
LINE = "#e5e3dc"

FONT_DIR = pathlib.Path("/System/Library/Fonts")
FONT_CANDIDATES = [
    (FONT_DIR / "HelveticaNeue.ttc", 0),
    (FONT_DIR / "Helvetica.ttc", 0),
    (FONT_DIR / "ArialHB.ttc", 0),
]


def load_font(size: int, bold: bool = False):
    """加载系统字体，逐个候选尝试，最后退回 PIL 默认字体"""
    for path, idx in FONT_CANDIDATES:
        if not path.exists():
            continue
        try:
            return ImageFont.truetype(str(path), size, index=idx)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap_to_width(draw, text, font, max_w):
    """按像素宽度折行，优先在词边界断开"""
    if not text:
        return []
    if draw.textbbox((0, 0), text, font=font)[2] <= max_w:
        return [text]
    # 先按估算字符数折行，再逐行微调
    avg = draw.textbbox((0, 0), "M" * 20, font=font)[2] / 20
    guess = max(8, int(max_w / max(avg, 1)))
    lines = []
    for para in textwrap.wrap(text, width=guess, break_long_words=False):
        while draw.textbbox((0, 0), para, font=font)[2] > max_w:
            words = para.split(" ")
            if len(words) < 2:
                break
            cut = len(words) - 1
            while cut > 0 and draw.textbbox(
                    (0, 0), " ".join(words[:cut]), font=font)[2] > max_w:
                cut -= 1
            if cut == 0:
                break
            lines.append(" ".join(words[:cut]))
            para = " ".join(words[cut:])
        lines.append(para)
    return lines[:4]


def draw_card(main: str, sub: str, brand: str, domain: str) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 顶部品牌色条
    d.rectangle([0, 0, W, 14], fill=ACCENT)
    # 左侧竖条，形成视觉锚点
    d.rectangle([64, 150, 70, 470], fill=ACCENT)

    # 主标题：长度自适应字号
    size = 68 if len(main) <= 24 else (58 if len(main) <= 40 else 48)
    f_main = load_font(size)
    lines = wrap_to_width(d, main, f_main, W - 220)
    y = 170
    for ln in lines:
        d.text((96, y), ln, font=f_main, fill=INK)
        y += int(size * 1.22)

    # 副标题
    if sub:
        f_sub = load_font(32)
        for ln in wrap_to_width(d, sub, f_sub, W - 220)[:2]:
            d.text((96, y + 12), ln, font=f_sub, fill=MUTED)
            y += 46

    # 底部分隔线与页脚
    d.line([64, 500, W - 64, 500], fill=LINE, width=2)
    f_brand = load_font(30)
    d.text((64, 534), brand, font=f_brand, fill=ACCENT)
    f_dom = load_font(26)
    w_dom = d.textbbox((0, 0), domain, font=f_dom)[2]
    d.text((W - 64 - w_dom, 538), domain, font=f_dom, fill=MUTED)

    return img


def split_title(title: str) -> tuple[str, str]:
    """把 <title> 拆成主标题与副标题"""
    t = re.sub(r"\s+", " ", title).strip()
    for sep in (" — ", " – ", " - ", " | "):
        if sep in t:
            a, b = t.split(sep, 1)
            b = b.strip()
            if b.lower().startswith("real pay tools"):
                return a.strip(), ""
            return a.strip(), b
    return t, ""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    dom = "career.linwt.top"
    p = ROOT / "domain.txt"
    if p.exists():
        v = p.read_text(encoding="utf-8").strip().splitlines()
        if v:
            dom = v[0].strip()

    made = []
    for f in sorted(SRC.glob("*.html")):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"<title>(.*?)</title>", t, re.S)
        main_t, sub_t = split_title(m.group(1)) if m else ("Real Pay Tools", "")
        name = "home" if f.name == "index.html" else f.stem
        img = draw_card(main_t, sub_t, "Real Pay Tools", dom)
        out_png = OUT / f"{name}.png"
        img.save(out_png, "PNG", optimize=True)
        made.append((out_png.name, main_t, out_png.stat().st_size))

    print(f"生成 {len(made)} 张 OG 分享图 -> {OUT}")
    for n, t, s in made:
        print(f"  {n:38s} {s // 1024:>3d}KB  {t[:44]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
