import os
import ssl
import certifi
import logging
import time
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from dotenv import load_dotenv
from funciones import process_slack_message

# Logging configuration
logging.basicConfig(level=logging.DEBUG)

# Store recent responses to avoid duplicates
recent_responses = {}
RESPONSE_TIMEOUT = 10  # Time in seconds to consider duplicate responses

def load_config():
    """
    Loads and validates the required environment variables.
    """
    load_dotenv()
    slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
    slack_app_token = os.getenv('SLACK_APP_TOKEN')

    if not slack_bot_token or not slack_app_token:
        raise EnvironmentError("Missing SLACK_BOT_TOKEN or SLACK_APP_TOKEN in the .env file")
    
    return slack_bot_token, slack_app_token

# Initialization
slack_bot_token, slack_app_token = load_config()
ssl_context = ssl.create_default_context(cafile=certifi.where())
client = WebClient(token=slack_bot_token, ssl=ssl_context)
socket_client = SocketModeClient(app_token=slack_app_token, web_client=client)

try:
    client.users_setPresence(presence="auto")
    logging.info("Bot presence set to 'auto'")
except SlackApiError as e:
    logging.error(f"Error setting bot presence: {e.response['error']}")

app = Flask(__name__)

def is_duplicate_response(channel, thread_ts, response_text):
    """
    Checks if the same response has been sent recently in the same thread.
    """
    key = (channel, thread_ts)
    current_time = time.time()
    if key in recent_responses:
        last_response, timestamp = recent_responses[key]
        if last_response == response_text and (current_time - timestamp) < RESPONSE_TIMEOUT:
            return True
    recent_responses[key] = (response_text, current_time)
    return False

@app.route('/send_message', methods=['POST'])
def send_message():
    """
    Endpoint to send a message to a specific Slack channel.
    """
    data = request.get_json()
    channel_id = data.get('channel_id')
    if not channel_id:
        return jsonify({"error": "No channel_id provided"}), 400

    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text="Hello, this is a test message from the bot!"
        )
        return jsonify({"status": "Message sent", "response": response.data}), 200
    except SlackApiError as e:
        logging.error(f"Error sending message: {e.response['error']}")
        return jsonify({"error": e.response['error']}), 500

def handle_app_mention_events(client, req: SocketModeRequest):
    """
    Handles app mention events in Slack.
    """
    if req.type == "events_api" and "event" in req.payload:
        event = req.payload["event"]
        if event.get("type") == "app_mention":
            user = event["user"]
            text = event["text"]
            channel = event["channel"]
            thread_ts = event.get("thread_ts", event["ts"])
            ts = event["ts"]

            try:
                client.web_client.reactions_add(
                    name="wave",
                    channel=channel,
                    timestamp=ts
                )
            except Exception as e:
                logging.error(f"Error adding reaction: {e}")

            if any(greeting in text.lower() for greeting in ["hi", "hello", "hola", "hey"]):
                response_text = f"<@{user}> How can I assist you?"
            else:
                response_text = process_slack_message(text).replace("Assistant", "Tier-2 Slack Bot")

            if not is_duplicate_response(channel, thread_ts, response_text):
                client.web_client.chat_postMessage(
                    channel=channel,
                    text=response_text,
                    thread_ts=thread_ts
                )
            else:
                logging.info("Duplicate response detected, skipping message.")

        socket_client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

def setup_socket_client():
    """
    Configures and connects the Socket Mode client.
    """
    socket_client.socket_mode_request_listeners.append(handle_app_mention_events)
    socket_client.connect()
    logging.info("Slack bot is listening for events...")

if __name__ == "__main__":
    setup_socket_client()
    ssl_cert = '/Users/sofiasanabria/Desktop/Sassito/cert.pem'
    ssl_key = '/Users/sofiasanabria/Desktop/Sassito/key.pem'
    ssl_context = (ssl_cert, ssl_key) if os.path.exists(ssl_cert) and os.path.exists(ssl_key) else None
    app.run(port=3000, ssl_context=ssl_context)
