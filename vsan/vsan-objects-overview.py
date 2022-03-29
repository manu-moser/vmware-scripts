#!/bin/python3
#
# Version: 1.0.3
# Written by Manuel Moser (moserm)

import sys, os, re, json, subprocess
from argparse import ArgumentParser


# Parsing command-line arguments
parser = ArgumentParser()

parser.add_argument('-c', '--cmmds', dest='cmmds', required=False,
	help='path to the CMMDS dump')
parser.add_argument('-a', '--affected', dest='affected', required=False, action='store_true',
	help='only print affected objects, i.e. with components that are not active')
parser.add_argument('-d', '--debug', dest='debug', required=False, action='store_true',
	help='debug output')

args = parser.parse_args(
)

# General variables
UUID = '[0-9a-z]{8}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12}'
objClass = ['VMDK', 'Snapshot', 'Namespace', 'VSWP', 'VMEM', 'Sidecar', 'HBR', 'Coredump', 'DPCONSISTENCYGRP', 'VDFS', 'VDFS_ROOT', 'N/A']
compStates = ['First', 'None', 'Need Config', 'Initialize', 'Initialized', 'Active', 'Absent', 'Stale', 'Resyncing', 'Degraded', 'Reconfiguring', 'Cleanup', 'Transient', 'Last']
objects = {}				# Structure: objects['<uuid>']['owner|objClass|groupUuid|components']
					#	     objects['<uuid>']['components']['<component-uuid>']['type|componentState|stale|diskUuid']
domNames = {}                           # Structure: domNames['<groupUuid>'] = <domName>
hosts = {}                              # Structure: hosts['<uuid>'] = <hostname>
devices = {}				# Structure: devices['<uuid>']['deviceId|hostUuid']

hosts['00000000-0000-0000-0000-000000000000'] = 'Not found'
devices['00000000-0000-0000-0000-000000000000'] = {}
devices['00000000-0000-0000-0000-000000000000']['deviceId'] = 'Not found'
devices['00000000-0000-0000-0000-000000000000']['hostUuid'] = '00000000-0000-0000-0000-000000000000'


#
## Functions
#

def create_cmmds_dump(cmmdsDumpOutput: str):
	'''Create a CMMSD dump on a live ESXi
	Arguments:
		cmmdsDumpOutput: path to write the CMMDS dump to'''

	cmdDumpCmmds = 'cmmds-tool find -f python > ' + cmmdsDumpOutput

	try:
		subprocess.check_output(cmdDumpCmmds, shell=True, stderr=subprocess.STDOUT)
	except subprocess.CalledProcessError as cpe:
		print('Error running cmmds-tool: ' + str(cpe))
		sys.exit()

	os.chmod(cmmdsDumpOutput, 0o666)
	return True


def fix_cmmds_dump(cmmdsDumpInput: str, cmmdsDumpOutput: str):
	'''Reads in the CMMDS dump, removes the last "," character, and then writes a new CMMDS dump file, so it can be loaded into Python json
	Arguments:
		cmmdsDumpInput: path to the original CMMDS dump
		cmmdsDumpOutput: path to the new CMMDS dump file that will be created by this function'''

	if not os.path.isfile(cmmdsDumpInput):
		print('CMMDS dump file not found: %s' % cmmdsDumpOrig)
		return False

	fhCmmds = open(cmmdsDumpInput, 'r')
	cmmdsContent = fhCmmds.readlines()
	cmmdsContent[len(cmmdsContent)-2] = '}'

	fhNewCmmds = open(cmmdsDumpOutput, 'w')
	fhNewCmmds.writelines(cmmdsContent)

	os.chmod(cmmdsDumpOutput, 0o666)
	fhCmmds.close()
	fhNewCmmds.close()

	return True


def call_cmmds_parser(cmmdsDump: str):
	'''Call CMMDS parse routine
	Arguments:
		cmmdsDump: path to the CMMDS dump that's to be parsed'''

	fhCmmds = open(cmmdsDump, 'r')
	cmmds = json.load(fhCmmds)
	fhCmmds.close()
	parse_cmmds(cmmds=cmmds)
	os.remove(cmmdsDump)
	return True


def parse_cmmds(cmmds):
	'''Parse CMMDS dump and call respective functions for the required entries'''

	for entry in cmmds:
		if entry['type'] == 'DOM_OBJECT':
			get_object_info(entry)
			continue
		if entry['type'] == 'DOM_NAME':
			get_dom_name(entry)
			continue
		if entry['type'] == 'HOSTNAME':
			get_host(entry)
			continue
		if entry['type'] == 'DISK':
			get_disk(entry)
			continue

	return True


def get_object_info(entryDomObject: dict):
	'''Get objcet info like group UUID, object class, etc.'''

	if not entryDomObject['uuid'] in objects.keys():
		objects[entryDomObject['uuid']] = {}
		objects[entryDomObject['uuid']]['components'] = {}

	objects[entryDomObject['uuid']]['owner'] = entryDomObject['owner']

	regexObjInfo = re.compile('"([^"]+)": ["]{0,1}([^",\}]+)')
	resultObjInfo = re.findall(regexObjInfo, entryDomObject['content'])

	parse_dom_object_details(objUuid=entryDomObject['uuid'], objDetails=resultObjInfo)

	return True


