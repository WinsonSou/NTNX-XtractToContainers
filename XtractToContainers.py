#!/usr/bin/python2.7

import paramiko
import time
import os
import argparse
import cgi
import cgitb
import subprocess
import docker

"""
form = cgi.FieldStorage()
vm_ip = form.getvalue('ipaddress')
vm_username = form.getvalue('username')
vm_password = form.getvalue('password')
#containername  = form.getvalue('containername')
containertag  = form.getvalue('containertag')
dockerrepo  = form.getvalue('dockerrepo')
dockerusername = form.getvalue('dockerusername')
dockerpassword = form.getvalue('dockerpassword')
"""

def InstallBlueprintOnSourceUbuntu(vm_ip, vm_username, vm_password):
    print('DEBUG: Installing Blueprint to Remote Server')

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
        #print(output.decode('utf-8'))
        time.sleep(0.1)

    #Enable universe sources & update repos: FOR UBUNTU ONLY

    channel.send('sudo add-apt-repository universe' + '\n')
    print('DEBUG: Enabling universe sources, pause 10 secs')
    time.sleep(10) #10s wait for universe sources to be setup
    output = channel.recv(9999) #read in
    #print(output.decode('utf-8'))
    print('DEBUG: running apt update, pause 15 secs')
    channel.send('sudo apt update' + '\n')
    time.sleep(15) #15s wait for apt update to complete ### REMEMBER TO CHANGE TO 15
    output = channel.recv(9999) #read in
    #print(output.decode('utf-8'))

    #Install Python-Pip & pip install Blueprint
    print('DEBUG: Installing Python-Pip and Blueprint on Remote Server, pause 180 secs')
    channel.send('sudo apt install -y python-pip git && sudo pip install blueprint' + '\n')
    time.sleep(180) #180s wait for python-pip & blueprint to be installed ### REMEMBER TO CHANGE TO 180
    output = channel.recv(99999) #read in
    #print(output.decode('utf-8'))

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
        #print(output.decode('utf-8'))
        time.sleep(0.1)
    
    #Blueprint the Source VM
    print('DEBUG: Starting Blueprint operation')
    print('DEBUG: Configuring Git')
    channel.send('git config --global user.email "winson.sou@nutanix.com" && git config --global user.name "WinsonSou"' + '\n')#init git
    print('DEBUG: Creating tmp directories on SourceVM')
    channel.send('mkdir /tmp/blueprint && cd /tmp/blueprint' + '\n')
    print('DEBUG: Running Blueprint operation, pause 30 secs')
    channel.send('sudo blueprint create sourcevm' + '\n')
    time.sleep(30) #wait enough for blueprinting to finish
    print('DEBUG: Blueprint operation complete')
    output = channel.recv(9999) #read in
    #print(output.decode('utf-8'))

    #Generate Source VM Tarball and Bootstraper and copy locally
    print('DEBUG: Creating Bootstrapper and Tarball, pause 10 secs')
    channel.send('cd /tmp/blueprint && sudo blueprint show -S sourcevm' + '\n')
    time.sleep(10) #wait enough for tarball and boostrap to finish
    output = channel.recv(9999) #read in
    print(output.decode('utf-8')) #DEBUG#
    print('DEBUG: Creating List of installed Packages')
    channel.send('sudo blueprint show-packages sourcevm > /tmp/blueprint/sourcevm/packages.txt' + '\n')
    output = channel.recv(9999) #read in
    print('DEBUG: Tarball, Bootstrapper and Package List created, copying to XtractVM')
    print('DEBUG: Copy Phase: renaming tarball')
    channel.send('cd /tmp/blueprint/sourcevm' + '\n')
    channel.send('sudo cp *.tar sourcevm.tar' + '\n')
    channel.send('tar -cvf nginx.tar /etc/nginx/' + '\n')
    time.sleep(0.5)
    output = channel.recv(9999) #read in
    #print(output.decode('utf-8'))
    print('DEBUG: Copy Phase: Creating Local tmp directories on XtractVM')
    if not os.path.exists('/tmp/xtract'):
        os.makedirs('/tmp/xtract/')
    print('DEBUG: Copy Phase: Copying Tarball and bootstrapper to XtractVM')
    ftp.get('/tmp/blueprint/sourcevm/sourcevm.tar','/tmp/xtract/sourcevm.tar')
    ftp.get('/tmp/blueprint/sourcevm/bootstrap.sh','/tmp/xtract/bootstrap.sh')
    ftp.get('/tmp/blueprint/sourcevm/packages.txt','/tmp/xtract/packages.txt')
    ftp.get('/tmp/blueprint/sourcevm/nginx.tar','/tmp/xtract/nginx.tar')
    #ADD CLEAN UP SOURCE VM /TMP FOLDER

#def GetOSType(vm_ip, vm_username, vm_password):

