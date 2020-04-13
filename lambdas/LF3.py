import json
import boto3

dynamo_resource = boto3.resource('dynamodb')
dynamo_visitors_table = dynamo_resource.Table("visitors")
dynamo_passcodes_table = dynamo_resource.Table("passcodes")


def lambda_handler(event, context):
    
    visitors_provided_otp = event['message']['otp']     
    passcodes_response = dynamo_passcodes_table.scan()
    otps = []
    
    otp_faceid_dict = {}
    
    for i in range(len(passcodes_response['Items'])):
        otp_faceid_dict[passcodes_response['Items'][i]['otp']] = passcodes_response['Items'][i]['faceid']
    
    
    if visitors_provided_otp in otp_faceid_dict.keys():
        print("Give access to visitor")       
        key = {'faceid' : otp_faceid_dict[visitors_provided_otp]}   
        visitors_response = dynamo_visitors_table.get_item(Key=key)
        visitors_name = visitors_response['Item']['name']
        visitors_phone = visitors_response['Item']['phone']
        
        return visitors_name
    else:  
        return "false"
    
    
    print(otp_faceid_dict)
    