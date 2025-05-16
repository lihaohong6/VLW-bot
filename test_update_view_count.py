from unittest import TestCase

from update_view_count import parse_links, VideoSite, format_views, generate_new_views, override_video_view_count, \
    should_update_views


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

    def test_format_views(self):
        self.assertEqual("500", format_views(599))
        self.assertEqual("1,400", format_views(1490))
        self.assertEqual("123,000", format_views(123456))

    def test_generate_new_views_permissive_mode(self):
        vid = "a"
        old_views = 1230
        new_views = 4560
        self.assertTrue(should_update_views(old_views, new_views))
        override_video_view_count(vid, new_views)
        actual = generate_new_views({
            VideoSite.NicoNico: [vid],
        }, 1, str(old_views))
        expected = format_views(new_views)
        self.assertEqual(expected, actual)

    def test_generate_new_views_permissive_mode_deny(self):
        vid = "a"
        override_video_view_count(vid, 0)
        views = "123 456"
        actual = generate_new_views({
            VideoSite.NicoNico: [vid],
        }, 1, views)
        self.assertEqual(views, actual)

    def test_generate_new_views_youtube_and_niconico(self):
        """
        If NN needs to be updated but YT does not, we still want to update both since we're making an edit anyway.
        """
        yt_id = 'v1'
        yt_old = 19000
        yt_new = 20000
        nn_id = 'v2'
        nn_old = 30001
        nn_new = 58229
        self.assertFalse(should_update_views(yt_old, yt_new))
        self.assertTrue(should_update_views(nn_old, nn_new))
        override_video_view_count(yt_id, yt_new)
        override_video_view_count(nn_id, nn_new)
        expected = f"{format_views(yt_new)} (YT) {format_views(nn_new)} (NN)"
        views = f"{yt_old} (YT) {nn_old} (NN)"
        actual = generate_new_views({
            VideoSite.YouTube: [yt_id],
            VideoSite.NicoNico: [nn_id],
        }, 2, views)
        self.assertEqual(expected, actual)

    def test_generate_new_views_youtube_and_niconico_no_update(self):
        """
        If NN needs to be updated but YT does not, we still want to update both since we're making an edit anyway.
        """
        yt_id = 'v1'
        yt_old = 19000
        yt_new = 20000
        nn_id = 'v2'
        nn_old = 30001
        nn_new = 32000
        self.assertFalse(should_update_views(yt_old, yt_new))
        self.assertFalse(should_update_views(nn_old, nn_new))
        override_video_view_count(yt_id, yt_new)
        override_video_view_count(nn_id, nn_new)
        views = f"{yt_old} (YT) {nn_old} (NN)"
        actual = generate_new_views({
            VideoSite.YouTube: [yt_id],
            VideoSite.NicoNico: [nn_id],
        }, 2, views)
        self.assertEqual(views, actual)