def parse_dom_object_details(objUuid: str, objDetails: list):
	'''Get the groupUuid, objClass, component UUIDs, and component states from the DOM_OBJECT content values'''

	staleCsn = False

	for keyValuePair in objDetails:
		if keyValuePair[0] == 'groupUuid':
			objects[objUuid]['groupUuid'] = keyValuePair[1]
			continue

		if keyValuePair[0] == 'objClass':
			objects[objUuid]['objClass'] = keyValuePair[1]
			continue

		if keyValuePair[0] == 'type':
			componentType = keyValuePair[1]
			continue

		if keyValuePair[0] == 'componentState':
			componentState = keyValuePair[1]
			continue

		if keyValuePair[0] == 'staleCsn':
			staleCsn = True
			continue

		if keyValuePair[0] == 'componentUuid':
			componentUuid = keyValuePair[1]
			continue

		if keyValuePair[0] == 'diskUuid':
			diskUuid = keyValuePair[1]
			objects[objUuid]['components'][componentUuid] = dict()
			objects[objUuid]['components'][componentUuid]['type'] = componentType
			objects[objUuid]['components'][componentUuid]['componentState'] = componentState
			objects[objUuid]['components'][componentUuid]['stale'] = staleCsn
			objects[objUuid]['components'][componentUuid]['diskUuid'] = diskUuid
			componentState = 0
			staleCsn = False

	if not 'groupUuid' in objects[objUuid].keys():
		objects[objUuid]['groupUuid'] = 'Not found'

	if not 'objClass' in objects[objUuid].keys():
		objects[objUuid]['objClass'] = 0

	return True


def get_dom_name(entryDomName: dict):
	'''Get VM name from DOM_NAME entry in CMMDS'''

	regexEmptyName = re.compile('.*ufn": "".*')
	regexDomName = re.compile('.*ufn": "(.+)", "cid": "' + UUID + '".*')

	if re.search(regexEmptyName, entryDomName['content']):
		domNames[entryDomName['uuid']] = '<none>'
		return True

	searchResult = re.search(regexDomName, entryDomName['content'])

	if not searchResult:
		regexDomName = re.compile('.*ufn": "(.+)"}.*')
		searchResult = re.search(regexDomName, entryDomName['content'])

	if searchResult:
		domNames[entryDomName['uuid']] = searchResult.group(1)
	else:
		domNames[entryDomName['uuid']] = 'Not found'

	return True


def get_host(entryHost: dict):
	'''Get hostname from HOSTNAME entry in CMMDS'''

	hosts[entryHost['uuid']] = entryHost['content'].split()[1].lstrip('"').rstrip('"}')
	return True


def get_disk(entryDisk: dict):
	'''Get device ID for a disk and the host UUID it's located in'''

	if not entryDisk['uuid'] in devices.keys():
		devices[entryDisk['uuid']] = {}
		devices[entryDisk['uuid']]['hostUuid'] = entryDisk['owner']

	regexDiskInfo = re.compile('"([^"]+)": ["]{0,1}([^",\}]+)')
	resultDiskInfo = re.findall(regexDiskInfo, entryDisk['content'])

	for keyValuePair in resultDiskInfo:
		if keyValuePair[0] == 'devName':
			devices[entryDisk['uuid']]['deviceId'] = keyValuePair[1]
			break

	return True


def get_max_length(stringList: list) -> list:
	'''Return the length of the longest string in a list'''

	maxLength = 0

	for string in stringList:
		if len(string) > maxLength:
			maxLength = len(string)

	return maxLength


def get_nested_dict_values(nestedDict: dict, subkey: str) -> list:
	'''Get the values from a nested dictionary for a particular subkey and return the values as a list'''

	valuesList = list()

	for key in nestedDict.keys():
		valuesList.append(nestedDict[key][subkey])

	return valuesList


