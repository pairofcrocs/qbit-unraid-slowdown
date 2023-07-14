# qBit/unRaid Slowdown

This script is designed to automate the management of a Plex media server, qBittorrent client, and an Unraid server. It checks the number of active streams on the Plex server and adjusts the speed mode of the qBittorrent client accordingly. It also provides functionality to pause or resume a parity check operation on the Unraid server.

## Prerequisites

Before using this script, make sure you have the following:

 - 'Parity Check Tuning' plugin by Dave Walker (itimpi)
 - Tautulli docker container by JonnyWong16
 - The required Python packages installed: `requests`, `re`, `qbittorrentapi`, `paramiko`. (create a user script that runs at the start of the array with the following: `docker exec tautulli pip install requests qbittorrentapi`)

## Setup

1.  Clone or download the script to your script folder in `/appdata/Tautulli/scripts/plex-qbit-unraid.py`
    
2.  Change the values in the script with login details for your set up.
3. Make sure you have `Use increments for manual Parity Check` and `Use increments for scheduled Parity Check` set to YES in the 'Parity Check Tuning' plugin. You can also set `Use increments for automatic Parity Check` to yes, but it's not recommenced.
![parity check settings](https://i.imgur.com/gsk4Auu.png)
5. Set up a new Script in Tautulli with only the triggers of `Playback Start` and `Playback Stop` and save.
![tautulli settings](https://i.imgur.com/NdVRjmZ.png)

After that, you should be good to go!

Now, every time something is started or stopped in Plex, the script will check if anyone is watching and slowdown qBittorrent/pause a parity check or speedup qBittorrent and resume parity check. This will only happen when there are 0 people steaming.
