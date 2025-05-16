from unittest import TestCase

from view_count import parse_links, VideoSite, format_views, get_nn_views, get_nn_views_old, get_yt_views


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

    def test_get_nn_views(self):
        for video_id in ['sm9714351', "sm35758524", "sm26077316"]:
            old_view_count = get_nn_views_old(video_id)
            new_view_count = get_nn_views(video_id)
            diff = new_view_count - old_view_count
            # Might be a small difference due to request timing
            self.assertTrue(diff <= 2)

    def test_get_yt_views(self):
        for video_id in ['zm4hQgHIgfk']:
            view_count = get_yt_views(video_id)
            # This is hard-coded. May fail if the video gets more views.
            self.assertTrue(1300 <= view_count <= 1400)

    def test_format_views(self):
        self.assertEqual("500", format_views(599))
        self.assertEqual("1,400", format_views(1490))
        self.assertEqual("123,000", format_views(123456))
