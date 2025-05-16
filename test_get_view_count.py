from unittest import TestCase

from get_view_count import get_yt_views, get_nn_views_old, get_nn_views, get_bb_views


class Test(TestCase):

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
        view_count = get_yt_views("KCVIFoBBVv4")
        self.assertTrue(600 <= view_count <= 700)

    def test_get_bb_views(self):
        for video_id in ['BV1Gu4y1B7b1']:
            view_count = get_bb_views(video_id)
            self.assertTrue(120000 <= view_count <= 130000)