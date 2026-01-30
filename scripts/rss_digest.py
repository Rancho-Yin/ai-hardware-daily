import re
import sys
import yaml
import feedparser
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser

def load_keywords(path: str):
    kws = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            k = line.strip()
            if k and not k.startswith("#"):
                kws.append(k.lower())
    return kws

def text_match(text: str, keywords):
    t = (text or "").lower()
    return any(k in t for k in keywords)

def parse_dt(entry):
    # Try common RSS date fields
    for k in ("published", "updated", "created"):
        if k in entry and entry[k]:
            try:
                return dateparser.parse(entry[k])
            except Exception:
                pass
    # feedparser sometimes provides struct_time
    for k in ("published_parsed", "updated_parsed"):
        if k in entry and entry[k]:
            try:
                return datetime(*entry[k][:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None

def clean_title(s: str):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s

def fetch_items(feed_urls, keywords, start_dt, end_dt, limit=12, label=""):
    items = []
    seen = set()

    for url in feed_urls:
        d = feedparser.parse(url)
    total = len(getattr(d, "entries", []) or [])
    print(f"[DEBUG] {label} feed={url} entries={total}")

    for e in (d.entries[:50] if getattr(d, "entries", None) else []):
            title = clean_title(getattr(e, "title", ""))
            link = getattr(e, "link", "")
            summary = getattr(e, "summary", "") or getattr(e, "description", "")
            dt = parse_dt(e)

            if not title or not link:
                continue

            # Time filter: only D-1 window
            if dt is None:
                # If no time, keep but rank lower; we'll still allow it if keyword matches
                pass
            else:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if not (start_dt <= dt.astimezone(timezone.utc) < end_dt):
                    continue

            if not (text_match(title, keywords) or text_match(summary, keywords)):
                continue

            key = title.lower()
            if key in seen:
                continue
            seen.add(key)

            items.append((dt or datetime(1970,1,1,tzinfo=timezone.utc), title, link, url))

    # Newer first; unknown dates sink
    items.sort(key=lambda x: x[0], reverse=True)
    return items[:limit]

def main():
    # Beijing time window for "yesterday"
    tz_bj = timezone(timedelta(hours=8))
    now_bj = datetime.now(tz_bj)
    yday_bj = (now_bj - timedelta(days=1)).date()

    start_bj = datetime(yday_bj.year, yday_bj.month, yday_bj.day, 0, 0, 0, tzinfo=tz_bj)
    end_bj = start_bj + timedelta(days=1)

    start_utc = start_bj.astimezone(timezone.utc)
    end_utc = end_bj.astimezone(timezone.utc)

    with open("config/feeds.yaml", "r", encoding="utf-8") as f:
        feeds = yaml.safe_load(f)

    keywords = load_keywords("config/keywords.txt")

    global_items = fetch_items(feeds.get("global", []), keywords, start_utc, end_utc, limit=10, label="GLOBAL")
china_items = fetch_items(feeds.get("china", []), keywords, start_utc, end_utc, limit=10, label="CHINA")

    today_str = now_bj.strftime("%Y-%m-%d")
    yday_str = yday_bj.strftime("%Y-%m-%d")

    def fmt(items):
        if not items:
            return ["（未抓到符合关键词的新闻，可在 config/feeds.yaml 增加源或放宽关键词）"]
        out = []
        for i, (_, title, link, _) in enumerate(items, 1):
            out.append(f"{i}. {title}\n{link}")
        return out

    msg = []
    msg.append(f"🤖 AI硬件日报｜{today_str}（抓取 {yday_str}）")
    msg.append("")
    msg.append("🌍 全球")
    msg.extend(fmt(global_items))
    msg.append("")
    msg.append("🇨🇳 中国")
    msg.extend(fmt(china_items))
    msg.append("")
    msg.append("📌 说明：本日报为 RSS+关键词筛选（半自动），如需“要点总结/趋势判断”，下一步再升级到全自动 AI 版本。")

    print("\n".join(msg))

if __name__ == "__main__":
    main()
