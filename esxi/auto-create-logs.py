#!/bin/python3
#
# Written by Manuel Moser (moserm)

import threading, subprocess
import select, os, sys, datetime, urllib.request
from argparse import ArgumentParser


# Parsing command-line arguments
parser = ArgumentParser()

argGrpMain = parser.add_argument_group('Required parameters')
argGrpMain.add_argument('-m', '--logmessage', metavar='LOGMESSAGE', dest='logmsg', nargs='?', required=True,
	help='log message to listen for')
argGrpMain.add_argument('-f', '--logfile', metavar='/path/to/logfile/', dest='logFile', nargs='?', required=True,
	help='log file to listen on')
argGrpMain.add_argument('-w', '--workingdir', metavar='WORKINGDIR', dest='workingDir', nargs='?', required=True,
	help='working directory to save the vm-support bundle in')

argGrpRemoteHosts = parser.add_argument_group('Remote hosts')
argGrpRemoteHosts.add_argument('-r', '--remotehosts', metavar='FQDN', dest='rhosts', nargs='+', required=False, default=False,
	help='list of remote hosts to collect log bundles from')
argGrpRemoteHosts.add_argument('-p', '--password', metavar='PASSWORD', dest='password', required=False,
	help='root password for the remote hosts')

parser.add_argument('-d', '--hostd', dest='hostd', required=False, default=False, action='store_true',
	help='Generate a hostd coredump before collecting the log bundle. This only works for the log bundle of the local host on which this script is executed.')

args = parser.parse_args()


#
## Functions
#
def trigger_collection(logLine):
	collectionThreads = list()

	threadLocalCollection = threading.Thread(target=local_collection, args=())
	threadLocalCollection.daemon = True
	collectionThreads.append(threadLocalCollection)
	threadLocalCollection.start()
	print('Local collection of ESXi log bundle triggered ...')

	if args.rhosts:
		for rhost in args.rhosts:
			threadRemoteCollection = threading.Thread(target=remote_collection, kwargs={'rhost': rhost, 'user': 'root', 'password': args.password})
			threadRemoteCollection.daemon = True
			collectionThreads.append(threadRemoteCollection)
			threadRemoteCollection.start()
			print('Remote collection of ESXi log bundle for host {rhost} triggered ...'.format(rhost=rhost))

	for thread in collectionThreads:
		thread.join()

	write_script_log('All log bundle collections completed')
	print('All log bundle collections have completed.')

	sys.exit()
	return True


def local_collection():
	if args.hostd:
		write_script_log('Generating hostd coredump on the local ESXi host.')
		cmdHostdCoredump = 'vmkbacktrace -n hostd -c -w'
		os.system(cmdHostdCoredump)
		write_script_log('Completed generating hostd coredump on the local ESXi host.')

	write_script_log('Starting local collection of ESXi log bundle.')
	cmd = 'vm-support -w {wdir} > /dev/null'
	os.system(cmd.format(wdir=args.workingDir))
	write_script_log('Completed local collection of ESXi log bundle.')
	return True


def remote_collection(rhost, user, password):
	write_script_log('Starting remote collection of ESXi log bundle for host {rhost}.'.format(rhost=rhost))
	timestamp = datetime.datetime.now()
	logBundleName = '{directory}/esx-{fqdn}-{timestamp}.tgz'.format(directory=args.workingDir.rstrip('/'), fqdn=rhost, timestamp=timestamp.strftime('%Y-%m-%d--%H-%M-%S'))
	hostUrl = 'https://{fqdn}/cgi-bin/'.format(fqdn=rhost)
	logBundleUrl = 'https://{fqdn}/cgi-bin/vm-support.cgi'.format(fqdn=rhost)

	os.environ['PYTHONHTTPSVERIFY'] = '0'
	pwManager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
	pwManager.add_password('VMware CGI server', hostUrl, user, password)
	auth = urllib.request.HTTPBasicAuthHandler(pwManager)
	opener = urllib.request.build_opener(auth)
	urllib.request.install_opener(opener)
	logBundleResponse = urllib.request.urlopen(logBundleUrl)

	with open(logBundleName, 'wb') as f:
		for data in logBundleResponse:
			f.write(data)

	write_script_log('Completed remote collection of ESXi log bundle for host {rhost}.'.format(rhost=rhost))
	return True


def write_script_log(message):
	scriptLog = args.workingDir.rstrip('/') + '/auto-create-logs.log'
	timestamp = datetime.datetime.now()

	with open(scriptLog, 'a') as f:
		f.write(timestamp.strftime('%Y-%m-%dT%H:%M:%S') + ' {msg}\n'.format(msg=message))

	return True


def listen_on(filename):
	tsk = subprocess.Popen(['tail', '-f', '-n', '0', filename], stdout=subprocess.PIPE, bufsize=1)
	
	pobj = select.poll()
	pobj.register(tsk.stdout, select.POLLIN)
		
	i = 0
	while True:
		evt = pobj.poll(-1)
		if not evt:
			print('timeout...')
		
		elif select.POLLIN == evt[0][1]:
			lineUnchomped = tsk.stdout.readline()
			line = lineUnchomped.decode('utf-8').rstrip('\n')
			i += 1
			if line.find(args.logmsg) != -1:
				trigger_collection(line)
		else:
			break

	return True


def main():
	if not os.path.isfile(args.logFile):
		sys.exit('Specified log file does not exist: ' + args.logFile)

	if not os.path.isdir(args.workingDir):
		sys.exit('Specified directory does not exist: ' + args.workingDir)

	if args.rhosts and not args.password:
		sys.exit('No root password was specified for the remote hosts')

	listen_on(args.logFile)
	return True


#
## Main
#
if __name__ == '__main__':
	main()
