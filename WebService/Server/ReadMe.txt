## Install Instructions for the AquaPointe Daemon
##

## Install the following files to /usr/bin
##
aquapointed.py
daemon.py 

## Install the following files to /usr/local/AquaPointe/config
##
config.db

## Ensure the files are executable
##

chmod 755 aquapointed.py
chmod 755 daemon.py 

## Add the following line to /etc/rc.local after
## the boot-complete-notify entry
##

aquapointed.py start

## The log file for the dameon is in /var/log/aquapointed.log
##

## To stop the daemon run the following command
##

aquapointed.py stop