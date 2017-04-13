import random

class GifStore:
	class Element:
		def __init__(self, url, tags):
			self.url = url
			self.tags = tags
	
	def __init__(self, data=""):
		self.elements = []
		self.tags = {}
		self.modifiers = [ "wonderful", "stupendous", "glorious", "life-changing", "heart warming", "endearing", "charming"]
		if data != "":
			for line in data.splitlines():
				line_data = line.split(",")
				if len(line_data) >= 2:
					self.add_gif(line_data[0], line_data[1:])
	
	
	def add_gif(self, url, tags):
		self.elements.append(self.Element(url, tags))
		for t in tags:
			if t in self.tags.keys():
				self.tags[t] += 1
			else:
				self.tags[t] = 1
	
	def remove_gif(self, url):
		matches = [e for e in self.elements
		              if e.url == url]
		if len(matches)==0:
			return
		self.elements = [e for e in self.elements
		                    if e.url != url]
		# Update the tags
		match_tags = [t for t_ in matches
		                for t in t_.tags]
		for t in match_tags:
			self.tags[t] -= 1
			if self.tags[t] == 0:
				del self.tags[t]
	
	def get_tags(self):
		return [t for t in self.tags]

	def get_info(self, max):
		text = ""
		if max==0 or len(self.tags) < max:
			for t in self.tags:
				count = self.tags[t]
				text += "\nWe have " + str(count) + \
				        " " + random.choice(self.modifiers) + \
				        " " + t + \
				        " gif" + ("s" if count > 1 else "") + "!"
		else:
			for t in random.sample(list(self.tags), max):
				count = self.tags[t]
				text += "\nWe have " + str(count) + \
				        " " + random.choice(self.modifiers) + \
				        " " + t + \
				        " gif" + ("s" if count > 1 else "") + "!"
			text += "\n... and many more!"
		return text
	
	def get_gif(self, tag):
		if tag == "all":
			matches = self.elements
		else:
			matches = [e for e in self.elements
			              if tag in e.tags]
		if len(matches) == 0:
			return
		return random.choice(matches).url
	
	def save_manifest(self, filename):
		file = open(filename, "w")
		for e in self.elements:
			line = e.url
			for t in e.tags:
				line += "," + t
			file.write(line + "\n")
		file.close()
