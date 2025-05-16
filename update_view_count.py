import logging
import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from pywikibot.pagegenerators import GeneratorFactory
from wikitextparser import WikiText, Template, parse

from get_view_count import table, tr, get_bb_views, get_yt_views, get_nn_views


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

for index in range(58):
    tr[table[index]] = index


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


def should_update_views(original_views: int, new_views: int) -> bool:
    assert original_views <= new_views, f"New views smaller than original views: {new_views} < {original_views}"
    return new_views >= 1000 and new_views >= original_views * 1.5


# For testing purposes only
video_view_overrides: dict[str, int] = {}


def override_video_view_count(vid: str, count: int) -> None:
    video_view_overrides[vid] = count


@dataclass
class ViewQueryResult:
    old_views: int
    new_views: int
    old_string: str
    new_string: str


def process_views(match: re.Match, links: VideoLinks, permissive: bool = False) -> ViewQueryResult | None:
    original = match.group(0)
    original_views = int(match.group("views").replace(",", ""))

    dispatcher: dict[VideoSite, Callable[[str], int]] = {
        VideoSite.Bilibili: get_bb_views,
        VideoSite.YouTube: get_yt_views,
        VideoSite.NicoNico: get_nn_views,
    }

    if permissive:
        for link_site, link_list in links.items():
            assert len(link_list) == 1
            site = link_site
            break
    else:
        site = VideoSite(match.group("site"))
    if site not in dispatcher:
        return None
    video_ids = links.get(site, [])
    # Multiple uploads to the same website. This is tricky, so we don't want to deal with it.
    if len(video_ids) != 1:
        return None
    video_id = video_ids[0]
    # In a unit test, we want to override the view count of a video
    if video_id in video_view_overrides:
        views = video_view_overrides[video_id]
    else:
        try:
            func = dispatcher[site]
            views = func(video_id)
        except Exception as e:
            return None
    if views <= 0:
        return None
    return ViewQueryResult(old_views=original_views,
                           new_views=views,
                           old_string=original,
                           new_string=original.replace(match.group("views"), format_views(views)))


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


def generate_new_views(links: VideoLinks, num_links: int, views: str) -> str:
    matches = list(re.finditer(r"( |^)(?P<views>[\d,]+)\+? \((?P<site>NN|YT|BB)\)",
                               views))
    # If only one site has a video on it, then we may not see the usual (NN/YT/BB) cue in the play count.
    # Thus, we perform some checks to see if this is the case. If so, we enter permissive mode and relax
    # the NN/YT/BB checking to only look for numbers.
    # There are 3 conditions for permissive mode:
    # 1. Only 1 link is present
    # 2. No substitution is made in the previous pass
    # 3. Only 1 number is present
    permissive = False
    if num_links == 1 and len(matches) == 0 and len(re.findall(r"[\d,]+", views)) == 1:
        matches = list(re.finditer(r"(\s|^)(?P<views>[\d,]+)\+?(\s|$)",
                                   views))
        assert len(matches) == 1
        permissive = True

    view_query_results: list[ViewQueryResult] = []
    should_update = False
    for match in matches:
        result = process_views(match, links, permissive=permissive)
        if result is None:
            continue
        if should_update_views(result.old_views, result.new_views):
            should_update = True
        view_query_results.append(result)

    if not should_update:
        return views

    for result in view_query_results:
        views = views.replace(result.old_string, result.new_string)
    return views


def process_template(template: Template) -> bool:
    view_arg = template.get_arg("#views")
    link_arg = template.get_arg("link")
    if not view_arg or not link_arg:
        return False
    views = view_arg.value
    links, num_links = parse_links(link_arg.value)

    new_views = generate_new_views(links, num_links, views)

    if views == new_views:
        return False

    view_arg.value = new_views
    return True


def main():
    gen = GeneratorFactory()
    gen.handle_args(['-start:-Geminate-', "-ns:0"])
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
