from unittest import TestCase

from view_count import parse_links, VideoSite


class Test(TestCase):
    def test_parse_links(self):
        links, count = parse_links(
            "{{#|https://www.nicovideo.jp/watch/sm42272597}} "
            "{{#|https://www.youtube.com/watch?v=S9EpjW70_fw}}")
        self.assertEqual(count, 2)
        self.assertEqual(
            links,
            {
                VideoSite.NicoNico: ["sm42272597"],
                VideoSite.YouTube: ["S9EpjW70_fw"],
            })
