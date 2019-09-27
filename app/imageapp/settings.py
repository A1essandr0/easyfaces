import os

imgbank = 'imageapp/static/'
allowed_extensions = ('jpeg', 'jpg')

access_token = os.getenv('AZURE_ACCESS_TOKEN')
service_url = os.getenv('AZURE_SERVICE_URL')
