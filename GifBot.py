from configobj import ConfigObj
from slackclient import SlackClient
from GifStore import GifStore
import time

class GifBot:
	def __init__(self, filename):
		config = ConfigObj(filename)
		self.NAME      = config["bot_name"]
		self.OWNER     = config["bot_owner"]
		self.API_TOKEN = config["api_token"]
		self.MANIFEST  = config["manifest_loc"]
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
				raise Exception("Unable to find user \"" + self.NAME + "\" in the Slack channel")
			if not set_owner_id:
				raise Exception("Unable to find user \"" + self.OWNER + "\" in the Slack channel")
		else:
			raise Exception("Error in Slack API call users.list")
	
	def run(self):
		DELAY = 1
		if self.client.rtm_connect():
			print("Bot \"" + self.NAME + "\" is running")
			while True:
				rtm_messages = self.client.rtm_read()
				self.handle(rtm_messages)
				time.sleep(DELAY)
	
	def handle(self, rtm_messages):
		if rtm_messages and len(rtm_messages) > 0:
			for message in rtm_messages:
				print("[received " + message["type"] + "]")
				if message["type"] == "message":
					self.handle_message(message)
	
	def handle_message(self, message):
		if "user" not in message:
			print("Unknown message type")
			return
		if message["user"] == self.BOT_ID:
			print("Self message")
			return
		elif message["user"] == self.OWNER_ID and message["channel"][0] == "D":
			print("Handling command")
			self.handle_command(message["text"], message["channel"])
		elif self.is_mention(message["text"]):
			print("Handling mention")
			self.handle_mention(message["text"], message["channel"])
		elif self.gif_trigger(message["text"]):
			print("Handling GIF request")
			self.post_gif(message["channel"])
	
	def is_mention(self, text):
		return "@" + self.BOT_ID in text
	
	def post_message(self, text, channel):
		self.client.api_call("chat.postMessage", channel=channel, text=text, as_user=True)
	
	def handle_command(self, text, channel):
		tokens = text.split(" ")
		if tokens[0] == "add":
			self.store.add_gif(tokens[1], tokens[2:])
			self.post_message(text="Adding " + tokens[1], channel=channel)
		elif tokens[0] == "remove":
			self.store.remove_gif(tokens[1])
			self.post_message(text="Removing " + tokens[1], channel=channel)
		elif tokens[0] == "status":
			self.post_message(text=self.store.get_info(max=10), channel=channel)
		elif tokens[0] == "request":
			if len(tokens) > 1:
				self.post_gif(channel=channel, type=tokens[1])
			else:
				self.post_gif(channel=channel)
		elif tokens[0] == "reload":
			self.store = GifStore(open(self.MANIFEST).read())
		else:
			self.post_message(text="Sorry, I don't understand that command. :/", channel=channel)
	
	def handle_mention(self, text, channel):
		tokens = text.split(" ")
		if tokens[0] != "<@" + self.BOT_ID + ">":
			return
		elif len(tokens) == 2 and tokens[1] == "help":
			text="Known commands:\n`help` : Display self message\n`status` : Give a status report of the bot\n`request cat` : Request a cat GIF"
			self.post_message(text=text, channel=channel)
		elif len(tokens) == 2 and tokens[1] == "status":
			self.post_message(text=self.store.get_info(max=10), channel=channel)
		elif len(tokens) == 3 and tokens[1] == "request":
			self.post_gif(channel, tokens[2])
		else:
			self.post_message(text="Sorry, I don't understand that. :/\nHINT: try `@" + self.NAME + " help`", channel=channel)
	
	def gif_trigger(self, text):
		return "help" in text.lower()
	
	def post_gif(self, channel, type="all"):
		if type != "all" and not type in self.store.get_tags():
			self.post_message("An error occurred. :(", channel=channel)
			self.post_message("[UNKNOWN GIF TYPE : \"" + type + "\"]", channel=channel)
			return
		for i in range(10):
			print("Getting gif of type " + type)
			url = self.store.get_gif(type)
			if url:
				self.post_message(text="Look after yourself, buddy! " + url, channel=channel)
				return
		print("Unable to find a gif of type " + type + " :(")
