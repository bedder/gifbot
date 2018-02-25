
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
Tests for the ``GifBot`` class.
"""

import unittest
from unittest.mock import patch, MagicMock

from gif_bot.gif_bot import GifBot

api_collector = MagicMock()


def mock_api_call(command, *args, **kwargs):
    if command == "users.list":
        return {
            "ok": True,
            "members": [
                {"name": "test_bot_name", "id": "test_bot_id"},
                {"name": "test_owner_name", "id": "test_owner_id"}
            ]
        }
    else:
        api_collector(command, *args, **kwargs)


def mock_client(_):
    return MagicMock(api_call=mock_api_call)


def Any(cls):
    class Any(cls):
        def __eq__(self, other):
            return True
    return Any()


@patch("gif_bot.gif_bot.SlackClient", mock_client)
@patch("gif_bot.gif_bot.getLogger")
@patch("gif_bot.gif_bot.Formatter")
@patch("gif_bot.gif_bot.Logger")
@patch("gif_bot.gif_bot.RotatingFileHandler")
class TestGifBot(unittest.TestCase):
    def setUp(self):
        api_collector.reset_mock()

    def test_is_mention(self, *args):
        """ The bot should be able to identify direct mentions """

        bot = GifBot("test.config", MagicMock())
        self.assertTrue(bot.is_mention("@test_bot_name"))
        self.assertTrue(bot.is_mention("@test_bot_name help"))
        self.assertFalse(bot.is_mention("Something @test_bot_name"))

    def test_is_trigger(self, *args):
        """ The bot should be able to identify trigger words being used in messages """

        bot = GifBot("test.config", MagicMock())
        self.assertTrue(bot.is_trigger("test_trigger blah"))
        self.assertTrue(bot.is_trigger("blah test_trigger"))
        self.assertFalse(bot.is_trigger("something else"))

    def test_not_trigger_non_message(self, *args):
        """ The bot should ignore non-messages """

        bot = GifBot("test.config", MagicMock())
        bot.handle_message({
            "channel": "test_channel",
            "ts": "test_ts"
        })
        api_collector.assert_not_called()

    def test_not_trigger_self(self, *args):
        """ The bot shouldn't be able to trigger itself """

        bot = GifBot("test.config", MagicMock())
        bot.handle_message({
            "user": "test_bot_id",
            "text": "Something something test_trigger",
            "channel": "test_channel",
            "ts": "test_ts"
        })
        api_collector.assert_not_called()

    def test_handle_trigger_message(self, *args):
        """ The bot should trigger on messages from users containing a trigger word """

        bot = GifBot("test.config", MagicMock())
        bot.handle_message({
            "user": "test_user_id",
            "text": "Something something test_trigger",
            "channel": "test_channel",
            "ts": "test_ts"
        })
        api_collector.assert_any_call("chat.postMessage", text=Any(str),
                                      channel="test_channel", as_user=True)
        api_collector.assert_any_call("reactions.add", name="test_reaction",
                                      channel="test_channel", timestamp="test_ts")

    def test_handle_request_success(self, *args):
        """ The bot should post a gif and a happy reaction when they can fulfill a request """

        bot = GifBot("test.config", MagicMock())
        bot.handle_message({
            "user": "test_user_id",
            "text": "@test_bot_name request tag_a1",
            "channel": "test_channel",
            "ts": "test_ts"
        })
        api_collector.assert_any_call("chat.postMessage", text=Any(str),
                                      channel="test_channel", as_user=True)
        api_collector.assert_any_call("reactions.add", name="test_reaction",
                                      channel="test_channel", timestamp="test_ts")

    def test_handle_request_failure(self, *args):
        """ The bot should send a message and react with :brokenheart: when it cannot fulfill a
        request """

        bot = GifBot("test.config", MagicMock())
        bot.handle_message({
            "user": "test_user_id",
            "text": "@test_bot_name request invalid_tag",
            "channel": "test_channel",
            "ts": "test_ts"
        })
        api_collector.assert_any_call("chat.postMessage", text=Any(str),
                                      channel="test_channel", as_user=True)
        api_collector.assert_any_call("reactions.add", name="broken_heart",
                                      channel="test_channel", timestamp="test_ts")

    def test_admin(self, *args):
        """ Test that basic admin commands work """
        bot = GifBot("test.config", MagicMock())

        self.assertNotIn("tag", bot.store.tags)
        self.assertEqual(len(bot.store.elements), 2)

        bot.handle_message({
            "user": "test_owner_id",
            "text": "add url tag",
            "channel": "Dtest_channel",
            "ts": "test_ts"
        })

        self.assertIn("tag", bot.store.tags)
        self.assertEqual(len(bot.store.elements), 3)

        bot.handle_message({
            "user": "test_owner_id",
            "text": "remove url",
            "channel": "Dtest_channel",
            "ts": "test_ts"
        })

        self.assertNotIn("tag", bot.store.tags)
        self.assertEqual(len(bot.store.elements), 2)

    def test_admin_access(self, *args):
        """ Test that basic admin commands work only for the owner """
        bot = GifBot("test.config", MagicMock())

        self.assertNotIn("tag", bot.store.tags)
        self.assertEqual(len(bot.store.elements), 2)

        bot.handle_message({
            "user": "test_user_id",
            "text": "add url tag",
            "channel": "Dtest_channel",
            "ts": "test_ts"
        })

        self.assertNotIn("tag", bot.store.tags)
        self.assertEqual(len(bot.store.elements), 2)
