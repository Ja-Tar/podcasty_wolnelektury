import datetime
import requests
from bs4 import BeautifulSoup, Tag
import sys
import os
import re

main_url = "https://wolnelektury.pl"


def fetch_html(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def parse_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    title = getattr(soup.find("h1"), "text", "")
    all_author_links = soup.find("div", {"class": "l-header__content"}) or Tag()
    author = getattr(all_author_links.find("a"), "text", "")
    summary = getattr(soup.find("ul", {"class": "l-aside__info"}), "text", "").strip()
    only_l_elements = soup.find("figure", {"class": "only-l"}) or Tag()
    image_element = only_l_elements.find("img") or Tag()
    image_url = image_element["src"]
    player_element = soup.find("div", {"class": "c-player__chapters"}) or Tag()
    chapter_items = player_element.find_all("li")
    audio_links = [li["data-mp3"] for li in chapter_items]
    episode_titles = [
        getattr(li.find("span", {"class": "title"}), "text", "") for li in chapter_items
    ]
    episode_duration = [li["data-duration"] for li in chapter_items]
    episode_metadata = [parse_episode_metadata_from_attrs(li) for li in chapter_items]
    return (
        title,
        author,
        summary,
        image_url,
        audio_links,
        episode_titles,
        episode_duration,
        episode_metadata,
    )


def create_rss_feed(
    title,
    author,
    summary,
    image_url,
    audio_links,
    episode_titles,
    episode_duration,
    episode_metadata,
    output_file,
):
    rss_feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
    <channel>
        <title>{title}</title>
        <link>https://wolnelektury.pl</link>
        <language>pl</language>
        <itunes:author>{author}</itunes:author>
        <itunes:summary>{summary}</itunes:summary>
        <description>{summary}</description>
        <itunes:image href="{main_url + image_url}"/>
        <itunes:category text="Arts">
            <itunes:category text="Books"/>
        </itunes:category>
        <itunes:type>serial</itunes:type>
        <itunes:complete>Yes</itunes:complete>
    """
    date = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
    episode_records = order_episode_records(
        audio_links, episode_titles, episode_duration, episode_metadata
    )
    for i, record in enumerate(episode_records, start=1):
        episode_tag = record["episode"] if record["episode"] is not None else i
        season_tag = (
            f"\n            <itunes:season>{record['season']}</itunes:season>"
            if record["season"] is not None
            else ""
        )
        rss_feed += f"""
        <item>
            <pubDate>{date}</pubDate>
            <title>{record["title"].strip()}</title>
            <itunes:episode>{episode_tag}</itunes:episode>{season_tag}
            <itunes:author>{author}</itunes:author>
            <itunes:duration>{record["duration"]}</itunes:duration>
            <link>{main_url + record["link"]}</link>
            <guid>{main_url + record["link"]}</guid>
            <enclosure url="{main_url + record["link"]}" type="audio/mpeg"/>
        </item>
        """
    rss_feed += """
    </channel>
</rss>
    """
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(rss_feed)


def format_title(title):
    title = "".join(e for e in title if e.isalnum() or e.isspace())
    return title.replace(" ", "_").lower() + ".rss"


def roman_to_int(roman):
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for char in reversed(roman.upper()):
        value = values.get(char)
        if value is None:
            return None
        if value < prev:
            total -= value
        else:
            total += value
            prev = value
    return total


def parse_number(value):
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if cleaned.isdigit():
        return int(cleaned)
    return roman_to_int(cleaned)


def parse_episode_metadata_from_title(title):
    match = re.search(
        r"\bTom\s+([IVXLCDM\d]+)\s*,\s*Rozdział\s+([IVXLCDM\d]+)\b",
        title,
        re.IGNORECASE,
    )
    if match:
        season = parse_number(match.group(1))
        episode = parse_number(match.group(2))
        if season is not None and episode is not None:
            return season, episode

    match = re.search(
        r"\bAkt\s+([IVXLCDM\d]+)\s*,\s*Scena\s+([IVXLCDM\d]+)\b", title, re.IGNORECASE
    )
    if not match:
        return None, None
    season = parse_number(match.group(1))
    episode = parse_number(match.group(2))
    if season is None or episode is None:
        return None, None
    return season, episode


def parse_episode_metadata_from_attrs(item):
    attrs = getattr(item, "attrs", {})
    season_candidates = [
        "data-season",
        "data-part",
        "data-volume",
        "data-tom",
        "data-book",
    ]
    episode_candidates = [
        "data-episode",
        "data-chapter",
        "data-rozdzial",
        "data-scena",
        "data-track",
    ]
    season = None
    episode = None
    for key in season_candidates:
        season = parse_number(attrs.get(key))
        if season is not None:
            break
    for key in episode_candidates:
        episode = parse_number(attrs.get(key))
        if episode is not None:
            break
    return season, episode


def order_episode_records(audio_links, episode_titles, episode_duration, episode_metadata):
    def is_act_scene_record(record):
        return record["season"] is not None and record["episode"] is not None

    records = []
    for idx, (link, title, duration, metadata) in enumerate(
        zip(audio_links, episode_titles, episode_duration, episode_metadata)
    ):
        season, episode = metadata
        if season is None or episode is None:
            season, episode = parse_episode_metadata_from_title(title.strip())
        records.append(
            {
                "index": idx,
                "link": link,
                "title": title,
                "duration": duration,
                "season": season,
                "episode": episode,
            }
        )

    act_scene_sorted = sorted(
        (r for r in records if is_act_scene_record(r)),
        key=lambda r: (r["season"], r["episode"], r["index"]),
    )
    sorted_iter = iter(act_scene_sorted)

    ordered_records = []
    for record in records:
        if is_act_scene_record(record):
            ordered_records.append(next(sorted_iter))
        else:
            ordered_records.append(record)
    return ordered_records


def main():
    # Najpierw sprawdź argument przekazany w CLI, potem zmienną środowiskową PODCAST_URL, a jako fallback - prompt.
    url = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        url = sys.argv[1].strip()
    else:
        url = os.environ.get("PODCAST_URL")

    if not url:
        try:
            url = input("Enter the URL of the book page: ")
        except EOFError:
            print("No URL provided. Exiting.")
            return

    html_content = fetch_html(url)
    (
        title,
        author,
        summary,
        image_url,
        audio_links,
        episode_titles,
        episode_duration,
        episode_metadata,
    ) = parse_html(html_content)
    output_file = format_title(title)
    create_rss_feed(
        title,
        author,
        summary,
        image_url,
        audio_links,
        episode_titles,
        episode_duration,
        episode_metadata,
        output_file,
    )
    print(f"RSS feed created: {output_file}")


if __name__ == "__main__":
    main()
