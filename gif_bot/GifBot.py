from configobj import ConfigObj
from slackclient import SlackClient
from gif_bot.GifStore import GifStore
import time
import random
import re

class GifBot:
	def __init__(self, filename):
		config          = ConfigObj(filename)
		self.NAME       = config["bot_name"]
		self.OWNER      = config["bot_owner"]
		self.API_TOKEN  = config["api_token"]
		self.MANIFEST   = config["manifest_loc"]
		self.nouns      = config["nouns"]
		self.greetings  = config["greetings"]
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
		
	def handle(self, rtm_messages):
		if rtm_messages and len(rtm_messages) > 0:
			for message in rtm_messages:
				# self.log("input", "Received " + message["type"])
				if message["type"] == "message":
					self.handle_message(message)
	
	def handle_message(self, message):
		if "user" not in message:
			return
		if message["user"] == self.BOT_ID:
			return
		elif message["user"] == self.OWNER_ID and message["channel"][0] == "D":
			self.handle_command(message["text"], message["channel"])
		elif self.is_mention(message["text"]):
			self.handle_mention(message["text"], message["channel"])
		elif self.gif_trigger(message["text"]):
			self.post_reaction(message["channel"], message["ts"], "heart")
			self.post_gif(message["channel"])
	
	def is_mention(self, text):
		return "@" + self.BOT_ID in text.split(" ")[0]
	
	def post_message(self, text, channel):
		self.client.api_call("chat.postMessage", channel=channel, text=text, as_user=True)
	
	def handle_command(self, text, channel):
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
			self.compare_counts(channel, tokens[1:])
		elif tokens[0] == "request":
			if len(tokens) > 1:
				self.post_gif(channel=channel, type=tokens[1])
			else:
				self.post_gif(channel=channel)
		elif tokens[0] == "reload":
			self.store.__init__(open(self.MANIFEST).read())
			self.post_message(text="Done!", channel=channel)
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
	
	def handle_mention(self, text, channel):
		tokens = re.split(r"\s+", text.lower())
		if len(tokens) == 2 and tokens[1] == "help":
			text="Known commands:\n" \
			     "`help` : Display self message\n" \
			     "`status` : Give a status report of the bot\n" \
			     "`request cat` : Request a cat GIF\n" \
			     "`compare cat dog` : Compare the number of GIFs I know about"
			self.post_message(text=text, channel=channel)
		elif len(tokens) == 2 and tokens[1] == "status":
			self.post_message(text=self.store.get_info(max=10), channel=channel)
		elif len(tokens) == 2 and tokens[1] == "request":
			self.post_gif(channel)
		elif len(tokens) == 3 and tokens[1] == "request":
			self.post_gif(channel, tokens[2])
		elif len(tokens) >= 3 and tokens[1] == "compare":
			self.compare_counts(channel, tokens[2:])
		else:
			self.post_message(text="Sorry, I don't understand that!\n" \
			                       "(HINT: try `@" + self.NAME + " help` to see a list of suitable commands)",
			                  channel=channel)
	
	def gif_trigger(self, text):
		return "help" in text.lower() or "halp" in text.lower()
	
	def post_reaction(self, channel, ts, emoji):
		response = self.client.api_call("reactions.add", name=emoji, channel=channel, timestamp=ts)

	def post_gif(self, channel, type="all"):
		self.log("status", "Retrieving gif of type " + type)
		url = self.store.get_gif(type)
		if url:
			text = random.choice(self.greetings).format(random.choice(self.nouns)) + " " + url
			self.post_message(text=text, channel=channel)
			return
		self.post_message("Sorry, I have no gifs of type `" + type + "` :weary:", channel=channel)

	def compare_counts(self, channel, tokens):
		best_count = 0
		best_tag = "neither of them!"
		msg = "Current GIF counts:\n```"
		for t in tokens:
			count = self.store.get_count(t)
			msg += "  " + t + " : " + str(count) + "\n"
			if count == 0:
				continue
			if count == best_count:
				if "both " in best_tag:
					best_tag += " and " + t
				else:
					best_tag = "both " + best_tag + " and " + t
			elif count > best_count:
				best_count = count
				best_tag = t
		msg += "```\nThe winner is.... " + best_tag + "!"
		self.post_message(text=msg, channel=channel)

	def log(self, type, message):
		msg = "{} {} {}".format(time.strftime("%Y%m%d %H:%M:%S", time.gmtime()),
		                        ("[" + type.upper() + "]").ljust(8),
		                        message)
		print(msg)
