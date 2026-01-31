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

    
    print("\n".join(msg))   # ✅ 唯一 print


from datetime import datetime
today_str = datetime.now().strftime("%Y-%m-%d")

global_items = []
china_items = []

# 这里是你抓 RSS、筛关键词、append title 的逻辑

    

# ===== Generate Xiaohongshu-style daily (viral structure) =====
def pick(items, n=3):
    # 取前 n 条，避免空
    return items[:n] if items else []

top_global = pick(global_items, 3)
top_china = pick(china_items, 3)

# 组合今日Top3（优先全球+中国混合）
top3 = (top_global + top_china)[:3]

# 自动生成“3句结论”（不接AI，规则化但很像真人）
conclusions = []
if len(global_items) + len(china_items) >= 8:
    conclusions.append("① 信息密度很高：硬件/供应链相关更新明显加速。")
else:
    conclusions.append("① 今天不算爆量，但主线依然清晰：算力与供应链。")

if len(china_items) >= 3:
    conclusions.append("② 中国相关动态占比上来了：不只是跟进，也开始“定节奏”。")
else:
    conclusions.append("② 海外仍更活跃：新品/数据中心/芯片仍在抢头条。")

conclusions.append("③ 结论：AI 硬件竞争已从“单点性能”转向“系统与生态”。")

# 3个看点：直接引用今日Top3标题（更真实、更省事）
highlights = []
for i, t in enumerate(top3, 1):
    highlights.append(f"{i}. {t}")

# 一句金句（固定但很像栏目slogan）
golden = "金句：算力不是未来，算力“被正确使用”才是未来。"

# Hashtags（固定+轻量，避免太“营销”）
tags = "#AI硬件 #芯片 #算力 #数据中心 #机器人 #科技资讯 #每日资讯"

xhs = []
# 标题：短、强、带日期
xhs.append(f"📌 AI硬件日报｜{today_str}｜今天3个信号")
xhs.append("")
# 开头钩子
xhs.append("今天的 AI 硬件圈，我只想说：别盯着参数表，真正的战场是“系统”。")
xhs.append("")
# 3句结论
xhs.append("✅ 3句结论（先看趋势）")
for c in conclusions:
    xhs.append(c)
xhs.append("")
# 3个看点
xhs.append("🔥 3个看点（今天最值得点开）")
if highlights:
    xhs.extend(highlights)
else:
    xhs.append("1. 今天抓到的有效新闻较少（建议放宽关键词或增加RSS源）。")
xhs.append("")
# 海外/中国分区（给喜欢信息密度的人）
xhs.append("🌍 海外 AI 硬件动态（精选）")
if global_items:
    for i, t in enumerate(global_items[:5], 1):
        xhs.append(f"{i}️⃣ {t}")
else:
    xhs.append("- 今天没抓到符合关键词的海外新闻，可在 config/feeds.yaml 放宽关键词或加源。")
xhs.append("")
xhs.append("🇨🇳 中国 AI 硬件观察（精选）")
if china_items:
    for i, t in enumerate(china_items[:5], 1):
        xhs.append(f"{i}️⃣ {t}")
else:
    xhs.append("- 今天没抓到符合关键词的中国新闻，可在 config/feeds.yaml 放宽关键词或加源。")
xhs.append("")
# 金句 + 互动
xhs.append(f"💬 {golden}")
xhs.append("")
xhs.append("🗣️ 互动：你更看好哪条赛道？（1）芯片（2）机器人（3）端侧AI（4）数据中心")
xhs.append(tags)

with open("daily_xhs.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(xhs) + "\n")


 


if __name__ == "__main__":
    main()
