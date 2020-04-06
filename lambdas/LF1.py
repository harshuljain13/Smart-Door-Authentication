import logging
import base64
import json
import cv2

import boto3
import os
import random as r
import time
from decimal import Decimal 

s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')

smsClient = boto3.client('sns')

dynamo_resource = boto3.resource('dynamodb')

dynamo_visitors_table = dynamo_resource.Table("visitors")
dynamo_passcodes_table = dynamo_resource.Table("passcodes")


def lambda_handler(event, context):
    print(cv2.VideoCapture)
    print(cv2.__version__)

    logging.info("API CALLED. EVENT IS:{}".format(event))
    print("Data streaming")
    json_data = event['Records'][0]['kinesis']['data']
    json_data = json.loads(base64.b64decode(json_data).decode('utf-8'))
    kvs_stream_name="smartdoor"
    print('JSON DATA: ',json_data)
    
    smsClient = boto3.client('sns')
    mobile = "34720045054"
    
    faceId='123'
    face_search_response = json_data['FaceSearchResponse'] # will be blank if no one is standing at door
    
    if not face_search_response:
        print(" No one at the door ")
        return ("No one at the door")
    else:
        matched_face = json_data['FaceSearchResponse'][0]['MatchedFaces']
    
    if face_search_response is not None and ( matched_face is None or len(matched_face)==0):
        print('Did not found the match in collections')
        fragmentNumber= json_data['InputInformation']['KinesisVideo']['FragmentNumber']
        fileName,faceId=store_image(kvs_stream_name,fragmentNumber, None)
        phone_number_owner = '3472004054'
        link_visitor_image = 'https://visitorb01.s3.amazonaws.com/' + filename
        
        ####saqib changes start
        link_visitor_details_form = 'https://visitorb01.s3.amazonaws.com/WebPage_Vistor_Info.html?filename='+fileName+"&faceid="+faceId
        ###saqib changes end
        
        print("URLs sent to Owner: ", link_visitor_details_form)
        sendMessageToOwner(phone_number_owner, link)
    else:
        print('found the match in collections')
        image_id = json_data['FaceSearchResponse'][0]['MatchedFaces'][0]['Face']['ImageId']
        print('IMAGEID',image_id)
        faceId = json_data['FaceSearchResponse'][0]['MatchedFaces'][0]['Face']['FaceId']
        print('FACEID',faceId)
    
        key = {'faceid' : faceId}   
        visitors_response = dynamo_visitors_table.get_item(Key=key)
        
        keys_list = list(visitors_response.keys())
        
        otp=""
        for i in range(4):
            otp+=str(r.randint(1,9))
        
        if('Item' in keys_list):
            print('Item found in visitors table')
            phone_number_visitor = visitors_response['Item']['phone']
            face_id_visitor = visitors_response['Item']['faceId']
            
            # send the otp to visitor
            
            
            visitors_name = visitors_response['Item']['name']
            visitors_photo = visitors_response['Item']['photo']
            photo={'objectKey':'updatedKey' , 'bucket' : 'visitorb01', 'createdTimestamp' : str(time.ctime(time.time()))}
            visitors_photo.append(photo)
            
            my_visitor_entry = {'faceId' : face_id_visitor , 'name' : visitors_name , 'phone' : phone_number_visitor , 'photo' : visitors_photo}
            dynamo_visitors_table.put_item(Item=my_visitor_entry)
            
            my_string = {'faceId' : face_id_visitor, 'otp': otp, 'expiration' : str(int(time.time() + 300))}
            dynamo_passcodes_table.put_item(Item=my_string)
        else:
            print('visitor details not present in db')
        
    return {
        'statusCode': 200,
        'body': json.dumps('processing completed!')
    }

def sendOtpToVisitor(phone_number, otp):
    
    message_visitor = "Hello, here is your one time password, "
    message_visitor += str(otp)
    smsClient.publish(PhoneNumber="+1"+phone_number,Message=message_visitor)
    
def sendMessageToOwner(phone_number, link):
    
    message_owner = "Hello, here is the link for your visitor image, "
    message_owner += str(link)
    
    smsClient.publish(PhoneNumber="+1"+phone_number,Message=message_owner)
	
def store_image(stream_name, fragmentNumber,faceId):
    s3_client = boto3.client('s3')
    rekClient=boto3.client('rekognition')
    
    kvs = boto3.client("kinesisvideo")

    endpoint = kvs.get_data_endpoint(
        APIName="GET_MEDIA_FOR_FRAGMENT_LIST",
        StreamName=stream_name
    )['DataEndpoint']
    
    print("Kinesis Data endpoint: ",endpoint)
    
    kvam = boto3.client("kinesis-video-archived-media", endpoint_url=endpoint)
    
    print(stream_name, fragmentNumber)
    
    kvs_stream = kvam.get_media_for_fragment_list(
        StreamName=stream_name,
        Fragments=[
            fragmentNumber,
        ])
        
    collectionId="smart_door_collection"
    print("KVS Stream: ",kvs_stream)
    
    with open('/tmp/stream.mkv', 'wb') as f:
        streamBody = kvs_stream['Payload'].read(1024*16384) 
        f.write(streamBody)
    
    print('reading the temp video file')
    cap = cv2.VideoCapture('/tmp/stream.mkv')
        
    total=int(count_frames_manual(cap)/2)
    cap.set(2,total);
    print(total)
    print('cap: ', cap)
    ret, frame = cap.read() 
    print('frame: ',ret,frame)
    print('writing the frame in a temp file')
    cv2.imwrite('/tmp/frame.jpg', frame)
        
    if(faceId is None):
        faceId=index_image(frame, collectionId,fragmentNumber)
            
    fileName= faceId+'-'+fragmentNumber+'.jpg'
    print('writing the file to s3')
    s3_client.upload_file(
            '/tmp/frame.jpg',
            'visitorb01', 
            fileName
        )
    cap.release()
    print('Image uploaded')
    return fileName, faceId

    
def index_image(frame, collectionId, fragmentNumber):
     
    retval, buffer = cv2.imencode('.jpg', frame)
    response=rekClient.index_faces(CollectionId=collectionId,
    Image={
    'Bytes': buffer,
    },
    ExternalImageId=fragmentNumber,
    DetectionAttributes=['ALL'])
    
    print('New Response',response)
    faceId=''
    for faceRecord in response['FaceRecords']:
        faceId = faceRecord['Face']['FaceId']

def count_frames_manual(video):
	total = 0
	while True:
		(grabbed, frame) = video.read()
		if not grabbed:
			break
		total += 1
	return total