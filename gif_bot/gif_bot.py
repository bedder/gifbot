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
Implementation of the main ``GifBot`` class
"""

import random
import re
from logging import Logger, Formatter, INFO, getLogger
from logging.handlers import RotatingFileHandler
from sys import exc_info
from time import sleep
from typing import List, Text, Any, Tuple

from configobj import ConfigObj
from slackclient import SlackClient

from gif_bot.gif_store import GifStore
from gif_bot.utils import get_config_list

LOG_FORMAT = "%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s"
LOG_SIZE_MB = 2

STD_DELAY = 0.5
ERR_DELAY = 5.
MAX_DELAY = 3600.


# pylint: disable=too-many-instance-attributes
class GifBot:
    """
    The main implementation of the GifBot
    """

    class BotConfigError(RuntimeError):
        """ Errors relating to how the bot is configured """
        pass

    class SlackApiError(RuntimeError):
        """ Errors relating to interactions with the Slack API """
        pass

    def __init__(self, config_filename: Text, log_filename: Text) -> None:
        self.log = self._init_log(log_filename)

        # Attempt to read settings from the config file
        try:
            config = ConfigObj(config_filename)
            self.bot_name = config["bot_name"]
            self.bot_id = None
            self.owner_name = config["bot_owner"]
            self.owner_id = None
            self.manifest_loc = config["manifest_loc"]
            self.api_token = config["slack_token"]

            # Save messaging parameters, and put into lists if required.
            self.nouns = get_config_list(config, "nouns")
            self.greetings = get_config_list(config, "greetings")
            self.triggers = get_config_list(config, "triggers")
            self.reactions = get_config_list(config, "reactions")
            self.reactions = get_config_list(config, "reactions")
            self.adjectives = get_config_list(config, "adjectives")
        except KeyError as err:
            self.log.error("The required key '%s' was not found in the config file (%s).",
                           err.args[0], log_filename)
            raise self.BotConfigError("Key not found: {key}".format(key=err.args[0]))

        # Initialise the store of GIFs
        try:
            self.store = GifStore(adjectives=self.adjectives,
                                  manifest_data=open(self.manifest_loc).read())
        except Exception as _:
            raise self.BotConfigError("Unable to load GIF manifest.")

        # Initialise the Slack client
        self.log.info("Initialising the Slack client...")
        self.client = SlackClient(self.api_token)
        self.log.info("Slack client initialised")

        # Get the bot and owner IDs
        self.bot_id, self.owner_id = self._get_user_id((self.bot_name, self.owner_name))

        self.log.info("Bot initialised with [ID:{bot_id}] and [ownerID:{owner_id}]"
                      .format(bot_id=self.bot_id, owner_id=self.owner_id))

    @staticmethod
    def _init_log(log_filename: Text) -> Logger:
        """ Initialise a logger """
        # Initialise the logger
        log_formatter = Formatter(LOG_FORMAT)

        log_handler = RotatingFileHandler(log_filename, mode="a",
                                          maxBytes=LOG_SIZE_MB * 1024 * 1024,
                                          backupCount=2, encoding=None, delay=False)
        log_handler.setFormatter(log_formatter)
        log_handler.setLevel(INFO)

        log = getLogger('root')
        log.setLevel(INFO)
        log.addHandler(log_handler)

        return log

    def _get_user_id(self, names: Tuple[Text, ...]) -> Tuple[Text, ...]:
        """ Get the Slack API ID for a set of users """
        api_call = self.client.api_call("users.list")

        if not api_call.get("ok"):
            self.log.error("Error in API call to users.list")
            raise self.SlackApiError("Unable to call the Slack command 'users.list'.")

        def extract_name(user_name: Text) -> Text:
            """ Extract the specific user's ID from the API call results """
            for user in api_call["members"]:
                if "name" in user and user["name"] == user_name:
                    return user["id"]
            raise self.SlackApiError("Unable to find a user with name {name}"
                                     .format(name=user_name))

        return tuple(extract_name(name) for name in names)

    ################################################################################################
    # Standard entry point
    ################################################################################################
    def run(self) -> None:
        """
        Runs the bot. If there's an error connecting to the Slack service then we pause before
        attempting to connect again to prevent network thrashing.
        """
        delay = ERR_DELAY

        while True:
            # Try to connect to the client, and loop through messages
            try:
                if self.client.rtm_connect():
                    self.log.info("Bot connected to Slack RTM API")
                    while True:
                        rtm_messages = self.client.rtm_read()
                        self.handle(rtm_messages)
                        sleep(STD_DELAY)
                else:
                    self.log.error("Bot is unable to connect to the Slack service")
            except:  # pylint: disable=bare-except
                self.log.error("Unknown exception encountered.")
                self.log.error(str(exc_info()[0]))

            # If we cannot connect or we get disconnected, wait for a while before retrying
            if delay < MAX_DELAY:
                self.log.info("Trying again in %s seconds", delay)
                sleep(delay)
                delay *= 1.1
            else:
                self.log.error("Maximum number of exceptions caught. Exiting...")
                return

    ################################################################################################
    # Message handlers
    ################################################################################################
    def handle(self, rtm_messages: List[Any]) -> None:
        """
        Handles a set of Slack RTM messages received from the client service.
        :param rtm_messages: Messages read from SlackClient::rtm_read
        """
        if not rtm_messages:
            return

        for message_obj in rtm_messages:
            if message_obj["type"] == "message":
                self.handle_message(message_obj)

    #pylint: disable=inconsistent-return-statements
    def handle_message(self, message_obj) -> None:
        """
        Handles an individual Slack RTM message read from the client service
        :param message_obj: An individual message extracted from the output of SlackClient::rtm_read
        """
        # It isn't a real message, so abort
        if "user" not in message_obj:
            return

        # Prevent self triggers
        if message_obj["user"] == self.bot_id:
            return

        # Handle DMs from the bot owner
        if message_obj["user"] == self.owner_id and message_obj["channel"][0] == "D":
            return self.handle_command(message_obj["text"],
                                       message_obj["channel"],
                                       message_obj["ts"])

        # Handle messages directed at the bot
        if self.is_mention(message_obj["text"]):
            return self.handle_mention(message_obj["text"],
                                       message_obj["channel"],
                                       message_obj["ts"])

        # Handle messages containing trigger words
        if self.is_trigger(message_obj["text"]):
            return self.handle_trigger(message_obj["channel"], message_obj["ts"])

    # pylint: disable=inconsistent-return-statements,too-many-return-statements
    def handle_command(self, message: Text, channel: Text, time_stamp: Text) -> None:
        """
        Handles a direct command given from the bot owner in a direct message
        :param message: The text of the command message
        :param channel: The channel ID where the message came from
        :param time_stamp: The timestamp of the message
        """
        tokens = re.split(r"\s+", message)

        if not tokens:
            return

        if tokens[0] == "add" and len(tokens) > 1:
            # Add a GIF into the store
            self.store.add_gif(tokens[1], set(tokens[2:]))
            return self.post_message(text="Adding {gif}\nType `save` to save this to the manifest."
                                     .format(gif=tokens[1]),
                                     channel=channel)

        if tokens[0] == "remove" and len(tokens) == 2:
            # Remove a GIF from the store
            self.store.remove_gif(tokens[1])
            return self.post_message(text="Removing " + tokens[1], channel=channel)

        if tokens[0] == "status":
            # Gets information about the GIF store
            return self.post_message(text=self.store.get_info(max_tags=10), channel=channel)

        if tokens[0] == "compare" and len(tokens) >= 2:
            # Compare the counts of multiple different tag types
            return self.handle_compare(channel, tokens[1:])

        if tokens[0] == "request":
            # Handle a request for a particular GIF type
            if len(tokens) == 1:
                return self.handle_trigger(channel=channel, time_stamp=time_stamp)
            return self.handle_trigger(channel=channel, time_stamp=time_stamp, gif_type=tokens[1])

        if tokens[0] == "reload":
            # Reload the store from the file
            self.store = GifStore(adjectives=self.adjectives,
                                  manifest_data=open(self.manifest_loc).read())
            return self.post_message(text="Manifest reloaded", channel=channel)

        if tokens[0] == "save":
            # Save the store to the file
            self.store.save_manifest(self.manifest_loc)
            return self.post_message(text="Manifest saved", channel=channel)

        # We've not had a valid trigger, so post a default message
        self.post_message(text="Sorry, I don't understand that command.\n"
                               "Supported commands:\n"
                               "  `add url token1 token2...`\n"
                               "  `remove url`\n"
                               "  `status`\n"
                               "  `request cat`\n"
                               "  `compare cat dog alpaca`\n"
                               "  `reload`\n"
                               "  `save`",
                          channel=channel)

    # pylint: disable=inconsistent-return-statements,too-many-return-statements
    def handle_mention(self, message: Text, channel: Text, time_stamp: Text) -> None:
        """
        Handles a mention or direct message to the bot.
        :param message: The text of the command message
        :param channel: The channel ID where the message came from
        :param time_stamp: The timestamp of the message
        """
        tokens = re.split(r"\s+", message.lower())

        if len(tokens) < 2:
            return

        if tokens[1] == "help":
            message = "Hi! I know the following commands:\n" \
                   "  `help` : Display self message\n" \
                   "  `about` : Display info about me\n" \
                   "  `status` : Give a status report of the bot\n" \
                   "  `request cat` : Request a cat GIF\n" \
                   "  `compare cat dog` : Compare the number of GIFs I know about"
            return self.post_message(text=message, channel=channel)

        if tokens[1] == "about":
            message = "I'm a wholesome bot created by *Matthew Bedder*. You can " \
                   "read my source-code at `https://github.com/bedder/gifbot`."
            return self.post_message(text=message, channel=channel)

        if tokens[1] == "status":
            return self.post_message(text=self.store.get_info(max_tags=10), channel=channel)

        if tokens[1] == "request":
            if len(tokens) == 2:
                return self.handle_trigger(channel=channel, time_stamp=time_stamp)
            return self.handle_trigger(channel=channel, time_stamp=time_stamp, gif_type=tokens[2])

        if tokens[1] == "compare" and len(tokens) > 2:
            return self.handle_compare(channel, tokens[2:])

        self.post_message(text="Sorry, I don't understand that!\n(HINT: try `@{} help` to see "
                               "a list of suitable commands)".format(self.bot_name),
                          channel=channel)

    def handle_trigger(self, channel: Text, time_stamp: Text, gif_type: Text = "all") -> None:
        """
        Handles an message containing a trigger message
        :param channel: The channel ID where the message came from
        :param time_stamp: The timestamp of the message
        :param gif_type: The type of GIF that we should return
        """
        success = self.post_gif(channel, gif_type)
        self.post_reaction(channel, time_stamp,
                           random.choice(self.reactions) if success else "broken_heart")

    def handle_compare(self, channel: Text, tokens: List[Text]) -> None:
        """
        Compare the GIF counts for multiple GIF types
        :param channel: The channel ID where the message came from
        :param tokens: The GIF types we want to compare
        """
        best_count = 0
        best_tag = "neither of them!"
        msg = "Current GIF counts:\n```"

        for token in tokens:
            count = self.store.get_count(token)
            msg += "  {token} : {count}\n".format(token=token, count=count)

            if count == 0:
                continue
            elif count == best_count:
                if "both " in best_tag:
                    best_tag += " and {token}".format(token=token)
                else:
                    best_tag = "both {best} and {token}".format(best=best_tag, token=token)
            elif count > best_count:
                best_count = count
                best_tag = token

        msg += "```\nThe winner is.... {best}!".format(best=best_tag)

        self.post_message(text=msg, channel=channel)

    ################################################################################################
    # Message type tests
    ################################################################################################
    def is_mention(self, message: Text) -> bool:
        """
        Checks to see if the message is mentioning the bot
        :param message: The text of the command message
        :return: Whether the message mentions the bot
        """
        return "@" + self.bot_name in message.split(" ")[0]

    def is_trigger(self, message: Text) -> bool:
        """
        Checks to see if the message contains a trigger word
        :param message: The text of the command message
        :return: Whether the message is a trigger
        """
        for trigger in self.triggers:
            if trigger.lower() in message.lower():
                return True
        return False

    ################################################################################################
    # Slack API wrapper functions
    ################################################################################################
    def post_message(self, text: Text, channel: Text) -> None:
        """
        Helper function to post a message into a channel
        :param text: The text we want to post
        :param channel: The channel ID where the message came from
        """
        try:
            self.client.api_call("chat.postMessage", channel=channel, text=text, as_user=True)
        except Exception as _:
            raise self.SlackApiError("Unable to call the Slack command 'chat.postMessage'.")

    def post_gif(self, channel: Text, gif_type: Text = "all") -> bool:
        """
        Attempts to retrieve a GIF from the store, and post it into the desired channel
        :param channel: The channel ID where the message came from
        :param gif_type: The GIF type we want to post
        :return: Whether we were able to successfully find and post the GIF
        """
        self.log.info("Retrieving gif of type %s", gif_type)
        url = self.store.get_gif(gif_type)

        if url:
            text = random.choice(self.greetings).format(random.choice(self.nouns)) + " " + url
            self.post_message(text=text, channel=channel)
            return True

        self.post_message("Sorry, I have no gifs of type `{}` :weary:".format(gif_type),
                          channel=channel)
        return False

    def post_reaction(self, channel: Text, time_stamp: Text, reaction_str: Text) -> None:
        """
        Post a reaction in response to a particular message
        :param channel: The channel ID where the message came from
        :param time_stamp: The timestamp of the message we want to respond to
        :param reaction_str: The string defining the response type (e.g. `:heart:`)
        """
        self.log.info("Adding reaction [%s] to message [ts:%s]", reaction_str, time_stamp)
        try:
            self.client.api_call("reactions.add", name=reaction_str, channel=channel,
                                 timestamp=time_stamp)

        except Exception as _:
            raise self.SlackApiError("Unable to call the Slack command 'reactions.add'.")
