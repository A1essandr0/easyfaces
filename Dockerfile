FROM python

ENV FLASK_APP=imageapp
ENV FLASK_SECRET_KEY=f4443rff2ffv
ENV AZURE_ACCESS_TOKEN=de4d1818166b4185ae6a56889ff960a4
ENV AZURE_SERVICE_URL=https://easyface.cognitiveservices.azure.com/face/v1.0/detect

COPY requirements.txt /apps-conf
RUN pip3 install -r /apps-conf/requirements.txt

RUN mkdir /apps-conf
RUN mkdir /apps
COPY /app /apps/easyfaces
COPY config/easyfaces.ini /apps-conf

EXPOSE 5000
CMD bash /apps/easyfaces/scripts/init_uwsgi.sh
