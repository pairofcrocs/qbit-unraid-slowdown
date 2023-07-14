import requests
import re
import qbittorrentapi
import paramiko

####################################################################

PLEX_TOKEN = 'REPLACE'  # Replace with your Plex token
PLEX_HOST = 'http://REPLACE:32400/status/sessions'
QBITTORRENT_HOST = 'REPLACE:8080'
USERNAME = 'admin'
PASSWORD = 'password'

# Replace the following values with your Unraid server details
hostname = 'REPLACE'
username = 'REPLACE'
password = 'REPLACE'

####################################################################

status_command = 'parity.check status'
pause_command = 'parity.check pause'
resume_command = 'parity.check resume'

#check status of parity check
def send_ssh_command(hostname, username, password, status_command):
    # Create SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the server
        client.connect(hostname, username=username, password=password)

        # Execute the command
        stdin, stdout, stderr = client.exec_command(status_command)

        # Read the command output
        output = stdout.read().decode()

        # Close the connection
        client.close()

        return output.strip()  # Return the output with leading/trailing whitespace removed
    except paramiko.AuthenticationException:
        print("Authentication failed")
    except paramiko.SSHException as ssh_exception:
        print("SSH connection failed:", str(ssh_exception))
    except paramiko.Exception as e:
        print("Error:", str(e))

#get amount of streams from plex
def get_active_streams(PLEX_TOKEN):
    headers = {
        'Accept': 'application/xml',
        'X-Plex-Token': PLEX_TOKEN
    }
    response = requests.get(PLEX_HOST, headers=headers)

    if response.status_code == 200:
        data = response.text
        active_streams = re.findall(r'<MediaContainer size="(\d+)"', data)

        if active_streams:
            return int(active_streams[0])
        else:
            return 0
    else:
        print('Error occurred while fetching active streams:', response.status_code)
        return None
active_streams1 = get_active_streams(PLEX_TOKEN)

#get speed mode from qbit
def check_speed_limits_mode():
    from qbittorrentapi import Client
    client = Client(host=QBITTORRENT_HOST, username=username, password=password)
    client.auth_log_in(username=username, password=password)
    transfer_info = client.transfer_speed_limits_mode()
    return transfer_info
check_speed_limits_mode()
transfer_info = check_speed_limits_mode()

#####################################################

#slows qbit
def qbit_slowdown():
    from qbittorrentapi import Client
    client = Client(host=QBITTORRENT_HOST, username=username, password=password)
    client.auth_log_in(username=username, password=password)
    speedset = client.transfer_setSpeedLimitsMode(intended_state=True)

#speed up qbit
def qbit_speedup():
    from qbittorrentapi import Client
    client = Client(host=QBITTORRENT_HOST, username=USERNAME, password=PASSWORD)
    client.auth_log_in(username=USERNAME, password=PASSWORD)
    speedset = client.transfer_setSpeedLimitsMode(intended_state=False)

#pause parity check
def send_pause_command(hostname, username, password, pause_command):
    # Create SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the server
        client.connect(hostname, username=username, password=password)

        # Execute the command
        stdin, stdout, stderr = client.exec_command(pause_command)

        # Close the connection
        client.close()
    except paramiko.AuthenticationException:
        print("Authentication failed")
    except paramiko.SSHException as ssh_exception:
        print("SSH connection failed:", str(ssh_exception))
    except paramiko.Exception as e:
        print("Error:", str(e))

#resume parity check
def send_resume_command(hostname, username, password, resume_command):
    # Create SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the server
        client.connect(hostname, username=username, password=password)

        # Execute the command
        stdin, stdout, stderr = client.exec_command(resume_command)

        # Close the connection
        client.close()
    except paramiko.AuthenticationException:
        print("Authentication failed")
    except paramiko.SSHException as ssh_exception:
        print("SSH connection failed:", str(ssh_exception))
    except paramiko.Exception as e:
        print("Error:", str(e))


#status_command output
command_output = send_ssh_command(hostname, username, password, status_command)


#checks to see if parity check is in progress
if command_output == "Status: No array operation currently in progress":
    status_variable = 1
elif "Correcting Parity-Check" in command_output:
    status_variable = 0
else:
    status_variable = -1

#sets print value for parity status
if status_variable == 1:
    parity_status = "Resuming..."
if status_variable == 0:
    parity_status = "Pausing..."

#prints status ()
print("Number of active streams:", active_streams1)
print("qBittorrent Speed Mode:", transfer_info)
print("Parity Check Status:", parity_status)

#if no streams, speed up
if active_streams1 == 0:
    qbit_speedup()
    print("qBittorrent Speed Up")
    
    if status_variable == 0:
        send_resume_command(hostname, username, password, resume_command)
        print("Resuming Parity Check")

#if people are streaming, slow down
if active_streams1 > 0:
    qbit_slowdown()
    print("Qbittorrent Slowed Down..." )

    if status_variable == 0:
        send_pause_command(hostname, username, password, pause_command)
        print("Pausing Parity Check")


