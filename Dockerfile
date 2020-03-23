FROM python

ENV FLASK_APP=imageapp
ENV FLASK_SECRET_KEY=cadabra_abra

# You can use it, it's ok
ENV AZURE_ACCESS_TOKEN=de4d1818166b4185ae6a56889ff960a4
ENV AZURE_SERVICE_URL=https://easyface.cognitiveservices.azure.com/face/v1.0/detect

RUN mkdir /apps-conf
RUN mkdir /apps
COPY requirements.txt /apps-conf
RUN pip3 install -r /apps-conf/requirements.txt

COPY /app /apps/easyfaces
COPY config/easyfaces.ini /apps-conf

EXPOSE 5000
CMD bash /apps/easyfaces/scripts/init_uwsgi.sh
