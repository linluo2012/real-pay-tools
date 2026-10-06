#!/usr/bin/env python3
"""
build.py — Real Pay Tools 构建脚本

第二站专属。与第一站（Small Profit Tools）完全独立：
独立目录、独立仓库、独立 Cloudflare Pages 项目、独立域名配置。
任何修改都不会触及第一站。

用法：
    python3 build.py career.linwt.top   # 本地构建到 site/
    python3 build.py --build            # Cloudflare Pages 云端构建到 dist/

流程：
    1. 递归复制 source/ → 输出目录，替换 example.com → 真实域名
    2. 生成 sitemap.xml、robots.txt、_headers
    3. 校验：JSON-LD 合法性、站内死链、占位域名残留
"""
import sys, os, pathlib, shutil, re, json

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "source"
OUT = ROOT / "site"
CF_OUT = ROOT / "dist"
PLACEHOLDER = "example.com"


def from_file(name: str) -> str:
    p = ROOT / name
    if not p.exists():
        return ""
    t = p.read_text(encoding="utf-8").strip()
    m = re.search(r'^SITE_DOMAIN\s*=\s*(.+)$', t, re.MULTILINE)
    if m:
        return m.group(1).strip().strip('"\'').lower()
    return t.splitlines()[0].strip().lower() if t else ""


def resolve_domain() -> str:
    env = os.environ.get("SITE_DOMAIN", "").strip()
    if env:
        return env.lower()
    for a in sys.argv[1:]:
        if not a.startswith("--") and "." in a:
            return a.lower()
    for name in (".env", "domain.txt"):
        v = from_file(name)
        if v:
            return v
    return PLACEHOLDER


def esc(s: str) -> str:
    """把文本安全地放进 HTML 属性里"""
    return (s.replace("&", "&amp;").replace('"', "&quot;")
             .replace("<", "&lt;").replace(">", "&gt;").strip())


def inject_og(text: str, domain: str, rel: str) -> tuple[str, bool]:
    """补全 Open Graph / Twitter Card 标签。

    求职垂类大量依赖 Reddit、X 分享冷启动，缺 og 标签时分享出去
    只是裸链接（无标题、无卡片图），点击率会显著下降。
    页面若已手写 og:title 则尊重原内容，不覆盖。
    """
    if 'property="og:title"' in text or "property='og:title'" in text:
        return text, False

    m = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    title = esc(re.sub(r"\s+", " ", m.group(1))) if m else "Real Pay Tools"

    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                  text, re.S | re.I)
    if not m:
        m = re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']',
                      text, re.S | re.I)
    desc = esc(re.sub(r"\s+", " ", m.group(1))) if m else ""

    stem = rel[:-5] if rel.endswith(".html") else rel
    url = f"https://{domain}" if rel == "index.html" else f"https://{domain}/{rel}"
    img = f"https://{domain}/og/{'home' if rel == 'index.html' else stem}.png"

    block = (
        f'  <meta property="og:type" content="website">\n'
        f'  <meta property="og:site_name" content="Real Pay Tools">\n'
        f'  <meta property="og:title" content="{title}">\n'
        f'  <meta property="og:description" content="{desc}">\n'
        f'  <meta property="og:url" content="{url}">\n'
        f'  <meta property="og:image" content="{img}">\n'
        f'  <meta property="og:image:width" content="1200">\n'
        f'  <meta property="og:image:height" content="630">\n'
        f'  <meta name="twitter:card" content="summary_large_image">\n'
        f'  <meta name="twitter:title" content="{title}">\n'
        f'  <meta name="twitter:description" content="{desc}">\n'
        f'  <meta name="twitter:image" content="{img}">\n'
    )
    if re.search(r"</head\s*>", text, re.I):
        text = re.sub(r"</head\s*>", block + "</head>", text, count=1, flags=re.I)
    else:
        text = text.replace("<body", block + "</head>\n<body", 1)
    return text, True


