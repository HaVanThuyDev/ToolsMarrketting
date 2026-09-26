import os

from dotenv import load_dotenv


load_dotenv()


FACEBOOK_APP_ID = os.getenv(
    "FACEBOOK_APP_ID",
    ""
)

FACEBOOK_APP_SECRET = os.getenv(
    "FACEBOOK_APP_SECRET",
    ""
)

FACEBOOK_GRAPH_VERSION = os.getenv(
    "FACEBOOK_GRAPH_VERSION",
    "v23.0"
)

REDIRECT_URI = os.getenv(
    "FACEBOOK_REDIRECT_URI",
    "http://127.0.0.1:8080/oauth/callback"
)

OAUTH_PORT = 8080