from __future__ import print_function

import base64
import email
import os
import pprint
import time
from email.mime.text import MIMEText
from email.utils import parseaddr

import httplib2
from apiclient import discovery
from apiclient import errors
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

from .canned_reply_config import to, senders, user_id, message_text, canned_label, \
    sender_credentials_file, client_secret_file

try:
    import argparse

    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/<sender_credentials_file>.json
SCOPES = ['https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.modify']
APPLICATION_NAME = 'Gmail API Python Quickstart'
seconds_between_checks = 15


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   sender_credentials_file)

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(client_secret_file, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def create_message(origin=None, destination=to, subject=None, msg_txt=None, thr_id=None):
    """Create a message for an email.

    Args:
      origin: Email address of the sender.
      destination: Email address of the receiver.
      subject: The subject of the email message.
      msg_txt: The text of the email message.
      thr_id: the threadId of the message to attach

    Returns:
      An object containing a base64url encoded email object.
    """
    message = MIMEText(msg_txt)
    message['to'] = destination
    message['from'] = origin
    message['subject'] = subject
    return {'raw': (base64.urlsafe_b64encode(message.as_bytes()).decode()),
            'threadId': thr_id}


def send_message(service, user_id, message):
    """Send an email message.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      message: Message to be sent.

    Returns:
      Sent Message.
    """
    try:
        message = (service.users().messages().send(userId=user_id, body=message)
                   .execute())
        print('Message Id: {}'.format(message['id']))
        return message
    except errors.HttpError as error:
        print('An error occurred: {}'.format(error))


def list_messages_matching_query(service, user_id, query='', label_ids=[],
                                 maxResults=None):
    """List all Messages of the user's mailbox matching the query.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      query: String used to filter messages returned.
      Eg.- 'from:user@some_domain.com' for Messages from a particular sender.
      label_ids: the list of labelIds present in the query
      maxResults: number of messages to return and to obtain at a time

    Returns:
      List of Messages that match the criteria of the query. Note that the
      returned list contains Message IDs, you must use get with the
      appropriate ID to get the details of a Message.
    """
    try:
        response = service.users().messages().list(userId=user_id, q=query,
                                                   labelIds=label_ids,
                                                   maxResults=maxResults).execute()
        messages = []
        if 'messages' in response:
            messages.extend(response['messages'])

        while 'nextPageToken' in response:
            if len(messages) >= maxResults:
                break
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId=user_id, q=query,
                                                       labelIds=label_ids,
                                                       pageToken=page_token).execute()
            messages.extend(response['messages'])

        return messages
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def list_labels(service, user_id):
    """Get a list all labels in the user's mailbox.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.

    Returns:
      A list all Labels in the user's mailbox.
    """
    try:
        response = service.users().labels().list(userId=user_id).execute()
        labels = response['labels']
        for label in labels:
            print('Label id: %s - Label name: %s' % (label['id'], label['name']))
        return labels
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def simple_list_labels(service, user_id):
    """Provide a simple list of labels present in account

    :param service:
    :param user_id:
    :return: list of label names
    """
    results = service.users().labels().list(userId=user_id).execute()
    labels = results.get('labels', ())
    list_labels = []
    if not labels:
        print('No labels found.')
    else:
        for label in labels:
            list_labels.append(label['name'])

    return list_labels


