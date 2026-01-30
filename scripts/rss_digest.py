import re
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
    for k in ("published", "updated", "created"):
        if k in entry and entry[k]:
            try:
                return dateparser.parse(entry[k])
            except Exception:
                pass
    for k in ("published_parsed", "updated_parsed"):
        if k in entry and entry[k]:
            try:
                return datetime(*entry[k][:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


    def tag_for(title: str):
    t = (title or "").lower()

    if any(k in t for k in ["gpu", "npu", "hbm", "chip", "semiconductor", "tsmc", "封装", "制程", "芯片", "算力", "昇腾", "国产gpu"]):
        return "【芯片/算力】"
    if any(k in t for k in ["server", "datacenter", "数据中心", "液冷", "cooling", "交换", "800g", "光模块", "网络"]):
        return "【数据中心】"
    if any(k in t for k in ["robot", "humanoid", "机器人", "具身", "人形"]):
        return "【机器人】"
    if any(k in t for k in ["pc", "laptop", "手机", "端侧", "edge", "终端"]):
        return "【终端/边缘】"
    if any(k in t for k in ["融资", "ipo", "并购", "investment", "funding", "政策", "补贴"]):
        return "【投融资/政策】"
    return "【其他】"


def fetch_items(feed_urls, keywords, start_dt, end_dt, limit=10):
    items = []
    seen = set()

    for url in feed_urls:
        try:
            d = feedparser.parse(url)
        except Exception:
            continue

        entries = getattr(d, "entries", None) or []
        for e in entries[:50]:
            title = clean_title(getattr(e, "title", ""))
            link = getattr(e, "link", "")
            summary = getattr(e, "summary", "") or getattr(e, "description", "")

            if not title or not link:
                continue

            dt = parse_dt(e)
            if dt is not None:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_utc = dt.astimezone(timezone.utc)
                if not (start_dt <= dt_utc < end_dt):
                    continue

            if not (text_match(title, keywords) or text_match(summary, keywords)):
                continue

            key = title.lower()
            if key in seen:
                continue
            seen.add(key)

            items.append((dt or datetime(1970, 1, 1, tzinfo=timezone.utc), title, link))

    items.sort(key=lambda x: x[0], reverse=True)
    return items[:limit]


def main():
    # 时间窗口：北京时间昨天
    tz_bj = timezone(timedelta(hours=8))
    now_bj = datetime.now(tz_bj)
    yday_bj = (now_bj - timedelta(days=1)).date()

    start_bj = datetime(yday_bj.year, yday_bj.month, yday_bj.day, 0, 0, 0, tzinfo=tz_bj)
    end_bj = start_bj + timedelta(days=1)
    start_utc = start_bj.astimezone(timezone.utc)
    end_utc = end_bj.astimezone(timezone.utc)

    # ✅ 这里是 feeds 的唯一定义位置（非常关键）
    with open("config/feeds.yaml", "r", encoding="utf-8") as f:
        feeds = yaml.safe_load(f) or {}

    keywords = load_keywords("config/keywords.txt")

    global_items = fetch_items(
        feeds.get("global", []),
        keywords,
        start_utc,
        end_utc,
        limit=6
    )

    china_items = fetch_items(
        feeds.get("china", []),
        keywords,
        start_utc,
        end_utc,
        limit=6
    )

    # 兜底：如果中国没有命中关键词，取最新 3 条
    if not china_items:
        china_items = fetch_items(
            feeds.get("china", []),
            [" "],
            start_utc,
            end_utc,
            limit=3
        )

    today_str = now_bj.strftime("%Y-%m-%d")
    yday_str = yday_bj.strftime("%Y-%m-%d")

    def fmt(items):
        if not items:
            return ["（未抓到符合条件的新闻）"]
        out = []
        for i, (_, title, link) in enumerate(items, 1):
            out.append(f"{i}. {tag_for(title)} {title}\n{link}")
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
    msg.append("📌 说明：本日报为 RSS + 关键词筛选（半自动）。")

    print("\n".join(msg))


if __name__ == "__main__":
    main()
