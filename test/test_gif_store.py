# MIT License
#
# Copyright (c) 2018 Matthew Bedder (matthew@bedder.co.uk)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Tests for the ``GifStore`` class.
"""

import unittest

from gif_bot.gif_store import GifStore


class TestGifStore(unittest.TestCase):
    def setUp(self):
        self.adjectives = ["TestAdjective1", "TestAdjective2"]
        self.data = "url_a,tag_a1,tag_a2\nurl_b,tag_b1,tag_b2\nurl_bb,tag_b1,tag_b3\n"
        self.store = GifStore(adjectives=self.adjectives, manifest_data=self.data)

    def test_add_new_gif(self):
        self.assertEqual(len(self.store.elements), 3)
        self.assertEqual(len(self.store.tags), 5)

        self.store.add_gif("url_c", {"tag_c1"})

        self.assertEqual(len(self.store.elements), 4)
        self.assertEqual(len(self.store.tags), 6)
        self.assertEqual(self.store.tags["tag_c1"], 1)

    def test_add_existing_gif(self):
        self.assertEqual(len(self.store.elements), 3)
        self.assertEqual(len(self.store.tags), 5)

        self.store.add_gif("url_a", {"tag_a1", "tag_a3"})

        self.assertEqual(len(self.store.elements), 3)
        self.assertEqual(len(self.store.tags), 6)
        self.assertEqual(self.store.tags["tag_a1"], 1)
        self.assertEqual(self.store.tags["tag_a3"], 1)

    def test_remove_gif(self):
        self.assertEqual(len(self.store.elements), 3)
        self.assertEqual(len(self.store.tags), 5)
        self.assertEqual(self.store.tags["tag_b1"], 2)
        self.assertEqual(self.store.tags["tag_b2"], 1)
        self.assertEqual(self.store.tags["tag_b3"], 1)

        self.store.remove_gif("url_bb")

        self.assertEqual(len(self.store.elements), 2)
        self.assertEqual(len(self.store.tags), 4)
        self.assertEqual(self.store.tags["tag_b1"], 1)
        self.assertEqual(self.store.tags["tag_b2"], 1)
        self.assertNotIn("tag_b3", self.store.tags)

    def test_get_tags(self):
        self.assertSetEqual(self.store.get_tags(), {"tag_a1", "tag_a2",
                                                    "tag_b1", "tag_b2", "tag_b3"})

    def test_get_count(self):
        self.assertEqual(self.store.get_count("tag_b1"), 2)
        self.assertEqual(self.store.get_count("tag_b2"), 1)
        self.assertEqual(self.store.get_count("tag_b4"), 0)

    def test_get_gif_success(self):
        self.assertEqual(self.store.get_gif("tag_a1"), "url_a")

    def test_get_gif_failure(self):
        self.assertIsNone(self.store.get_gif("tag_d1"))
