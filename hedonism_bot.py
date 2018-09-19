import signal
import logging
import re
import requests
import time
from logging import handlers
from slackclient import SlackClient
from settings import SLACK_BOT_TOKEN
exit_flag = False
start_time = time.time()

"""custom logger"""
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = handlers.RotatingFileHandler(
    'slackbot_logs.log', mode='a', maxBytes=1000, backupCount=5)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
searched_files = {}


def receive_signal(sig, stack):
    """Listener for SIGINT and SIGTERM"""
    logger.warning("Received signal: {}".format(sig))
    global exit_flag
    if sig == signal.SIGINT:
        logger.info('SIGINT detected')
        exit_flag = True
    if sig == signal.SIGTERM:
        logger.info('SIGTERM detected')
        exit_flag = True


# instantiate Slack client
slack_client = SlackClient(SLACK_BOT_TOKEN)
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None

# constants
RTM_READ_DELAY = 1  # 1 second delay between reading from RTM
TEST_COMMAND = "test"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"


def command_clean(str):
    low_str = str.lower()
    new_str = ' '.join(low_str.split())
    return new_str


def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from
        the Slack RTM API to find bot commands.
        If a bot command is found, this function
        returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and "subtype" not in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None


def parse_direct_mention(message_text):
    """
        Finds a direct mention
        (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned.
        If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username,
    # the second group contains the remaining message
    return (matches.group(1),
            matches.group(2).strip()) if matches else (None, None)


def handle_command(command, channel):
    command = command_clean(command)
    PING_COMMAND = 'ping'
    EXIT_COMMAND = 'exit'
    DAD_JOKE = 'dad joke'
    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    default_response = "Type help to see a list of commands"

    # Finds and executes the given command, filling in response
    response = None
    global start_time

    if command.startswith('help'):
        response = (
            "Try one of these delicious commands:\n`{}`\n`{}`\n`{}`".format(
                    PING_COMMAND, EXIT_COMMAND, DAD_JOKE))

    if command.startswith(TEST_COMMAND):
        response = "Stuff is happening"

    if command.startswith('fuck ryan'):
        response = "<@ryanbot> exit"

    if command.startswith('ping'):
        response = 'Uptime: {} seconds'.format(time.time() - start_time)

    if command.startswith('dad joke'):
        r = requests.get('https://icanhazdadjoke.com/slack')
        joke = r.json()
        response = joke['attachments'][0]['text']

    if command.startswith('exit'):
        global exit_flag
        response = "I'll be upstairs...putting batteries in things"
        exit_flag = True
    logger.info('Response: {}'.format(response))
    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )


if __name__ == "__main__":
    channel_test_url = 'https://hooks.slack.com/services/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'
    payload = {'text': 'Oh, sirrah, how deliciously absurd!'}
    signal.signal(signal.SIGINT, receive_signal)
    signal.signal(signal.SIGTERM, receive_signal)
    if slack_client.rtm_connect(with_team_state=False):
        print("Hedonism-bot connected and running!")
        logger.info("Hedonism-bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        r = requests.post(channel_test_url, json=payload)
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while not exit_flag:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            try:
                if command:
                    logger.info('Command: {}'.format(command))
                    handle_command(command, channel)
                    time.sleep(RTM_READ_DELAY)
            except Exception as exc:
                logger.exception('Unhandled exception: {}'.format(exc))
                time.sleep(5)
    else:
        logger.error("Failed to connect")
        print("Connection failed. Exception traceback printed above.")