def get_message(service, user_id, msg_id):
    """Get a Message with given ID.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      msg_id: The ID of the Message required.

    Returns:
      A Message.
    """
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id).execute()

        return message
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def message_body_as_string(message):
    """Returns the message body decoded as text

    :param message:
    :return: string
    """
    if 'multipart' in message['payload']['mimeType']:
        # for multi-part messages
        for part in message['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                return base64.urlsafe_b64decode(part['body']['data']).decode()
    # for straightforward messages
    else:
        for part in [message['payload']]:
            if part['mimeType'] == 'text/plain':
                return base64.urlsafe_b64decode(part['body']['data']).decode()


def get_mime_message(service, user_id, msg_id):
    """Get a Message and use it to create a MIME Message.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      msg_id: The ID of the Message required.

    Returns:
      A MIME Message, consisting of data from Message.
    """
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id,
                                                 format='raw').execute()

        msg_str = base64.urlsafe_b64decode(message['raw']).decode()

        mime_msg = email.message_from_string(msg_str)

        return mime_msg
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def print_mime_message(message):
    # from email - print header details
    print('From: {}'.format(message['From']))
    print('To: {}'.format(message['To']))
    print('Subject: {}'.format(message['Subject']))
    print('Date: {}'.format(message['Date']))
    print('Message-ID: {}'.format(message['Message-ID']))
    print('---')

    # print body of email
    for parts in message.walk():
        if parts.get_content_type() == 'text/plain':
            print('---------')
            print(parts.get_payload())
            print('---------')


def modify_message(service, user_id, msg_id, msg_labels):
    """Modify the Labels on the given Message.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      msg_id: The id of the message required.
      msg_labels: The change in labels.

    Returns:
      Modified message, containing updated labelIds, id and threadId.
    """
    try:
        message = service.users().messages().modify(userId=user_id, id=msg_id,
                                                    body=msg_labels).execute()

        label_ids = message['labelIds']

        print('Message ID: %s - With Label IDs %s' % (msg_id, label_ids))
        return message
    except errors.HttpError as error:
        print('An error occurred: {}'.format(error))


def field_from_message(message, field_name):
    # 3 different ways of getting the from field from the message
    msg_headers = message['payload']['headers']
    msg_sender = None
    clean_name = field_name.strip().lower()

    # Way 1: a standard for , if loop, which breaks as soon as it finds the message
    # clean_name in the message fields
    for field in msg_headers:
        clean_field = field['name'].strip().lower()
        if clean_field == clean_name:
            msg_sender = field['value']
            break

    # Way 2: a dictionary generator
    # msg_sender = next((item['value'] for item in msg_headers if
    #                    item['name'].strip().lower() == clean_name), None)

    # Way 3: a filter
    # msg_sender = next(filter(lambda field: field['name'].strip().lower() == clean_name,
    # msg_headers))['value']

    return msg_sender


def create_msg_labels(service, addLabels=[], removeLabels=[]):
    """Create object to update labels.

    Returns:
      A label update object.
    """
    for label in addLabels:
        if label not in simple_list_labels(service, user_id):
            new_label = make_label(label)
            label_obj = create_label(service, user_id, new_label)
            print('Added label {}, label_id: '.format(label, label_obj))
    return {'removeLabelIds': removeLabels, 'addLabelIds': addLabels}


def create_label(service, user_id, label_object):
    """Creates a new label within user's mailbox, also prints Label ID.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      label_object: label to be added.

    Returns:
      Created Label.
    """
    try:
        label = service.users().labels().create(userId=user_id,
                                                body=label_object).execute()
        print(
            'created label name: {}, label id: {}'.format(label_object["name"],
                                                          label['id']))
        return label
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def make_label(label_name, mlv='show', llv='labelShow'):
    """Create Label object.

    Args:
      label_name: The name of the Label.
      mlv: Message list visibility, show/hide.
      llv: Label list visibility, labelShow/labelHide.

    Returns:
      Created Label.
    """
    label = {'messageListVisibility': mlv,
             'name': label_name,
             'labelListVisibility': llv}
    return label


