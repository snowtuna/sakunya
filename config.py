import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
TIMEWINDOW = int(os.getenv("timewindow", 2))
MAXMSG = int(os.getenv("maxmsg", 4))
PREFIX = "^w^ "