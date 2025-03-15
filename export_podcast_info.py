import requests
from bs4 import BeautifulSoup
import os

def fetch_html(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def parse_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    title = soup.find('h1').text
    author = soup.find('a', {'rel': 'author'}).text
    summary = soup.find('div', {'class': 'summary'}).text.strip()
    image_url = soup.find('img', {'class': 'cover'})['src']
    audio_links = [a['href'] for a in soup.find_all('a', {'class': 'audio'})]
    return title, author, summary, image_url, audio_links

def create_rss_feed(title, author, summary, image_url, audio_links, output_file):
    rss_feed = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
    <channel>
        <title>{title}</title>
        <link>https://wolnelektury.pl</link>
        <language>pl</language>
        <itunes:author>{author}</itunes:author>
        <itunes:summary>{summary}</itunes:summary>
        <description>{summary}</description>
        <itunes:image href="{image_url}" />
        <itunes:category text="Arts">
            <itunes:category text="Books"/>
        </itunes:category>
        <itunes:type>serial</itunes:type>
    '''
    for i, link in enumerate(audio_links, start=1):
        rss_feed += f'''
        <item>
            <title>Episode {i}</title>
            <itunes:episode>{i}</itunes:episode>
            <itunes:author>{author}</itunes:author>
            <itunes:duration></itunes:duration>
            <link>{link}</link>
            <guid>{link}</guid>
            <enclosure url="{link}" type="audio/mpeg"/>
        </item>
        '''
    rss_feed += '''
    </channel>
</rss>
    '''
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(rss_feed)

def main():
    url = input("Enter the URL of the book page: ")
    html_content = fetch_html(url)
    title, author, summary, image_url, audio_links = parse_html(html_content)
    output_file = 'feedDziadyCzescIII.rss'
    create_rss_feed(title, author, summary, image_url, audio_links, output_file)
    print(f"RSS feed created: {output_file}")

if __name__ == "__main__":
    main()
