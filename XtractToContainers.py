#!/usr/bin/python2.7

import paramiko
import time
import os
import argparse

def InstallBlueprintOnSourceUbuntu(vm_ip, vm_username, vm_password):
    print('DEBUG: Installing Blueprint to Remote Server')
    ''' 
    #For Debugging
    vm_ip='10.139.76.160'
    vm_username='ubuntu'
    vm_password='nutanix/4u' 
    '''

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=vm_ip,username=vm_username,password=vm_password)
    channel = ssh.invoke_shell()

    #Use this to clear welcome banner
    time.sleep(1) 
    channel.recv(9999)
    channel.send("\n")
    time.sleep(1)

    #Enter sudo mode for all commands run from here on out: FOR UBUNTU ONLY!
    print('DEBUG: Entering sudo mode')
    sudo_cmds = ['sudo su -', vm_password, 'whoami']
    for sudo_cmd in sudo_cmds:
        channel.send(sudo_cmd + '\n')
        while not channel.recv_ready(): #Wait for the server to read and respond
            time.sleep(1)
        time.sleep(1) #wait enough for writing to (hopefully) be finished
        output = channel.recv(9999) #read in
        print(output.decode('utf-8'))
        time.sleep(0.1)

    #Enable universe sources & update repos: FOR UBUNTU ONLY

    channel.send('sudo add-apt-repository universe' + '\n')
    print('DEBUG: Enabling universe sources, pause 10 secs')
    time.sleep(10) #10s wait for universe sources to be setup
    output = channel.recv(9999) #read in
    print(output.decode('utf-8'))
    print('DEBUG: running apt update, pause 15 secs')
    channel.send('sudo apt update' + '\n')
    time.sleep(1) #15s wait for apt update to complete ### REMEMEBER TO CHANGE TO 15
    output = channel.recv(9999) #read in
    print(output.decode('utf-8'))

    #Install Python-Pip & pip install Blueprint
    print('DEBUG: Installing Python-Pip and Blueprint on Remote Server, pause 180 secs')
    channel.send('sudo apt install -y python-pip git && sudo pip install blueprint' + '\n')
    time.sleep(1) #180s wait for python-pip & blueprint to be installed ### REMEMEBER TO CHANGE TO 180
    output = channel.recv(99999) #read in
    print(output.decode('utf-8'))

    channel.close()

def BlueprintSourceVM(vm_ip, vm_username, vm_password):
    print('DEBUG: Blueprinting Source Server')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=vm_ip,username=vm_username,password=vm_password)
    channel = ssh.invoke_shell()
    ftp = ssh.open_sftp()

    #Use this to clear welcome banner
    time.sleep(1) 
    channel.recv(9999)
    channel.send("\n")
    time.sleep(1)

    #Enter sudo mode for all commands run from here on out: FOR UBUNTU ONLY!
    print('DEBUG: Entering sudo mode')
    sudo_cmds = ['sudo su -', vm_password, 'whoami']
    for sudo_cmd in sudo_cmds:
        channel.send(sudo_cmd + '\n')
        while not channel.recv_ready(): #Wait for the server to read and respond
            time.sleep(1)
        time.sleep(1) #wait enough for writing to (hopefully) be finished
        output = channel.recv(9999) #read in
        print(output.decode('utf-8'))
        time.sleep(0.1)
    
    #Blueprint the Source VM
    print('DEBUG: Starting Blueprint operation')
    print('DEBUG: Configuring Git')
    channel.send('git config --global user.email "winson.sou@nutanix.com" && git config --global user.name "WinsonSou"' + '\n')#init git
    print('DEBUG: Creating tmp directories on SourceVM')
    channel.send('mkdir /tmp/blueprint && cd /tmp/blueprint' + '\n')
    print('DEBUG: Running Blueprint operation, pause 15 secs')
    channel.send('sudo blueprint create sourcevm' + '\n')
    time.sleep(15) #wait enough for blueprinting to finish
    print('DEBUG: Blueprint operation complete')
    output = channel.recv(9999) #read in
    print(output.decode('utf-8'))
    time.sleep(0.1)

    #Generate Source VM Tarball and Bootstraper and copy locally
    print('DEBUG: Creating Bootstrapper and Tarball, pause 5 secs')
    channel.send('sudo blueprint show -S sourcevm' + '\n')
    time.sleep(5) #wait enough for tarball and boostrap to finish
    output = channel.recv(9999) #read in
    print(output.decode('utf-8'))
    print('DEBUG: Tarball and Bootsrapper created, copying to master')
    print('DEBUG: Copy Phase: renaming tarball')
    channel.send('cd /tmp/blueprint/sourcevm' + '\n')
    channel.send('sudo cp *.tar sourcevm.tar' + '\n')
    time.sleep(0.5)
    output = channel.recv(9999) #read in
    print(output.decode('utf-8'))
    print('DEBUG: Copy Phase: Creating Local tmp directories on master')
    if not os.path.exists('/tmp/xtract'):
        os.makedirs('/tmp/xtract/')
    print('DEBUG: Copy Phase: Copying Tarball and bootstrapper to master')
    ftp.get('/tmp/blueprint/sourcevm/sourcevm.tar','/tmp/xtract/sourcevm.tar')
    ftp.get('/tmp/blueprint/sourcevm/bootstrap.sh','/tmp/xtract/bootstrap.sh')
    #ADD CLEAN UP SOURCE VM /TMP FOLDER

#def BuildDockerFile():
    #echo true

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Xtract for Containers')
    parser.add_argument('vm_ip', help='IP Address of the VM')
    parser.add_argument('vm_username', help='Username of the VM')
    parser.add_argument('vm_password', help='Password of the VM')
    
    args = parser.parse_args()
    InstallBlueprintOnSourceUbuntu(args.vm_ip, args.vm_username, args.vm_password)
    BlueprintSourceVM(args.vm_ip, args.vm_username, args.vm_password)






