import json
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET


ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = ROOT_DIR / "feeds.json"


def read_feed_title(feed_path: Path) -> str:
    try:
        tree = ET.parse(feed_path)
        title = tree.findtext("./channel/title")
        if title:
            return title.strip()
    except ET.ParseError:
        pass
    return feed_path.stem.replace("_", " ").strip()


def build_feed_record(feed_path: Path) -> dict:
    return {
        "file": feed_path.name,
        "title": read_feed_title(feed_path),
        "url": quote(feed_path.name),
        "size_bytes": feed_path.stat().st_size,
    }


def update_feed_list() -> None:
    feeds = sorted(ROOT_DIR.glob("*.rss"), key=lambda item: item.name.lower())
    data = {"feeds": [build_feed_record(feed) for feed in feeds]}
    OUTPUT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Feed list updated: {OUTPUT_FILE.name} ({len(feeds)} items)")


if __name__ == "__main__":
    update_feed_list()
