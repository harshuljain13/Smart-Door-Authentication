import json
import boto3
import time
import random as r


smsClient = boto3.client('sns')

dynamo_resource = boto3.resource('dynamodb')

dynamo_visitors_table = dynamo_resource.Table("visitors")
dynamo_passcodes_table = dynamo_resource.Table("passcodes")


def lambda_handler(event, context):
    
    visitors_faceId = event['faceid']
    visitors_filename = event['filename']
    key = {'faceid' : visitors_faceId}
    visitors_response = dynamo_visitors_table.get_item(Key=key)
    
    keys_list = list(visitors_response.keys())
    
    if('Item' in keys_list):
        visitors_name = visitors_response['Item']['name']
        visitors_phone = visitors_response['Item']['phone'] #photo changed to phone 
        visitors_photo = visitors_response['Item']['photo']
        photo={'objectKey':visitors_filename , 'bucket' : 'visitorb01', 'createdTimestamp' : str(time.ctime(time.time()))} # bucket changed to visitorb01
        visitors_photo.append(photo)
    
    else:
        visitors_name = event['name']
        visitors_phone = event['phone']
        
        visitors_photo = []
        photo={'objectKey':visitors_filename , 'bucket' : 'visitorb01', 'createdTimestamp' : str(time.ctime(time.time()))} #bucket name changed to visitorb01
        visitors_photo.append(photo)
    
    
    otp=""
    for i in range(4):
        otp+=str(r.randint(1,9))
    
    my_visitor_entry = {'faceid' : visitors_faceId , 'name' : visitors_name , 'phone' : visitors_phone , 'photo' : visitors_photo}
    dynamo_visitors_table.put_item(Item=my_visitor_entry)
    
    my_passcodes_entry = {'faceid' : visitors_faceId, 'otp': otp, 'expiration' : int(time.time() + 300)}
    dynamo_passcodes_table.put_item(Item=my_passcodes_entry)
    
    sendOtpToVisitor(visitors_phone, otp)
   
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }


def sendOtpToVisitor(phone_number, otp):
    
    message_visitor = "Hello, here is your one time password, "
    message_visitor += str(otp)
    
    smsClient.publish(PhoneNumber="+1"+phone_number,Message=message_visitor)