import requests
import json
from settings import access_token, service_url

filepath = 'imageapp/static/image15.jpg'

headers = {'Ocp-Apim-Subscription-Key': access_token, 'Content-Type': 'application/octet-stream'}
params = {
    'returnFaceId': 'true',
    'returnFaceLandmarks': 'false',
    'returnFaceAttributes': 'age,gender,headPose,smile,facialHair,glasses,emotion,hair',
}
binary_file = open(filepath, 'rb')
response = requests.post(service_url, params=params,
                         headers=headers, data=binary_file)

coordinates = []
for face_record in response.json():
    x1 = face_record['faceRectangle']['left']
    y1 = face_record['faceRectangle']['top']
    x2 = x1 + face_record['faceRectangle']['width']
    y2 = y1 + face_record['faceRectangle']['height']
    coordinates.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
print(coordinates)
