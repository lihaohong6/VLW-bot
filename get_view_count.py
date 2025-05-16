import re

import requests
from bs4 import BeautifulSoup

table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
tr = {}
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
    # bilibili doesn't like scrapers; use typical browser UA
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'})
    response = response.json()
    pic = response['data']['pic']
    views = response['data']['stat']['view']
    return views


def get_yt_views(vid: str) -> int:
    url = 'https://www.youtube.com/watch?v=' + vid
    response = requests.get(url).text
    soup = BeautifulSoup(response, 'html.parser')
    for script in soup.find_all("script"):
        text = script.text
        if not "ytInitialData" in text:
            continue
        break
    else:
        return 0
    match = re.search(r'"simpleText":"([\d,]+) views"', text)
    if match is None:
        return 0
    views = int(match.group(1).replace(',', ''))
    return views


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
