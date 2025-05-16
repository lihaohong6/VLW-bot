from datetime import datetime
import logging
import re
import sys
from enum import Enum
from typing import Callable

import requests
from bs4 import BeautifulSoup
from pywikibot.pagegenerators import PreloadingGenerator, GeneratorFactory
from wikitextparser import WikiText, Template, parse

def get_logger(name: str = "logger") -> logging.Logger:
    logging.basicConfig(level=logging.INFO,
                        filename=f"{name}_log.txt",
                        filemode="a",
                        encoding="utf-8")
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger

logger = get_logger()

def normalize_template_name(template_name: str) -> str:
    return template_name.lower().strip().replace(" ", "_")


def get_templates_by_name(wikitext: WikiText, name: str) -> list[Template]:
    result = []
    for t in wikitext.templates:
        if normalize_template_name(t.name) == normalize_template_name(name):
            result.append(t)
    return result

class VideoSite(Enum):
    Bilibili = 'BB'
    YouTube = 'YT'
    NicoNico = 'NN'

VideoLinks = dict[VideoSite, list[str]]

table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
tr = {}
for index in range(58):
    tr[table[index]] = index
s = [11, 10, 3, 8, 4, 6]
xor = 177451812
add = 8728348608

def av_to_bv(av: str) -> str:
    x = int(av[2:])
    x = (x ^ xor) + add
    r = list('BV1  4 1 7  ')
    for i in range(6):
        r[s[i]] = table[x // 58 ** i % 58]
    return ''.join(r)

def get_bv(vid: str) -> str:
    search_bv = re.search("BV[0-9a-zA-Z]+", vid, re.IGNORECASE)
    if search_bv is not None:
        return search_bv.group(0)
    search_av = re.search("av[0-9]+", vid, re.IGNORECASE)
    if search_av is not None:
        return av_to_bv(search_av.group(0))
    return vid

def get_bb_views(vid: str) -> int:
    vid = get_bv(vid)
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={vid}"
    response = requests.get(url).json()
    pic = response['data']['pic']
    views = response['data']['stat']['view']
    return views


def get_yt_views(vid: str) -> int:
    url = 'https://www.youtube.com/watch?v=' + vid
    text = requests.get(url).text
    match = re.search(r'"simpleText":"([\d,]+) views"', text)
    if match is None:
        return 0
    views = int(match.group(1).replace(',', ''))
    return views


def format_views(views: int) -> str:
    string = str(views)
    num_digits = len(str(views))

    if num_digits >= 6:
        keep_digits = 3
    elif num_digits >= 4:
        keep_digits = 2
    else:
        keep_digits = 1
    string = string[:keep_digits] + "0" * (num_digits - keep_digits)
    return '{:,}'.format(int(string))

def get_nn_views_old(vid: str) -> int:
    url = f"https://www.nicovideo.jp/watch/{vid}"
    result = requests.get(url).text
    soup = BeautifulSoup(result, "html.parser")
    views = 0
    for script in soup.find_all('script'):
        t: str = script.get_text()
        index_start = t.find("userInteractionCount")
        if index_start != -1:
            index_start += len("userInteractionCount") + 2
            index_end = t.find("}", index_start)
            views = int(t[index_start:index_end])
    return views


def get_nn_views(vid: str) -> int:
    result = requests.get(f"https://ext.nicovideo.jp/api/getthumbinfo/{vid}").text
    match = re.search(r"<view_counter>(\d+)</view_counter>", result)
    if match:
        return int(match.group(1))
    return 0


def process_views(match: re.Match, links: VideoLinks, permissive: bool = False) -> str:
    original = match.group(0)
    original_views = int(match.group("views").replace(",", ""))

    dispatcher: dict[str, tuple[VideoSite, Callable[[str], int]]] = {
        'BB': (VideoSite.Bilibili, get_bb_views),
        'YT': (VideoSite.YouTube, get_yt_views),
        'NN': (VideoSite.NicoNico, get_nn_views)
    }

    video_site: VideoSite
    if permissive:
        for link_site, link_list in links.items():
            assert len(link_list) == 1
            site = link_site.value
            break
    else:
        site = match.group("site")
    if site not in dispatcher:
        return original
    video_site, func = dispatcher[site]
    video_ids = links.get(video_site, [])
    # Multiple uploads to the same website. This is tricky, so we don't want to deal with it.
    if len(video_ids) != 1:
        return original
    try:
        views = func(video_ids[0])
    except Exception as e:
        return original
    if views <= 0:
        return original
    if views < original_views * 1.5 or views < 1000:
        return original
    view_start, view_end = match.span("views")
    return original[:view_start] + format_views(views) + original[view_end:]


def parse_links(links: str) -> tuple[VideoLinks, int]:
    result: VideoLinks = {}
    num_links = 0

    def add(site: VideoSite, video_id: str) -> None:
        nonlocal num_links
        num_links += 1
        if site not in result:
            result[site] = []
        result[site].append(video_id)

    for template in get_templates_by_name(parse(links), "#"):
        arg1 = template.arguments[0]
        if not arg1:
            continue
        if arg1.name != "1":
            # YouTube links have a = in them
            link = arg1.name + "=" + arg1.value
        else:
            link = arg1.value.strip()
        match = re.search(r"nicovideo\.jp/watch/([a-z0-9]+)$", link)
        if match:
            add(VideoSite.NicoNico, match.group(1))
            continue
        match = re.search(r"youtube.com/watch\?v=([^ /&]+)$", link)
        if match:
            add(VideoSite.YouTube, match.group(1))
            continue
        match = re.search(r"bilibili.com/video/([^ /&]+)$", link)
        if match:
            add(VideoSite.Bilibili, match.group(1))
            continue
    return result, num_links

def process_template(template: Template) -> bool:
    view_arg = template.get_arg("#views")
    link_arg = template.get_arg("link")
    if not view_arg or not link_arg:
        return False
    views = view_arg.value
    links, num_links = parse_links(link_arg.value)

    new_views, count = re.subn(r"( |^)(?P<views>[\d,]+)\+? \((?P<site>NN|YT|BB)\)",
                               lambda m: process_views(m, links, False),
                               views)

    if num_links == 1 and count == 0:
        new_views, count = re.subn(r"(\s|^)(?P<views>[\d,]+)\+?(\s|$)",
                                   lambda m: process_views(m, links, True),
                                   views)
        assert count == 1

    if views == new_views:
        return False

    view_arg.value = new_views

    return True


def main():
    gen = GeneratorFactory()
    gen.handle_args(['-start:------TRIP_LINE------', "-ns:0"])
    gen = gen.getCombinedGenerator(preload=True)
    for page in gen:
        text = page.text
        if not re.search("infobox[ _]song", text, re.IGNORECASE):
            continue
        parsed = parse(text)
        templates = get_templates_by_name(parsed, "Infobox Song")
        edit_made = False
        for template in templates:
            res = process_template(template)
            edit_made = res or edit_made
        if not edit_made:
            continue
        setattr(page, "_bot_may_edit", True)
        page.text = str(parsed)
        page.save(summary="update view count ([[User:PetraMagna/Bots/View count|bot]])", bot=True)


if __name__ == '__main__':
    main()