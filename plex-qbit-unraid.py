import os
import paramiko
import requests
import re
import time

from dotenv import load_dotenv
from qbittorrentapi import Client as qbitClient
from qbittorrentapi.exceptions import APIConnectionError

load_dotenv()
UNRAID_IP = os.environ['UNRAID_IP']
PLEX_TOKEN = os.environ['PLEX_TOKEN']
PLEX_PORT = os.environ['PLEX_PORT']
QBIT_PORT = os.environ['QBIT_PORT']
QBIT_USERNAME = os.environ['QBIT_USERNAME']
QBIT_PASSWORD = os.environ['QBIT_PASSWORD']
UNRAID_USERNAME = os.environ['UNRAID_USERNAME']
UNRAID_PASSWORD = os.environ['UNRAID_PASSWORD']

PARITY_STATUS_COMMAND = 'parity.check status'
PAUSE_PARITY_COMMAND = 'parity.check pause'
RESUME_PARITY_COMMAND = 'parity.check resume'
START_MOVER_COMMAND = 'mover'
STOP_MOVER_COMMAND = 'mover stop'

ACTIVE_STREAM_EXPRESSION = re.compile(r'<MediaContainer size="(\d+)"')
DEFAULT_MOVER_FILE_NAME = 'mover.status'

## write status file for interrupt
def writeStatusFile(interrupted: bool, fileLocation: str = DEFAULT_MOVER_FILE_NAME) -> int:
    with open(fileLocation, 'w') as f:
        f.write('1' if interrupted else '0')
    return 1

## read status file for interrupt
def readStatusFile(fileLocation: str = DEFAULT_MOVER_FILE_NAME) -> int:
    try:
        with open(fileLocation, 'r') as f:
            return int(f.read())
    except FileNotFoundError:
        return 0

## send ssh command
def sendSSHCommand(unraidHostname: str, unraidUser: str, unraidPass: str, command: str, waitForOutput: bool = True) -> str:
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
            if waitForOutput:
                return stdout.read().decode().strip()
        except paramiko.AuthenticationException:
            print('Authentication failed')
        except paramiko.SSHException as ssh_exception:
            print('SSH connection failed:', str(ssh_exception))
        except paramiko.Exception as e:
            print('Error:', str(e))
    return ''

## stop mover and write to file
def stopMover(unraidHostname: str, unraidUser: str, unraidPass: str) -> int:
    ## stop mover
    moverStatus = sendSSHCommand(unraidHostname, unraidUser, unraidPass, STOP_MOVER_COMMAND)
    ## write to file if mover was stopped
    if 'mover: not running' not in moverStatus:
        return writeStatusFile(interrupted=True)
    return 0
    
## resume mover if mover was interrupted
def resumeMover(unraidHostname: str, unraidUser: str, unraidPass: str) -> int:
    moverStatus = readStatusFile()
    if moverStatus == 1:
        sendSSHCommand(unraidHostname, unraidUser, unraidPass, START_MOVER_COMMAND, waitForOutput=False)
        writeStatusFile(interrupted=False)
    return moverStatus

## get amount of plex streams
def getActiveStreams(plexHost: str, plexToken: str) -> int:
    headers = {
        'Accept': 'application/xml',
        'X-Plex-Token': plexToken
    }
    resp = requests.get(plexHost, headers=headers)

    if resp.status_code == 200:
        active_streams = ACTIVE_STREAM_EXPRESSION.findall(resp.text)

        if active_streams:
            return int(active_streams[0])
        return 0
    
    print('Error occurred while fetching active streams:', resp.status_code)
    return None

## change qbit speed
def limitQbitSpeed(qbitHost: str, qbitUser: str, qbitPass: str, limitSpeed: bool = True) -> int:
    ## login
    qbit = qbitClient(host=qbitHost)
    ## authenticate unraid
    try:
        qbit.auth_log_in(username=qbitUser, password=qbitPass)
    except APIConnectionError:
        return -1
    ## send limit state
    qbit.transfer_setSpeedLimitsMode(intended_state=limitSpeed)
    return 1 if limitSpeed else 0

## parse status message to int
def parseParityStatus(status: str) -> int:
    ## check if parity is in progress
    if status == 'Status: No array operation currently in progress':
        return -1
    if 'PAUSED' in status:
        return 0
    if 'Correcting Parity-Check' in status:
        return 1

if __name__ == '__main__':
    plexHost = f'http://{UNRAID_IP}:{PLEX_PORT}/status/sessions'
    qbitHost = f'{UNRAID_IP}:{QBIT_PORT}'

    activeStreams = getActiveStreams(plexHost, PLEX_TOKEN)

    print('------------------------------')
    print('Starting Script...')
    print('------------------------------')
    print(f'Number of active streams: {activeStreams}')
    print('------------------------------')

    ## active stream
    ## slow qbit, pause parity check, and stop mover if moving
    if activeStreams > 0:
        print('Slowing Qbit down...')
        if limitQbitSpeed(qbitHost, QBIT_USERNAME, QBIT_PASSWORD, limitSpeed=True) == 1:
            print("Successfully limited Qbit's speed")
        else:
            print("Problem limiting Qbit's speed - Check if Qbit is running and that the credentials are correct")
        
        print('------------------------------')
        
        print('Attempting to pause parity check...')
        sendSSHCommand(UNRAID_IP, UNRAID_USERNAME, UNRAID_PASSWORD, PAUSE_PARITY_COMMAND)
        
        parityStatus = parseParityStatus(sendSSHCommand(UNRAID_IP, UNRAID_USERNAME, UNRAID_PASSWORD, PARITY_STATUS_COMMAND))
        if parityStatus == 0:
            print('Successfully paused parity check')
        elif parityStatus == -1:
            print('Parity check was not running')
        else:
            print('Problem stopping parity check')
        
        print('------------------------------')
            
        print('Attemping to stop mover...')
        if stopMover(UNRAID_IP, UNRAID_USERNAME, UNRAID_PASSWORD) == 1:
            print('Mover was stopped')
        else:
            print('Mover was not running')
    ## inactive stream
    ## speed qbit back up, resume parity check, and start mover if interrupted
    else:
        print('Speeding Qbit back up...')
        if limitQbitSpeed(qbitHost, QBIT_USERNAME, QBIT_PASSWORD, limitSpeed=False) == 0:
            print("Successfully removed limit on Qbit's speed")
        else:
            print("Problem removing the limit on Qbit's speed - Check if Qbit is running and that the credentials are correct")
            
        print('------------------------------')
        
        print('Attempting to resume parity check...')
        sendSSHCommand(UNRAID_IP, UNRAID_USERNAME, UNRAID_PASSWORD, RESUME_PARITY_COMMAND)
        time.sleep(1) ## this is to prevent checking the status before parity check starts
        
        parityStatus = parseParityStatus(sendSSHCommand(UNRAID_IP, UNRAID_USERNAME, UNRAID_PASSWORD, PARITY_STATUS_COMMAND))
        if parityStatus == 1:
            print('Successfully resumed parity check')
        elif parityStatus == -1:
            print('Parity check was not running')
        else:
            print('Problem resuming parity check')
        
        print('------------------------------')
        
        print('Attemping to resume mover...')
        if resumeMover(UNRAID_IP, UNRAID_USERNAME, UNRAID_PASSWORD) == 1:
            print('Mover has resumed moving')
        else:
            print('Mover was not interrupted previously so mover was not started')

    print('------------------------------')
    print('Done!')
    print('------------------------------')