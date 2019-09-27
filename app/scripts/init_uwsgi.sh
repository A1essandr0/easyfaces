#!/usr/bin/env bash

chown www-data /tmp 
chown www-data /apps/easyfaces/instance/imageapp.sqlite
chown www-data /apps/easyfaces/instance
chown www-data /apps/easyfaces/imageapp/static

uwsgi --emperor /apps-conf --uid www-data --gid www-data --master
