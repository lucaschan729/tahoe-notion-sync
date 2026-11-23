import html as htmllib
import io
import re

import pdfplumber
import requests

NOTICE = "https://www.tahoelife.com.hk/tl/tc/important_notice/"
PDF = "https://www.tahoelife.com.hk/tl/doc/hfr_tc.pdf"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8"}
WORDS = ("分紅", "紅利", "實現率", "現金價值", "派息", "支付率")
S = re.S | re.I


def clean(s):
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=S)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def get(url):
    for label, headers in (("模擬 Chrome", UA), ("普通連線", {})):
        try:
            r = requests.get(url, headers=headers, timeout=60)
            print(f"[{label}] 狀態 {r.status_code}｜{len(r.content)} bytes｜"
                  f"{r.headers.get('content-type')}｜last-modified {r.headers.get('last-modified')}"
                  f"｜server {r.headers.get('server')}")
            if r.status_code == 200:
                return r
        except requests.RequestException as e:
            print(f"[{label}] {type(e).__name__}: {e}")
    return None


def notice():
    print("=== A. 重要通知頁 ===")
    r = get(NOTICE)
    if r is None:
        return
    page = r.content.decode("utf-8", errors="replace")
    for w in WORDS:
        print(f"「{w}」出現 {page.count(w)} 次")
    print("--- 表格行 ---")
    for tr in re.findall(r"<tr\b.*?</tr>", page, flags=S)[:40]:
        hrefs = re.findall(r'href="([^"]+)"', tr)
        print(clean(tr)[:80], "→", hrefs)
    print("--- 所有 PDF 連結 ---")
    for m in re.finditer(r'href="([^"]+\.pdf[^"]*)"', page, flags=re.I):
        print(m.group(1), "｜前文：", clean(page[max(0, m.start() - 300):m.start()])[-60:])


def pdf():
    print()
    print("=== B. 分紅實現率 PDF ===")
    r = get(PDF)
    if r is None or not r.content.startswith(b"%PDF"):
        print("不是 PDF 或讀取失敗")
        return
    doc = pdfplumber.open(io.BytesIO(r.content))
    print("文件資料：", doc.metadata)
    print(f"頁數：{len(doc.pages)}")
    total_pct, total_na = 0, 0
    for i, p in enumerate(doc.pages, 1):
        text = p.extract_text() or ""
        lines = [ln for ln in text.split("\n") if ln.strip()]
        tables = p.extract_tables()
        pcts = len(re.findall(r"\d+(?:\.\d+)?\s*%", text))
        nas = len(re.findall(r"不適用|N/A|N\.A\.|－|—", text))
        total_pct += pcts
        total_na += nas
        print()
        print(f"----- 第 {i} 頁｜{p.width:.0f}x{p.height:.0f}｜文字 {len(lines)} 行｜表格 {len(tables)} 個"
              f"｜百分比 {pcts} 個｜不適用類 {nas} 個 -----")
        limit = 60 if i <= 6 else 15
        for ln in lines[:limit]:
            print("T|", ln[:160])
        if len(lines) > limit:
            print(f"T| …（餘下 {len(lines) - limit} 行略）")
        for k, t in enumerate(tables, 1):
            cols = max((len(row) for row in t), default=0)
            print(f"[表格 {k}] {len(t)} 行 x {cols} 欄")
            for row in t[:40 if i <= 6 else 12]:
                print("R|", "｜".join("" if c is None else str(c).replace("\n", "⏎") for c in row)[:220])
    print()
    print(f"全文件：百分比 {total_pct} 個｜不適用類 {total_na} 個")


if __name__ == "__main__":
    notice()
    pdf()
    print()
    print("探查完成（只讀，沒有上傳）")
