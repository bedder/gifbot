from gif_bot.GifBot import GifBot
import sys

def main():
	try:
		bot = GifBot("botconfig")
	except:
		print("[ERROR]  Unable to initialise the bot")
		print("[ERROR]  {}".format(sys.exc_info()[0]))
		return
	bot.run()

if __name__ == "__main__":
	main()
