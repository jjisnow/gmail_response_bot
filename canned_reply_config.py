# Your email - gets added in the "from" field when you write your reply
to = 'your email <your@email.com'

# a list of blacklisted senders whom this applies to. Emails must be surrounded by ''
# and separated by commas, and the list inside []
senders = ['boring@mail.com', 'spammer@mail.com']

# the standard reply text to reply with
message_text = """
Please respond to someone who cares
"""

user_id = 'me'

# the label for the responses
canned_label = 'Canned-reply'

# where the gmail api credentials and client_secret file is located
sender_credentials_file = 'email-sender-creds.json'
client_secret_file = 'your_client_secret.json'
