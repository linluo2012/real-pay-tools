#!/usr/bin/env python3
"""
submit_indexnow.py — 把站点 URL 主动推送给 Bing（IndexNow 协议）

为什么需要它：
    新站上线后，等搜索引擎自己来爬通常要几周。IndexNow 是「我更新了，你快来抓」的
    主动通知协议，Bing / Yandex / Seznam / Naver 都支持，通常几天内就能收录。

    ⚠️ Google 目前不支持 IndexNow —— Google 只能靠 Search Console 提交 sitemap
    和用 URL 检查工具请求索引。所以这个脚本和 GSC 是两条互补的路，都要走。

用法：
    python3 submit_indexnow.py                  # 推送线上 sitemap 里的全部 URL
    python3 submit_indexnow.py https://...      # 只推送指定 URL（新增页面后用它）

原理：
    站点根目录放一个 {key}.txt，内容就是 key 本身，用于验证你对这个域名有控制权。
    本脚本把它连同 URL 列表一起 POST 到 api.indexnow.org。
"""
import sys, json, pathlib, re, urllib.request

ROOT = pathlib.Path(__file__).parent
KEY_FILE = ROOT / ".indexnow_key"
API = "https://api.indexnow.org/IndexNow"


def domain() -> str:
    for name in ("domain.txt", ".env"):
        p = ROOT / name
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        m = re.search(r"^SITE_DOMAIN\s*=\s*(.+)$", t, re.MULTILINE)
        v = (m.group(1) if m else t.splitlines()[0]).strip().strip('"\'').lower()
        if v:
            return v
    return ""


def find_key() -> str:
    """key 不是秘密（协议要求它公开可访问），直接从站点文件里读"""
    if KEY_FILE.exists():
        return KEY_FILE.read_text(encoding="utf-8").strip()
    for p in sorted((ROOT / "source").glob("*.txt")):
        if p.name == "robots.txt":
            continue
        v = p.read_text(encoding="utf-8").strip()
        if v == p.stem:            # 文件名 == 内容，符合 IndexNow 要求
            return v
    return ""


def urls_from_sitemap(dom: str) -> list[str]:
    try:
        req = urllib.request.Request(
            f"https://{dom}/sitemap.xml",
            headers={"User-Agent": "Mozilla/5.0 (compatible; IndexNowSubmitter/1.0)"})
        xml = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"读取线上 sitemap 失败: {e}")
        print("提示：站点可能尚未部署，或网络被代理干扰")
        return []
    return re.findall(r"<loc>\s*(.*?)\s*</loc>", xml)


def submit(dom: str, key: str, urls: list[str]) -> int:
    if not urls:
        print("没有可提交的 URL")
        return 1
    payload = {
        "host": dom,
        "key": key,
        "keyLocation": f"https://{dom}/{key}.txt",
        "urlList": urls,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API, data=body,
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "Mozilla/5.0 (compatible; IndexNowSubmitter/1.0)"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code = r.getcode()
            print(f"提交成功：HTTP {code}（{len(urls)} 条 URL）")
            print("  Bing 通常需要几天完成抓取，不保证立刻收录")
            return 0
    except urllib.error.HTTPError as e:
        print(f"提交失败：HTTP {e.code}")
        print("  200 = 已接受；202 = 已排队；400 = 请求格式错；403 = key 无效；429 = 太频繁")
        try:
            print("  响应体:", e.read().decode("utf-8", "ignore")[:300])
        except Exception:
            pass
        return 1
    except Exception as e:
        print(f"提交失败：{e}")
        return 1


def main() -> int:
    dom = domain()
    key = find_key()
    if not dom:
        print("错误：读不到域名，检查 domain.txt")
        return 1
    if not key:
        print("错误：找不到 IndexNow key 文件（source/{key}.txt）")
        return 1

    if len(sys.argv) > 1:
        urls = [u for u in sys.argv[1:] if u.startswith("http")]
    else:
        urls = urls_from_sitemap(dom)

    print(f"host:  {dom}")
    print(f"key:   {key}")
    print(f"urls:  {len(urls)}")
    for u in urls[:6]:
        print(f"       {u}")
    if len(urls) > 6:
        print(f"       ... 共 {len(urls)} 条")
    print()
    return submit(dom, key, urls)


if __name__ == "__main__":
    sys.exit(main())
