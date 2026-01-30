import re
import yaml
import feedparser
import socket
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser
def clean_title(s: str):
    if not s:
        return ""
    return " ".join(s.split())


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


    



def fetch_items(feed_urls, keywords, start_dt, end_dt, limit=10):
    items = []
    seen = set()

    for url in feed_urls:
        socket.setdefaulttimeout(10)    
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
    msg.append("📌 说明：本日报为 RSS + 关键词筛选（半自动）。")

    
    print("\n".join(msg))


from datetime import datetime
today_str = datetime.now().strftime("%Y-%m-%d")

global_items = []
china_items = []

# 这里是你抓 RSS、筛关键词、append title 的逻辑

    

# ===== Generate Xiaohongshu-style daily =====
xhs = []
xhs.append(f"🤖 今天 AI 硬件圈发生了什么？｜{today_str}")
xhs.append("")
xhs.append("一句话先看趋势：")
xhs.append("👉 芯片 / 算力 / 供应链依然是核心主线，中国相关动态密度明显上升。")
xhs.append("")

xhs.append("🌍 海外 AI 硬件动态")
if global_items:
    for i, t in enumerate(global_items[:5], 1):
        xhsa = ["0️⃣","1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        xhs.append(f"{i}️⃣ {t}" if i < 10 else f"{i}. {t}")
else:
    xhs.append("- 今天没抓到符合关键词的海外新闻，可在 config/feeds.yaml 放宽关键词或加源。")

xhs.append("")
xhs.append("🇨🇳 中国 AI 硬件观察")
if china_items:
    for i, t in enumerate(china_items[:5], 1):
        xhs.append(f"{i}️⃣ {t}" if i < 10 else f"{i}. {t}")
else:
    xhs.append("- 今天没抓到符合关键词的中国新闻，可在 config/feeds.yaml 放宽关键词或加源。")

xhs.append("")
xhs.append("📌 今天你可以关注：")
xhs.append("- AI 芯片不再只拼算力，而是系统与生态")
xhs.append("- 硬件与应用场景的结合正在加速")
xhs.append("")
xhs.append("#AI硬件 #芯片 #算力 #科技资讯 #每日资讯")

with open("daily_xhs.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(xhs) + "\n")

 
    print("\n".join(out))


if __name__ == "__main__":
    main()
