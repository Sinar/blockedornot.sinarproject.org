#!/usr/bin/env sh
apt-get update
apt-get install -y redis-server python-setuptools python-dev postgresql postgresql-server-dev-all python-pip \
    build-essential postgresql-contrib
pip install -r requirement.txt
sudo -u postgres psql -c "create database blockedornot"
sudo -u postgres psql -c "create user blockedornot with password 'password'"
sudo -u postgres psql -c "grant all privileges on database blockedornot to blockedornot"
sudo -u postgres psqckendl blockedornot -c "create extension hstore"