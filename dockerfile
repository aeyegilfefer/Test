FROM 541767400186.dkr.ecr.us-east-2.amazonaws.com/python:3.6.8
MAINTAINER gil@aeyehealth.com
USER root

COPY . /app
WORKDIR /app

RUN apt-get clean && apt-get -y update
RUN apt-get install -y openssh-server
RUN apt-get install sudo
RUN yes | cp -rf ./sudoers /etc/sudoers

RUN apt-get install -y supervisor

RUN apt-get -y install nginx
RUN pip install -r requirements.txt --src /usr/local/src
RUN apt-get install -y libgtk2.0-dev

COPY nginx.conf /etc/nginx
RUN chmod +x ./start.sh

RUN mkdir -p /var/log/aeyelogs
RUN mkdir -p /var/log/aeyelogs/filters

ADD supervisord.conf /etc/supervisor/conf.d/supervisord.conf
EXPOSE 5000
ENTRYPOINT ["/usr/bin/supervisord"]
