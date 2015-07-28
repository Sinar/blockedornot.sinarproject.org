This is out Network Access & Content Check
==========================================

* requirement
  * vagrant

Instruction
============

Run the following command in vagrant
* vagrant up
* cd /vagrant/blockornot
* python server.py &
* celery -A worker.backend worker &

Note
=====
currently the celery daemon is run manually, all http worker on each server will listen to 1 queue. 

The frontend will send task to each queue as they request for http test. So the celery daemon on server different that 
one where this app is run need to assign to a queue manually. The name of queue is "<location name>_<isp>" with small case
and space replaced with _. so worker running on TM in Subang Jaya will listen to queue  subang_jaya_tm.  

Might be a good idea to have 2 shell running. 

p.s I did not plan for deployment yet. I just spend half a day on this. 
