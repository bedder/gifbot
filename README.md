# gifbot

## What is this?

It's a Slack Bot that looks after the wellbeing of people via the medium of animal GIFs.

## How do I use it?

It's just a Python project, so should be fairly easy to run. I recommended that you use `virtualenv` to install the dependencies.

1) Generate a `botconfig` file with the name of the bot, the API token for the bot, and the name of the controller (see `botconfig.example`)

2) Generate a `manifest.txt` file containing the URLs the bot can post, along with their associated tags (see `manifest.txt.example`)
    
3) Generate the Python virtual environment, and install the dependencies listed in `requirements.txt`

   This can be done using the `setup.bat` script, or manually.

		> virtualenv venv
		> venv\Scripts\activate
		> pip install -r requirements.txt 
			
4) Run the bot!

		> python run.py

## FAQs

#### Which version of Python should I use?

I use Python 3.4, but it may work with other versions.

#### Can it only post GIFs?

Nope, it just posts URLs.

#### Can I use this?

Why wouldn't you be able to? Just follow the license I've attached...

#### Can I use your GIF manifest?

Nope, sorry.

#### How do you pronounce GIF?

However makes you feel happiest. I use the "soft g".
