import os
from flask import Flask, request, redirect
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Get Slack client ID, client secret, and redirect URI from environment variables
client_id = os.getenv('SLACK_CLIENT_ID')
client_secret = os.getenv('SLACK_CLIENT_SECRET')
redirect_uri = os.getenv('SLACK_REDIRECT_URI')

oauth_scope = "commands,bot"

# Pre-install route
@app.route("/slack/install", methods=["GET"])
def pre_install():
    state = "randomly-generated-one-time-value"
    return f'''
        <a href="https://slack.com/oauth/v2/authorize?scope={oauth_scope}&client_id={client_id}&state={state}&redirect_uri={redirect_uri}">
            Add to Slack
        </a>
    '''

# OAuth completion route
@app.route("/slack/oauth_redirect", methods=["GET"])
def post_install():
    # Verify the "state" parameter
    # (you should validate the state parameter here)

    # Retrieve the auth code from the request params
    code_param = request.args.get('code')
    state_param = request.args.get('state')

    # An empty string is a valid token for this request
    client = WebClient()

    try:
        # Request the auth tokens from Slack
        response = client.oauth_v2_access(
            client_id=client_id,
            client_secret=client_secret,
            code=code_param,
            redirect_uri=redirect_uri
        )
        logging.debug(f"OAuth response: {response}")

        # Save the bot token to an environmental variable or to your data store for later use
        os.environ["SLACK_BOT_TOKEN"] = response['access_token']

        # Don't forget to let the user know that OAuth has succeeded!
        return "Installation is completed!"
    except SlackApiError as e:
        logging.error(f"Error during OAuth: {e.response['error']}")
        return f"Error: {e.response['error']}"

if __name__ == "__main__":
    # Use the generated certificate and key
    app.run(host="localhost", port=3000, ssl_context=('cert.pem', 'key.pem'))


