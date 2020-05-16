"""
This sample demonstrates an implementation of the Lex Code Hook Interface
in order to serve a sample bot which manages orders for flowers.
Bot, Intent, and Slot models which are compatible with this sample can be found in the Lex Console
as part of the 'OrderFlowers' template.

For instructions on how to set up and test this bot, as well as additional samples,
visit the Lex Getting Started documentation http://docs.aws.amazon.com/lex/latest/dg/getting-started.html.
"""
import math
import dateutil.parser
import datetime
import time
import os
import logging
import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import json
import botocore



logger = logging.getLogger()
logger.setLevel(logging.ERROR)


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

def validate_search_request(noun_1, noun_2 ):

    if noun_1 is not None:
            if noun_1.isnumeric():
                return build_validation_result(False,
                                               'animals',
                                               'Invalid value with numbers. Please enter the value again')
            if ' ' in noun_1:
                return build_validation_result(False,
                                               'animals',
                                               'The provided input value for first slot is invalid as it contains spaces. Please enter the value again')

    if noun_2 is not None:
        if noun_2.isnumeric():
            return build_validation_result(False,
                                           'sports',
                                           'The input value for second slot is invalid as it contains numbers. Please enter a valid value'
                                         .format(str(noun_2)))
    # if drinks is not None:
    #     if str(drinks).isnumeric():
    #         return build_validation_result(False,
    #                                        'Drinks',
    #                                        'The input drink {} is invalid as it contains numbers. '
    #                                        'Please enter a valid drink'
    #                                        .format(str(drinks)))
    # if date is not None:
    #     # Handle if date is today or tomorrow and handle for date formats other than mm--dd-yyyy
    #     if not isvalid_date(date):
    #         return build_validation_result(False, 'Date', 'I did not understand that, what date would you like '
    #                                                       'to book a reservation? '
    #                                                       'Please enter date in the format MM-DD-YYYY (with hyphens)' )
    #     elif datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
    #         return build_validation_result(False, 'Date', 'You can book restaurants from today. The date entered is not valid   '
    #                                                       'What day would you like to book a table?')
    #
    # if phone_number is not None:
    #     phone_number = str(phone_number)
    #     if not phone_number[0:1] == "+1":
    #         return build_validation_result(False, 'Phone_Number', 'The phone number entered does not have the country '
    #                                                               'code or is not a US phone number.  '
    #                                                               'Please enter a US number starting with +1')
    #     phone_number = phone_number[2 :]
    #     if not int(phone_number) or len(phone_number) != 10:
    #         if not phone_number[0:2] == "+1":
    #             return build_validation_result(False, 'Phone_Number',
    #                                            'The phone number entered is not a valid phone number '
    #                                            'Please enter a US number starting with +1')
    #
    # if no_of_people is not None:
    #     if not int(no_of_people):
    #         return build_validation_result(False, 'No_of_people',
    #                                        'The no of people entered is not a number '
    #                                        'Please enter a number')
    #     if int(no_of_people) <1:
    #         return build_validation_result(False, 'No_of_people',
    #                                        'The no of people entered is less than 1 '
    #                                        'Please enter a number greater than 1')
    # Tejas
    # Pick up time not considered currently

    # if pickup_time is not None:
    #     if len(pickup_time) != 5:
    #         # Not a valid time; use a prompt defined on the build-time model.
    #         return build_validation_result(False, 'PickupTime', None)
    #
    #     hour, minute = pickup_time.split(':')
    #     hour = parse_int(hour)
    #     minute = parse_int(minute)
    #     if math.isnan(hour) or math.isnan(minute):
    #         # Not a valid time; use a prompt defined on the build-time model.
    #         return build_validation_result(False, 'PickupTime', None)
    #
    #     if hour < 10 or hour > 16:
    #         # Outside of business hours
    #         return build_validation_result(False, 'PickupTime', 'Our business hours are from ten a m. to five p m. Can you specify a time during this range?')

    return build_validation_result(True, None, None)


""" --- Functions that control the bot's behavior --- """


