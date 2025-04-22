import os
import feedparser
import requests
import io
from notion_client import Client
from PIL import Image
from dotenv import load_dotenv

# .env ファイルから環境変数を読み込む
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
RSS_FEED    = os.getenv("RSS_FEED")

# Notion クライアント初期化
notion = Client(auth=NOTION_TOKEN)

# RSS フィードを解析
feed   = feedparser.parse(RSS_FEED)
latest = feed.entries[0]

# ① 重複チェック：Link プロパティに同じ URL がないか検索
query = notion.databases.query(
    **{
        "database_id": NOTION_DB_ID,
        "filter": {
            "property": "Link",
            "url": {"equals": latest.link}
        }
    }
)
if query["results"]:
    print("Already registered.")
    exit()

# ② カバー画像の正方形化処理
cover_url = getattr(latest, "itunes_image", None) or feed.feed.image.href
img_data  = requests.get(cover_url).content
img       = Image.open(io.BytesIO(img_data))
sq        = max(img.size)
canvas    = Image.new("RGB", (sq, sq), "white")
canvas.paste(img, ((sq - img.width)//2, (sq - img.height)//2))
buf = io.BytesIO()
canvas.save(buf, format="JPEG", quality=85)
buf.seek(0)

# ③ Notion に新規ページを作成
notion.pages.create(
    parent={"database_id": NOTION_DB_ID},
    properties={
        "Title":    {"title": [{"text": {"content": latest.title}}]},
        "Pub Date": {"date":  {"start": latest.published}},
        "Link":     {"url":   latest.link},
        "Cover":    {
            "files": [{
                "name": "cover.jpg",
                "type": "external",
                "external": {"url": cover_url}
            }]
        },
    }
)

print("New episode synced:", latest.title)