def get_thread(service, user_id, thread_id):
    """Get a Thread.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      thread_id: The ID of the Thread required.

    Returns:
      Thread with matching ID.
    """
    try:
        thread = service.users().threads().get(userId=user_id, id=thread_id).execute()
        messages = thread['messages']
        print('thread id: {} , messages in this thread: {}'.format(thread['id'],
                                                                   len(messages)))
        return thread
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def modify_thread(service, user_id, thread_id, msg_labels):
    """Add labels to a Thread.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      thread_id: The id of the thread to be modified.
      msg_labels: The change in labels.

    Returns:
      Thread with modified Labels.
    """
    try:
        thread = service.users().threads().modify(userId=user_id, id=thread_id,
                                                  body=msg_labels).execute()

        thread_id = thread['id']
        label_ids = thread['messages'][0]['labelIds']

        print('Thread ID: {} - With Label IDs: {}'.format(thread_id, label_ids))
        return thread
    except errors.HttpError as error:
        print('An error occurred: {}'.format(error))


def find_label_id(service, user_id, label_name):
    try:
        response = service.users().labels().list(userId=user_id).execute()
        labels = response['labels']
        for label in labels:
            if label["name"] == label_name:
                return label["id"]
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def get_label_id(service, canned_label):
    label_id = find_label_id(service, user_id, canned_label)
    if label_id is None:
        new_label = make_label(canned_label)
        label_id = create_label(service, user_id, new_label)['id']
    return label_id


def find_label_names(service, label_ids=[]):
    """ finds the label names given a list of label_ids

    :param service:
    :param label_ids: list of label_ids
    :return: list of label_names
    """
    try:
        response = service.users().labels().list(userId=user_id).execute()
        labels = response['labels']
        label_names = []
        for label_id in label_ids:
            for label in labels:
                if label_id == label['id']:
                    label_names.append(label['name'])
                    break

        return label_names
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def main():
    """Canned reply responder using the Gmail API.

    Creates a Gmail API service object and responds to a query with a standard response
    whilst giving it a label to ensure only 1 response per thread is sent
    """

    # start time in milliseconds to compare with last message time
    start_time = int(time.time()) * 1000

    # get credentials first and create gmail service object
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)

    while True:
        # receive email messages
        q_to_list = ['from:' + e_mail for e_mail in senders]
        q = 'in:inbox {}'.format(' OR '.join(q_to_list))
        messages = list_messages_matching_query(service, user_id,
                                                query=q,
                                                maxResults=1)
        if not messages:
            print("No messages to show")
            time.sleep(seconds_between_checks)
            continue
        else:
            pprint.pprint('Messages to show: {}'.format(messages))

        # get thread of first document - so you can label the thread itself if need be
        thread_id = messages[0]['threadId']
        thread = get_thread(service, user_id, thread_id)

        msg_id = messages[0]['id']
        message = get_message(service, user_id, msg_id)

        msg_sender = field_from_message(message, 'From')
        canned_label_id = get_label_id(service, canned_label)
        thread_label_ids = thread['messages'][0]["labelIds"]

        # check that the date is later than starting, and emails match list
        if int(message["internalDate"]) < start_time:
            print('internalDate earlier than start_time!')
            print("better luck next time")
        # check if it's already replied to
        elif canned_label_id in thread_label_ids:
            print("you replied already to this one, even if it is later than startup")
            print("better luck next time")
        else:
            # check cleaned sender email in list
            sender_email = parseaddr(msg_sender)[1]
            if sender_email not in senders:
                print("emails don't match!!")
            # after all tests passed, reply to message with same subject
            else:
                subject = 'Re: ' + field_from_message(message, 'Subject')
                msg = create_message(destination=msg_sender, origin=to,
                                     subject=subject,
                                     msg_txt=message_text, thr_id=thread_id)
                send_message(service, user_id, msg)
                print("Replied to message!")
                start_time = int(time.time()) * 1000

                # then label the thread
                labels = create_msg_labels(service, addLabels=[canned_label_id])
                modify_thread(service, user_id, thread_id, labels)
                print("Added a label: {} ".format(canned_label))
                print('done!')

        # always print blank line and wait a few seconds
        print('=====\n')
        time.sleep(seconds_between_checks)


if __name__ == '__main__':
    main()
