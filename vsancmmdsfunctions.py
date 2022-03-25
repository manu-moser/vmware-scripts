#!/bin/python3
#
# Written by Manuel Moser (moserm)

import os, re

#
## General variables
#

UUID = '[0-9a-z]{8}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12}'


#
## Functions
#

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


def get_dom_name(entryDomName: dict) -> tuple:
	'''Get VM name from DOM_NAME entry in CMMDS
	Arguments:
		entryDomName: CMMDS entry to process
	Return:
		tuple with DOM_NAME UUID and namespace object name'''

	regexDomName = re.compile('.*ufn": "(.+)", "cid": "' + UUID + '".*')

	searchResult = re.search(regexDomName, entryDomName['content'])

	if not searchResult:
		regexDomName = re.compile('.*ufn": "(.+)"}.*')
		searchResult = re.search(regexDomName, entryDomName['content'])

	if searchResult:
		return (entryDomName['uuid'], searchResult.group(1))
	else:
		return (entryDomName['uuid'], 'Not found')

	return True


def get_object_info(entryDomObject: dict) -> tuple:
	'''Get objcet info like group UUID, object class, etc.
	Arguments:
		entryDomObject: CMMDS entry to process
	Return:
		tuple with object UUID and dictionary with object details'''

	objectDetails = dict()
	objectDetails['owner'] = entryDomObject['owner']

	regexObjInfo = re.compile('"([^"]+)": ["]{0,1}([^",\}]+)')
	resultObjInfo = re.findall(regexObjInfo, entryDomObject['content'])

	objectDetails = parse_dom_object_details(objDetails=resultObjInfo, vsanObject=objectDetails)

	return (entryDomObject['uuid'], objectDetails)


def parse_dom_object_details(objDetails: list, vsanObject: dict) -> dict:
	'''Get the groupUuid, objClass, component UUIDs, and component states from the DOM_OBJECT content values
	Arguments:
		objDetails: dictionary with all object details
		vsanObject: dictionary to popluate with details in nice format
	Return:
		dictionary with pupulated details in nice format'''

	staleCsn = False
	vsanObject['components'] = dict()

	for keyValuePair in objDetails:
		if keyValuePair[0] == 'groupUuid':
			vsanObject['groupUuid'] = keyValuePair[1]
			continue

		if keyValuePair[0] == 'objClass':
			vsanObject['objClass'] = keyValuePair[1]
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
			vsanObject['components'][componentUuid] = dict()
			vsanObject['components'][componentUuid]['componentState'] = componentState
			vsanObject['components'][componentUuid]['stale'] = staleCsn
			vsanObject['components'][componentUuid]['diskUuid'] = diskUuid
			componentState = 0
			staleCsn = False

	if not 'groupUuid' in vsanObject.keys():
		vsanObject['groupUuid'] = 'Not found'

	if not 'objClass' in vsanObject.keys():
		vsanObject['objClass'] = 0

	return vsanObject