def search_suggestions(intent_request):
    """
    Performs dialog management and fulfillment for Searching the requested items.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """

    noun_1 = get_slots(intent_request)["animals"]
    noun_2 = get_slots(intent_request)["sports"]
    print("Noun_1",noun_1)
    print("Noun_2",noun_2) 
    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_search_request(noun_1 , noun_2)
        # print("################################")
        print('Validation Result:',validation_result)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])


        # output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

        # return delegate(output_session_attributes, get_slots(intent_request))

    # sqs = boto3.resource('sqs', 'us-east-1')
    #
    # queue = sqs.get_queue_by_name(QueueName='ChatbotAssignmentQ1')
    # test_body = {
    #     "Date": date,
    #     "Cusine": cusine,
    #     "Drinks": drinks,
    #     "Location": location,
    #     "No_of_people": no_of_people,
    #     "Phone_Number": phone_number,
    #     "Street": street
    # }
    #
    # response = queue.send_message(MessageBody=str(test_body))
    
    # Query Elastic search and get the paths of images that satisfy the given criteria
    # Store the resultant image list in variable image_list ( initialized to None for Now)

    region = 'us-east-1'
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    host = 'vpc-photos-plg3qizcqhdnhij3jnpnbpnyaq.us-east-1.es.amazonaws.com'


    es = Elasticsearch(
    hosts = [{'host': host, 'port': 443}],
    http_auth = awsauth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection)
    
    search_list=[]
    if(noun_1):
        search_list.append(noun_1)
    if(noun_2):
        search_list.append(noun_2)
    print("Search List is:",search_list) 
    
    k = es.search(index="image-data", doc_type="_doc", body={"query": {"terms": {"labels":search_list}}})
    l = json.dumps(k)
    print("K after elastic search is=",k)
    # print("l is:",)
    image_list=[]
    print(image_list)
    # length=len(k["hits"]["hits"])
    # print("Length=",len)
    for i in k["hits"]["hits"]:
        print("inside for",i)
        file_name=i["_source"]["objectKey"]
        print(file_name)
        # if not image_list:
        image_list.append("https://voicecontrolledsearchb2.s3.amazonaws.com/"+file_name)
    print(image_list)


    print("After for")
    
    # file_name=k["hits"]["hits"][0]["_source"]["objectKey"]
    bucket_name=k["hits"]["hits"][0]["_source"]["bucket"]
    
    
    
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': '{}'.format(image_list)})
    

""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))
    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'SearchIntent':
        return search_suggestions(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')

def upload_file_to_s3(local_file_path, bucket_name, s3_file_path):
    try:
        # Upload file to S3
        s3 = boto3.client('s3')

        # path_output_dir + str(count - 1) + '.png'
        # 'stream' + fragment_name + '.png'
        s3.upload_file(local_file_path, bucket_name, s3_file_path)
        return True
    except Exception as e:
        print("An error occurred while uploading files to S3 with exception ",
              e)
        return False

# Download transcribe file from s3
def download_file_from_s3(bucket, s3_file_path,mp3_file_path):
    try:
        s3 = boto3.resource('s3')
        # local_file_path = "/tmp/test_file.webm"
        response1 = s3.Bucket(bucket).download_file(s3_file_path, local_file_path)
        if response1:
            print("File Downloaded from S3 ")
        response2 = AudioSegment.from_file(local_file_path).export(mp3_file_path, format="mp3")
        if response2:
            print("Converted file to mp3 format")
        return response2

    except Exception as e:
        print(str(e))
        return False
        
""" --- Main handler --- """
def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    # logger.debug('event.bot.name={}'.format(event['bot']['name']))
    print("Event is " , event )
    try:
        # This means call was made by AWS LEX
        if 'currentIntent' in event.keys():
            if event['currentIntent'] != None:
                return dispatch(event)
        if event['Records'][0]['eventSource'] == 'aws:s3':
            print("S3 event triggered!!!!!")
            bucket = event['Records'][0]['s3']['bucket']['name']
            transcribe_job_file_name = event['Records'][0]['s3']['object']['key']
            # mp3_file_path = "/tmp/voice1.mp3"
            # voice_control-copy4.json
            print("After bucket")
            print("Bucket name:",bucket)
            print("job file name",transcribe_job_file_name)
            s3 = boto3.resource('s3')
            local_file_path = "/tmp/test_transcribe.json"
            
            print("After creation of boto3 resource")
            
            response1 = s3.Bucket(bucket).download_file(transcribe_job_file_name, local_file_path)
            print("After download statement:",response1)
            
            with open(local_file_path) as file_ptr2:
                json_data = json.load(file_ptr2)
            print("After with open :",json_data)

            voice_to_text=json_data['results']['transcripts'][0]['transcript']
            print("Decoded text is:",voice_to_text)
            
            # download_res = download_file_from_s3_and_convert_to_mp3(bucket=bucket,
                                # s3_file_path=transcribe_job_file_name,mp3_file_path=mp3_file_path)
            # print("Result from download and convert file ", download_res)

    except Exception as e:
        print("The exception is :",e)
    
    finally:
        # This means call was made by API Gateway
        print("Timepass")
