from configobj import ConfigObj
from slackclient import SlackClient
from gif_bot.GifStore import GifStore
import time
import random
import re

def asList(item):
	if isinstance(item, list):
		return item
	return [item]

class GifBot:
	def __init__(self, filename):
		config          = ConfigObj(filename)
		self.NAME       = config["bot_name"]
		self.OWNER      = config["bot_owner"]
		self.API_TOKEN  = config["api_token"]
		self.MANIFEST   = config["manifest_loc"]
		# Save messaging parameters, and put into lists if required.
		self.nouns      = asList(config["nouns"])
		self.greetings  = asList(config["greetings"])
		self.triggers   = asList(config["triggers"])
		self.reactions  = asList(config["reactions"])
		# Initialise the store of GIFs
		self.store = GifStore(open(self.MANIFEST).read())
		# Initialise the Slack client
		self.client = SlackClient(self.API_TOKEN)
		# Find out the bot's ID
		api_call = self.client.api_call("users.list")
		if api_call.get("ok"):
			set_bot_id = False
			set_owner_id = False
			for user in api_call["members"]:
				if "name" in user and user["name"] == self.NAME:
					self.BOT_ID = user["id"]
					set_bot_id = True
				if "name" in user and user["name"] == self.OWNER:
					self.OWNER_ID = user["id"]
					set_owner_id = True
			if not set_bot_id:
				self.log("error", "Unable to find user \"" + self.NAME + "\" in the Slack channel")
				raise Exception()
			if not set_owner_id:
				self.log("error", "Unable to find user \"" + self.OWNER + "\" in the Slack channel")
				raise Exception()
		else:
			self.log("error", "Error in API call to users.list")
			raise Exception()
		self.log("status", "Bot initialised with [ID:{}] and [ownerID:{}]".format(self.BOT_ID, self.OWNER_ID))

	############################################################################
	# Standard entry point
	############################################################################
	def run(self):
		STD_DELAY = 0.5
		ERR_DELAY = 5
		MAX_DELAY = 3600
		while True:
			try:
				if self.client.rtm_connect():
					self.log("staus", "Bot connected to Slack RTM API")
					while True:
						rtm_messages = self.client.rtm_read()
						self.handle(rtm_messages)
						time.sleep(STD_DELAY)
				else:
					self.log("error", "Bot is unable to connect to the Slack service")
			except:
				self.log("error", "Unknown exception encountered.")
			if (ERR_DELAY < MAX_DELAY):
				self.log("status", "Trying again in " + str(ERR_DELAY) + " seconds...")
				time.sleep(ERR_DELAY)
				ERR_DELAY *= 2
			else:
				self.log("error", "Maximum number of exceptions caught. Exiting...")
				return
	
	############################################################################
	# Message type handlers
	############################################################################
	def handle(self, rtm_messages):
		if rtm_messages and len(rtm_messages) > 0:
			for message in rtm_messages:
				if message["type"] == "message":
					self.handle_message(message)
	
	def handle_message(self, message):
		if "user" not in message:
			return
		if message["user"] == self.BOT_ID:
			return
		elif message["user"] == self.OWNER_ID and message["channel"][0] == "D":
			self.handle_command(message["text"], message["channel"], message["ts"])
		elif self.is_mention(message["text"]):
			self.handle_mention(message["text"], message["channel"], message["ts"])
		elif self.is_trigger(message["text"]):
			self.handle_trigger(message["channel"], message["ts"])
	
	def handle_command(self, text, channel, ts):
		tokens = re.split(r"\s+", text)
		if len(tokens)==0:
			return
		if tokens[0] == "add" and len(tokens) > 1:
			self.store.add_gif(tokens[1][1:-1], tokens[2:])
			self.post_message(text="Adding {}\nType `save` to save this to the manifest.".format(tokens[1]), channel=channel)
		elif tokens[0] == "remove" and len(tokens) == 2:
			self.store.remove_gif(tokens[1])
			self.post_message(text="Removing " + tokens[1], channel=channel)
		elif tokens[0] == "status":
			self.post_message(text=self.store.get_info(max=10), channel=channel)
		elif tokens[0] == "compare" and len(tokens) >= 2:
			self.handle_compare(channel, tokens[1:])
		elif tokens[0] == "request":
			if len(tokens) == 1:
				self.handle_trigger(channel=channel, ts=ts)
			else:
				self.handle_trigger(channel=channel, ts=ts, type=tokens[1])
		elif tokens[0] == "reload":
			self.store.__init__(open(self.MANIFEST).read())
			self.post_message(text="Manifest reloaded", channel=channel)
		elif tokens[0] == "save":
			self.store.save_manifest(self.MANIFEST)
			self.post_message(text="Manifest saved", channel=channel)
		else:
			self.post_message(text="Sorry, I don't understand that command.\n" \
			                       "Supported commands:\n" \
			                       "  `add url token1 token2...`\n" \
			                       "  `remove url`\n" \
			                       "  `status`\n" \
			                       "  `request cat`\n" \
			                       "  `compare cat dog alpaca`\n" \
			                       "  `reload`\n" \
			                       "  `save`", channel=channel)
	
	def handle_mention(self, text, channel, ts):
		tokens = re.split(r"\s+", text.lower())
		if len(tokens) < 2:
			return
		if tokens[1] == "help":
			text="Hi! I know the following commands:\n" \
			     "  `help` : Display self message\n" \
			     "  `about` : Display info about me\n" \
			     "  `status` : Give a status report of the bot\n" \
			     "  `request cat` : Request a cat GIF\n" \
			     "  `compare cat dog` : Compare the number of GIFs I know about"
			self.post_message(text=text, channel=channel)
		elif tokens[1] == "about":
			text = "I'm a wholesome bot created by *Matthew Bedder*. You can " \
			       "read my source-code at `https://github.com/bedder/gifbot`."
			self.post_message(text=text, channel=channel)
		elif tokens[1] == "status":
			self.post_message(text=self.store.get_info(max=10), channel=channel)
		elif tokens[1] == "request":
			if len(tokens) == 2:
				self.handle_trigger(channel=channel, ts=ts)
			else:
				self.handle_trigger(channel=channel, ts=ts, type=tokens[2])
		elif tokens[1] == "compare" and len(tokens)>2:
			self.handle_compare(channel, tokens[2:])
		else:
			self.post_message(text="Sorry, I don't understand that!\n" \
			                       "(HINT: try `@" + self.NAME + " help` to see a list of suitable commands)",
			                  channel=channel)
	
	def handle_trigger(self, channel, ts, type="all"):
			self.post_reaction(channel, ts, random.choice(self.reactions))
			self.post_gif(channel, type)

	def handle_compare(self, channel, tokens):
		best_count = 0
		best_tag = "neither of them!"
		msg = "Current GIF counts:\n```"
		for t in tokens:
			count = self.store.get_count(t)
			msg += "  " + t + " : " + str(count) + "\n"
			if count == 0:
				continue
			elif count == best_count:
				if "both " in best_tag:
					best_tag += " and " + t
				else:
					best_tag = "both " + best_tag + " and " + t
			elif count > best_count:
				best_count = count
				best_tag = t
		msg += "```\nThe winner is.... " + best_tag + "!"
		self.post_message(text=msg, channel=channel)

	############################################################################
	# Message type tests
	############################################################################
	def is_mention(self, text):
		return "@" + self.BOT_ID in text.split(" ")[0]
	
	def is_trigger(self, text):
		for t in self.triggers:
			if t.lower() in text.lower():
				return True
		return False

	############################################################################
	# Slack API wrapper functions
	############################################################################
	def post_message(self, text, channel):
		self.client.api_call("chat.postMessage", channel=channel, text=text, as_user=True)

	def post_gif(self, channel, type="all"):
		self.log("status", "Retrieving gif of type " + type)
		url = self.store.get_gif(type)
		if url:
			text = random.choice(self.greetings).format(random.choice(self.nouns)) + " " + url
			self.post_message(text=text, channel=channel)
			return
		self.post_message("Sorry, I have no gifs of type `" + type + "` :weary:", channel=channel)

	def post_reaction(self, channel, ts, emoji):
		self.log("status", "Adding reaction [{}] to message [ts:{}]".format(emoji, ts))
		response = self.client.api_call("reactions.add", name=emoji, channel=channel, timestamp=ts)

	############################################################################
	# Helper functions
	############################################################################
	def log(self, type, message):
		msg = "{} {} {}".format(time.strftime("%Y%m%d %H:%M:%S", time.gmtime()),
		                        ("[" + type.upper() + "]").ljust(8),
		                        message)
		print(msg)