def print_objects_overview():
	'''Print a table with the overview of the objects'''

	hostnameColWidth = get_max_length(hosts.values()) + 2

	deviceIdColWidth = get_max_length(get_nested_dict_values(nestedDict=devices, subkey='deviceId')) + 2
	if deviceIdColWidth < 32:
		deviceIdColWidth = 32

	columnWidths = [37, 18, hostnameColWidth, 65, deviceIdColWidth, hostnameColWidth, 27]

	def print_header(columnWidths: list):
		columnTitle0 = 'vSAN Object UUID'
		columnTitle1 = 'Object Type'
		columnTitle2 = 'DOM Owner'
		columnTitle3 = 'vSAN Component States'
		columnTitle4 = 'Capacity Device with Component'
		columnTitle5 = 'Host with Component'
		columnTitle6 = 'Related VM Name'

		padding0 = columnWidths[0] - len(columnTitle0)
		padding1 = columnWidths[1] - len(columnTitle1) - 2 # the '- 2' at the end is to take into account the manually added padding with ' | '
		padding2 = columnWidths[2] - len(columnTitle2) - 2
		padding3 = columnWidths[3] - len(columnTitle3) - 2
		padding4 = columnWidths[4] - len(columnTitle4) - 2
		padding5 = columnWidths[5] - len(columnTitle5) - 2

		print(columnTitle0 + ' ' * padding0 + '| '
			+ columnTitle1 + ' ' * padding1 + ' | '
			+ columnTitle2 + ' ' * padding2 + ' | '
			+ columnTitle3 + ' ' * padding3 + ' | '
			+ columnTitle4 + ' ' * padding4 + ' | '
			+ columnTitle5 + ' ' * padding5 + ' | '
			+ columnTitle6)
		return True

	def print_separator(columnWidths: list):
		print('-' * columnWidths[0] + '+'
			+ '-' * columnWidths[1] + '+'
			+ '-' * columnWidths[2] + '+'
			+ '-' * columnWidths[3] + '+'
			+ '-' * columnWidths[4] + '+'
			+ '-' * columnWidths[5] + '+'
			+ '-' * columnWidths[6])
		return True

	def print_object(columnWidths: list, objUuid: str):
		firstLine = True

		for compUuid in objects[objUuid]['components'].keys():
			strCompState = compStates[int(objects[objUuid]['components'][compUuid]['componentState'])]
			if objects[objUuid]['components'][compUuid]['stale']:
				strCompState += ' Stale'

			diskUuid = objects[objUuid]['components'][compUuid]['diskUuid']
			if not diskUuid in devices:
				diskUuid = '00000000-0000-0000-0000-000000000000'

			padding1 = columnWidths[1] - len(objClass[int(objects[objUuid]['objClass'])]) - 2
			padding2 = columnWidths[2] - len(hosts[objects[objUuid]['owner']]) - 2
			padding3 = columnWidths[3] - len(compUuid) - len(objects[objUuid]['components'][compUuid]['type'])- 5 - len(strCompState) - 2 # the first '- 5' is for the strings ' (' and  '): '
			padding4 = columnWidths[4] - len(devices[diskUuid]['deviceId']) - 2
			padding5 = columnWidths[5] - len(hosts[devices[diskUuid]['hostUuid']]) - 2

			if firstLine or args.debug:
				try:
					domName = domNames[objects[objUuid]['groupUuid']]
				except:
					domName = 'Not found'

				print(objUuid + ' | '
					+ objClass[int(objects[objUuid]['objClass'])] + ' ' * padding1 + ' | '
					+ hosts[objects[objUuid]['owner']] + ' ' * padding2 + ' | '
					+ compUuid + ' (' + objects[objUuid]['components'][compUuid]['type'] + '): ' + strCompState + ' ' * padding3 + ' | '
					+ devices[diskUuid]['deviceId'] + ' ' * padding4 + ' | '
					+ hosts[devices[diskUuid]['hostUuid']] + ' ' * padding5 + ' | '
					+ domName)
				firstLine = False
			else:
				#linePadding = len(objUuid + ' | ' + objClass[int(objects[objUuid]['objClass'])] + ' ' * padding1)
				linePadding = columnWidths[0] + 1 + columnWidths[1] + 1 + columnWidths[2] # '+ 1' is for the '|'
				padding3 = columnWidths[3] - len(compUuid) - len(objects[objUuid]['components'][compUuid]['type']) - 5 - len(strCompState) - 2 # the first '- 5' is for the strings ' (' and  '): '
				print(' ' * linePadding + '| '
					+ compUuid + ' (' + objects[objUuid]['components'][compUuid]['type'] + '): ' + strCompState + ' ' * padding3 + ' | '
					+ devices[diskUuid]['deviceId'] + ' ' * padding4 + ' | '
					+ hosts[devices[diskUuid]['hostUuid']] + ' ' * padding5 + ' | ')

		return True

	def check_affected(objUuid: str):
		for compUuid in objects[objUuid]['components'].keys():
			if int(objects[objUuid]['components'][compUuid]['componentState']) != 5:
				return True

		return False

	print_header(columnWidths=columnWidths)
	print_separator(columnWidths=columnWidths)

	for objUuid in objects.keys():
		if args.affected:
			if check_affected(objUuid=objUuid):
				print_object(columnWidths=columnWidths, objUuid=objUuid)
				print_separator(columnWidths=columnWidths)
		else:
			print_object(columnWidths=columnWidths, objUuid=objUuid)
			print_separator(columnWidths=columnWidths)

	return True


def main():
	'''Main function'''

	cmmdsDump = '/tmp/cmmds.json'

	if args.cmmds:
		cmmdsDumpOrig = args.cmmds
	else:
		cmmdsDumpOrig = '/tmp/cmmdsDump.txt'
		create_cmmds_dump(cmmdsDumpOutput=cmmdsDumpOrig)

	if fix_cmmds_dump(cmmdsDumpInput=cmmdsDumpOrig, cmmdsDumpOutput=cmmdsDump):
		call_cmmds_parser(cmmdsDump=cmmdsDump)
	else:
		sys.exit('Function to rectify ending of the CMMDS dump file didn\'t run successfully. Exiting.')

	print_objects_overview()

	return True


#
## Main
#
if __name__ == '__main__':
	main()
