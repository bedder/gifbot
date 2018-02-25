# GifBot

GifBot is a simple Slack bot designed to make people happier on Slack by distributing GIFs to people that need them.

It was designed by [Matthew Bedder](https://twitter.com/bedder) for the [IGGI](http://iggi.org.uk) student Slack channel, and later released publicly.  

## Getting started

1) Install prerequisite libraries.
    * `pip3 install -r requirements.txt`
    
2) Update the `bot.config` file with the appropriate settings.

3) Create a `manifest.csv` file. This can initially be empty (with GIFs being added using the admin interface via Slack messages), but it needs to exist.

    * The `manifest.csv` file should be provided at the root of this git repository. Each line in the file should start with a URL to a GIF followed by any number of tags, as follows: 
    ```
    https://example.com/some.gif,tag1,tag2
    https://example.org/another.gif,tag3,tag4,tag5
    ```
    
4) Run the `run.py` script.
    * `python3 run.py`

5) Bask in the glory of GIFs-on-demand.

## Admin commands

The Slack user with the name provided in the `bot.config` file should be able to send direct messages to the bot in order to add or remove GIFs, update or reload the manifest, or see the status of the bot. For information on what commands are available, they should send the message `help` to the bot.

## License

GifBot is released under the [MIT license](https://tldrlegal.com/license/mit-license).

If you were to use GifBot, I would be very happy to hear from you [via Twitter](https://twitter.com/bedder)! This is just for my personal interest, so in no way interferes with the rights given to you under the MIT license, nor gives me any responsibility for the usage of this bot.
