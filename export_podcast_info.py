import datetime
import requests
from bs4 import BeautifulSoup, Tag

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
    audio_links = [li["data-mp3"] for li in player_element.find_all("li")]
    episode_titles = [
        span.text for span in player_element.find_all("span", {"class": "title"})
    ]
    episode_duration = [li["data-duration"] for li in player_element.find_all("li")]
    return (
        title,
        author,
        summary,
        image_url,
        audio_links,
        episode_titles,
        episode_duration,
    )


def create_rss_feed(
    title,
    author,
    summary,
    image_url,
    audio_links,
    episode_titles,
    episode_duration,
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
    for i, link in enumerate(audio_links, start=1):
        rss_feed += f"""
        <item>
            <pubDate>{date}</pubDate>
            <title>{episode_titles[i-1].strip()}</title>
            <itunes:episode>{i}</itunes:episode>
            <itunes:author>{author}</itunes:author>
            <itunes:duration>{episode_duration[i-1]}</itunes:duration>
            <link>{main_url + link}</link>
            <guid>{main_url + link}</guid>
            <enclosure url="{main_url + link}" type="audio/mpeg"/>
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


def main():
    url = input("Enter the URL of the book page: ")
    # url = "https://wolnelektury.pl/katalog/lektura/dziady-dziady-poema-dziady-czesc-iii/"
    html_content = fetch_html(url)
    title, author, summary, image_url, audio_links, episode_titles, episode_duration = (
        parse_html(html_content)
    )
    output_file = format_title(title)
    create_rss_feed(
        title,
        author,
        summary,
        image_url,
        audio_links,
        episode_titles,
        episode_duration,
        output_file,
    )
    print(f"RSS feed created: {output_file}")


if __name__ == "__main__":
    main()
