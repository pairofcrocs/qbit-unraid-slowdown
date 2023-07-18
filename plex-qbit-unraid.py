import os
import paramiko
import requests
import re

from qbittorrentapi import Client as qbitClient
from dotenv import load_dotenv

load_dotenv()
UNRAID_IP = os.environ['UNRAID_IP']
PLEX_TOKEN = os.environ['PLEX_TOKEN']
PLEX_PORT = os.environ['PLEX_PORT']
QBIT_PORT = os.environ['QBIT_PORT']
QBIT_USERNAME = os.environ['QBIT_USERNAME']
QBIT_PASSWORD = os.environ['QBIT_PASSWORD']
UNRAID_USERNAME = os.environ['UNRAID_USERNAME']
UNRAID_PASSWORD = os.environ['UNRAID_PASSWORD']

STATUS_COMMAND = 'parity.check status'
PAUSE_COMMAND = 'parity.check pause'
RESUME_COMMAND = 'parity.check resume'

ACTIVE_STREAM_EXPRESSION = re.compile(r'<MediaContainer size="(\d+)"')

## send ssh command
def sendSSHCommand(unraidHostname: str, unraidUser: str, unraidPass: str, command: str) -> str:
    ## create ssh client
    with paramiko.SSHClient() as ssh:
        ## add host key policy
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ## connect to server
            ssh.connect(unraidHostname, username=unraidUser, password=unraidPass)
            ## execute command
            stdin, stdout, stderr = ssh.exec_command(command)
            ## return output
            return stdout.read().decode().strip()
        except paramiko.AuthenticationException:
            print('Authentication failed')
        except paramiko.SSHException as ssh_exception:
            print('SSH connection failed:', str(ssh_exception))
        except paramiko.Exception as e:
            print('Error:', str(e))

## get amount of plex streams
def getActiveStreams(plexHost: str, plexToken: str) -> int:
    headers = {
        'Accept': 'application/xml',
        'X-Plex-Token': plexToken
    }
    resp = requests.get(plexHost, headers=headers)

    if resp.status_code == 200:
        data = resp.text
        active_streams = ACTIVE_STREAM_EXPRESSION.findall(data)

        if active_streams:
            return int(active_streams[0])
        else:
            return 0
    else:
        print('Error occurred while fetching active streams:', resp.status_code)
        return None

## get qbit speed mode
def getQbitSpeed(qbitHost: str, qbitUser: str, qbitPass: str) -> None:
    qbit = qbitClient(host=qbitHost)
    ## authenticate unraid
    qbit.auth_log_in(username=qbitUser, password=qbitPass)
    ## send limit state
    return qbit.transfer_speed_limits_mode()

## change qbit speed
def limitQbitSpeed(qbitHost: str, qbitUser: str, qbitPass: str, limitSpeed: bool = True) -> None:
    ## login
    qbit = qbitClient(host=qbitHost)
    ## authenticate unraid
    qbit.auth_log_in(username=qbitUser, password=qbitPass)
    ## send limit state
    return qbit.transfer_setSpeedLimitsMode(intended_state=limitSpeed)

## parse status message to int
def parseParityStatus(status: str) -> int:
    ## check if parity is in progress
    if status == 'Status: No array operation currently in progress':
        return 1
    if 'Correcting Parity-Check' in status:
        return 0
    return -1

if __name__ == '__main__':
    plexHost = f'http://{UNRAID_IP}:{PLEX_PORT}/status/sessions'
    qbitHost = f'{UNRAID_IP}:{QBIT_PORT}'

    activeStreams = getActiveStreams(plexHost, PLEX_TOKEN)
    qbitSpeed = getQbitSpeed(qbitHost, QBIT_USERNAME, QBIT_PASSWORD)
    parityStatus = sendSSHCommand(UNRAID_IP, UNRAID_USERNAME, UNRAID_PASSWORD, STATUS_COMMAND)
    parityState = parseParityStatus(parityStatus)

    print('------------------------------')
    print('Starting Script...')
    print('------------------------------')
    print(f'Number of active streams: {activeStreams}')
    print(f'qBittorrent Speed Mode: {qbitSpeed}')
    print(f'Parity Check Status: {parityState} ({parityStatus})')
    print('------------------------------')
    print('Sending signals...')
    print('------------------------------')

    ## active stream
    ## slow qbit and pause parity check
    if activeStreams > 0:
        print('Slowing Qbit down...')
        limitQbitSpeed(qbitHost, QBIT_USERNAME, QBIT_PASSWORD, limitSpeed=True)
        
        if parityState == 0:
            print('Pausing parity check...')
            sendSSHCommand(UNRAID_IP, UNRAID_USERNAME, UNRAID_PASSWORD, PAUSE_COMMAND)
    ## inactive stream
    ## speed qbit back up and resume parity check
    else:
        print('Speeding Qbit back up...')
        limitQbitSpeed(qbitHost, QBIT_USERNAME, QBIT_PASSWORD, limitSpeed=False)
        
        if parityState == 0:
            print('Resuming parity check...')
            sendSSHCommand(UNRAID_IP, UNRAID_USERNAME, UNRAID_PASSWORD, RESUME_COMMAND)
    
    activeStreams = getActiveStreams(plexHost, PLEX_TOKEN)
    qbitSpeed = getQbitSpeed(qbitHost, QBIT_USERNAME, QBIT_PASSWORD)
    parityStatus = sendSSHCommand(UNRAID_IP, UNRAID_USERNAME, UNRAID_PASSWORD, STATUS_COMMAND)
    parityState = parseParityStatus(parityStatus)

    print('------------------------------')
    print(f'Number of active streams: {activeStreams}')
    print(f'qBittorrent Speed Mode: {qbitSpeed}')
    print(f'Parity Check Status: {parityState} ({parityStatus})')
    print('------------------------------')
    print('Done!')
    print('------------------------------')
