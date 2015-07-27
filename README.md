This is out Network Access & Content Check
==========================================

* requirement
** vagrant

Instruction
============

Run the following command in vagrant
# vagrant up
# cd /vagrant/blockornot
# python server.py &
# celery -A worker.backend worker &

Might be a good idea to have 2 shell running. 

p.s I did not plan for deployment yet. I just spend half a day on this. 
