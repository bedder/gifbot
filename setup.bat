@ECHO off

:start
:: Check if the virtual env has been created
IF EXIST venv GOTO :venv

:setup
:: Check that we know where virtualenv is, and request it if required
CALL where virtualenv > nul 2> nul
IF NOT ERRORLEVEL 1 GOTO :install
ECHO virtualenv not found - This must be added to this prompt's PATH variable for installing dependencies.
SET /P VENV_LOC=Please enter the location of the virtualenv executable:
SET PATH=%PATH%;%VENV_LOC%
GOTO :setup

:install
:: Create the virtual environment, and install requirements
CALL virtualenv venv
CALL venv\Scripts\Activate.bat
CALL pip install -r requirements.txt

:venv
:: Activate the virtual environment if required
IF NOT DEFINED VIRTUAL_ENV CALL venv\Scripts\Activate.bat

:end
ECHO Virtual environment and dependencies installed.
ECHO You can now run GifBot using the command "python run.py"