def build(domain: str, outdir: pathlib.Path) -> int:
    if not SRC.exists():
        print(f"错误：找不到 {SRC}")
        return 1

    pages = sorted(SRC.rglob("*.html"))
    if not pages:
        print(f"错误：{SRC} 里没有 html 文件")
        return 1

    outdir.mkdir(parents=True, exist_ok=True)

    changed = []
    og_added = []
    for f in pages:
        rel = f.relative_to(SRC)
        rel_s = str(rel).replace("\\", "/")
        out_file = outdir / rel
        out_file.parent.mkdir(parents=True, exist_ok=True)
        text = f.read_text(encoding="utf-8")
        n = text.count(PLACEHOLDER)
        if n:
            text = text.replace(PLACEHOLDER, domain)
            changed.append((rel_s, n))
        text, added = inject_og(text, domain, rel_s)
        if added:
            og_added.append(rel_s)
        out_file.write_text(text, encoding="utf-8")

    for extra in sorted(p for p in SRC.rglob("*") if p.is_file() and p.suffix != ".html"):
        rel = extra.relative_to(SRC)
        (outdir / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(extra, outdir / rel)

    built = sorted(str(p.relative_to(outdir)).replace("\\", "/")
                   for p in outdir.rglob("*.html"))
    order = ["index.html"] + [n for n in built if n != "index.html"]
    urls = []
    for name in order:
        loc = domain if name == "index.html" else f"{domain}/{name}"
        if "calculator" in name:
            pri, freq = "0.9", "weekly"
        elif name == "index.html" or name == "tools.html":
            pri, freq = "1.0", "weekly"
        else:
            pri, freq = "0.3", "yearly"
        urls.append(f"  <url>\n    <loc>https://{loc}</loc>\n"
                    f"    <changefreq>{freq}</changefreq>\n"
                    f"    <priority>{pri}</priority>\n  </url>")

    (outdir / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")

    (outdir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: https://{domain}/sitemap.xml\n",
        encoding="utf-8")

    (outdir / "_headers").write_text(
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  X-Frame-Options: SAMEORIGIN\n"
        "  Permissions-Policy: geolocation=(), microphone=(), camera=()\n"
        "\n"
        "/index.html\n"
        "  Cache-Control: no-cache\n"
        "\n"
        "/tools.html\n"
        "  Cache-Control: no-cache\n",
        encoding="utf-8")

    issues = []

    if domain == PLACEHOLDER:
        issues.append(
            f"域名未配置，构建使用了占位域名 {PLACEHOLDER}。\n"
            f"     修复方式：在 domain.txt 写入真实域名，或在 Cloudflare 后台设置环境变量 SITE_DOMAIN")

    leftover = []
    for f in sorted(outdir.rglob("*.html")):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(rf'href="https://{re.escape(PLACEHOLDER)}/([a-z0-9\-/\.]+\.html)"', t):
            leftover.append(f"{f.relative_to(outdir)} -> {m.group(1)}")
            break
    if leftover:
        issues.append(f"站内链接仍指向占位域名: {leftover}")

    for f in sorted(outdir.rglob("*.html")):
        rel = str(f.relative_to(outdir)).replace("\\", "/")
        t = f.read_text(encoding="utf-8")
        for i, b in enumerate(re.findall(
                r'<script type="application/ld\+json">(.*?)</script>', t, re.S)):
            try:
                json.loads(b)
            except Exception as e:
                issues.append(f"JSON-LD 非法 {rel}#{i+1}: {e}")
        for h in set(re.findall(rf'href="https://{re.escape(domain)}/([a-z0-9\-/\.]+\.html)"', t)):
            if h not in built and h != rel:
                issues.append(f"死链 {rel} -> {h}")

    print(f"domain:  {domain}")
    print(f"out:     {outdir}")
    print(f"pages:   {len(built)}")
    for name, n in changed:
        print(f"         {name:44s} {n} 处域名替换")
    if og_added:
        print(f"og:      为 {len(og_added)} 个页面补全 Open Graph / Twitter Card")
    missing_og = [p for p in og_added
                  if not (outdir / "og" / ("home.png" if p == "index.html"
                                           else p[:-5] + ".png")).exists()]
    if missing_og:
        issues.append(f"缺少 og 分享图（运行 make_og.py 生成）: {missing_og}")
    if issues:
        print("\n构建完成，但有问题:")
        for i in issues:
            print(f"  ! {i}")
    else:
        print("\n构建完成，无问题")
    return 1 if issues else 0


if __name__ == "__main__":
    cloud = "--build" in sys.argv
    dom = resolve_domain()
    target = CF_OUT if cloud else OUT
    sys.exit(build(dom, target))