def packageManager():
    print('DEBUG: Determining Packages to be Installed')
    blacklisted_packages = []
    with open('PackageBlacklistUbuntu.txt','r+') as ubuntuPackageBlacklist:
        for line in ubuntuPackageBlacklist:
            blacklisted_packages.append(line)
        ubuntuPackageBlacklist.close()

    #Preparing list of Existing Packages
    #remove 'apt '
    with open('/tmp/xtract/packages.txt', 'r') as existingPackage, open('/tmp/xtract/aptcleanpackages.txt', 'w+') as aptcleanpackages:
        for line in existingPackage:
            line = line.replace('apt ', '')
            aptcleanpackages.write(line)
        aptcleanpackages.close()
        existingPackage.close()

        #remove versions from packages
    with open('/tmp/xtract/aptcleanpackages.txt', 'r+') as aptcleanpackages, open('/tmp/xtract/versioncleanpackages.txt', 'w+') as versioncleanpackages:
        for line in aptcleanpackages:
            seperator = ' '
            line = line.split(seperator, 1)[0]
            versioncleanpackages.write(line + '\n')    
        aptcleanpackages.close()
        versioncleanpackages.close()

    #remove blacklisted packages
    with open('/tmp/xtract/versioncleanpackages.txt', 'r+') as versioncleanpackages, open('/tmp/xtract/packagesToBeInstalled.txt', 'a+') as packagesToBeInstalled:
        for line in versioncleanpackages:
            if not any(blacklisted in line for blacklisted in blacklisted_packages):
                packagesToBeInstalled.write(line)
        versioncleanpackages.close()
        packagesToBeInstalled.close()
    print('DEBUG: Determining Packages to be Installed: Completed')
    

""" def filesystemManager():
    with open('/tmp/xtract/packagesToBeInstalled.txt', 'a+') as packagesToBeInstalled:
        for line in packagesToBeInstalled:
            if 

 """
def BuildDockerFile():
    print('DEBUG: Building Dockerfile')    
    
    if os.path.isfile('/tmp/xtract/Dockerfile'):
        print('DEBUG: Building Dockerfile: Existing Dockerfile Exists, Deleting and Recreating')
        os.remove('/tmp/xtract/Dockerfile')
        df = open('/tmp/xtract/Dockerfile','a+')
        df.write('FROM %s \r\n' % ('ubuntu:18.04')) # sets a base image for the Container
        df.write('ADD %s \r\n' % ('. .')) #Adds Tarball and Boostrapper and Package Requirements into Container
        df.write('RUN %s \r\n' % ('apt-get update && cat packagesToBeInstalled.txt | xargs apt-get install -y --no-install-recommends')) #Executes Bootstrapper in Container
        df.write('RUN %s \r\n' % ('mkdir -p "/usr/local" && tar xf "sourcevm.tar" -C "/usr/local" && tar xf "nginx.tar" -C "/"')) #Replaces filesystem in container with sourcevm filesystem
        #df.write('RUN %s \r\n' % ('npm install forever -g')) #Installs Forever
        df.write('WORKDIR %s \r\n' % ('/usr/local/www/html'))
        #df.write('RUN %s \r\n' % ('npm build && forever start server.js'))
        df.write('EXPOSE %s \r\n' % ('80'))
        df.write('CMD %s \r\n' % ('["nginx", "-g", "daemon off;"]'))
        df.close()

    elif not os.path.isfile('/tmp/xtract/Dockerfile'):
        print('DEBUG: Building Dockerfile: No Dockerfile Exists, Creating New Dockerfile')
        df = open('/tmp/xtract/Dockerfile','a+')
        df.write('FROM %s \r\n' % ('ubuntu:18.04')) # sets a base image for the Container
        df.write('ADD %s \r\n' % ('. .')) #Adds Tarball and Boostrapper and Package Requirements into Container
        df.write('RUN %s \r\n' % ('apt-get update && cat packagesToBeInstalled.txt | xargs apt-get install -y --no-install-recommends')) #Executes Bootstrapper in Container
        df.write('RUN %s \r\n' % ('mkdir -p "/usr/local" && tar xf "sourcevm.tar" -C "/usr/local" && tar xf "nginx.tar" -C "/"')) #Replaces filesystem in container with sourcevm filesystem
        #df.write('RUN %s \r\n' % ('npm install forever -g')) #Installs Forever
        df.write('WORKDIR %s \r\n' % ('/usr/local/www/html'))
        #df.write('RUN %s \r\n' % ('npm build && forever start server.js'))
        df.write('EXPOSE %s \r\n' % ('80'))
        df.write('CMD %s \r\n' % ('["nginx", "-g", "daemon off;"]'))
        df.close()
    print('DEBUG: Building Dockerfile: Completed')

def BuildContainer(ctag, drepo, dusername, dpassword):
    imagetag = 'docker.io/' + dusername + '/' + drepo + ':' + ctag
    print('Image Tag of Container is: ' + imagetag)
    print('DEBUG: Building Container from Dockerfile')
    client = docker.from_env()
    output = client.images.build(path='/tmp/xtract/',tag=imagetag)
    print('DEBUG: Pushing Container into DockerHub')
    output = client.login(username=dusername, password=dpassword)
    output = client.images.push(repository=imagetag)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Xtract for Containers')
    parser.add_argument('vm_ip', help='IP Address of the VM')
    parser.add_argument('vm_username', help='Username of the VM')
    parser.add_argument('vm_password', help='Password of the VM')
    parser.add_argument('containertag', help='Tag of the Container')
    parser.add_argument('dockerrepo', help='Docker Repo')
    parser.add_argument('dockerusername', help='Dockerhub Username')
    parser.add_argument('dockerpassword', help='Dockerhub Password')

    args = parser.parse_args()

    InstallBlueprintOnSourceUbuntu(args.vm_ip, args.vm_username, args.vm_password)
    BlueprintSourceVM(args.vm_ip, args.vm_username, args.vm_password)
    packageManager()
    BuildDockerFile()
    BuildContainer(args.containertag, args.dockerrepo, args.dockerusername, args.dockerpassword)
