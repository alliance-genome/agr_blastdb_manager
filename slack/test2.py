from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Create a client instance
client = WebClient(token='xoxb-32867833447-6153585617507-jPHvbqxoHnUYCOuxezF8BrFZ')

try:
   # Call the chat.postMessage method using the WebClient
   response = client.chat_postMessage(
       channel='#blast-status', # Channel to send message to
       text="Example of rich message", # Subject of the message
       attachments=[
           {
               "title": "Update 1",
               "text": "Thanks for all the fish.",
               "color": "#36a64f"
           },
           {
               "title": "Update 2",
               "text": "Red alert, Marvin.",
               "color": "#8D2707"
           }
       ]
   )
except SlackApiError as e:
   # You will get a SlackApiError if "ok" is False
   assert e.response["ok"] is False
   assert e.response["error"] # str like 'invalid_auth', 'channel_not_found'
   print(f"Got an error: {e.response['error']}")
