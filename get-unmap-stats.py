#!/bin/python
#
# Written by Manuel Moser (moserm)

import sys

try:
	import vmware.vsi as vsi
	import pyCMMDS
except:
	sys.exit('Failed to import Python modules for VSI and CMMDS. Is this really a live ESXi?')


#
## Functions
#
def get_vsan_object_uuids():
	vsanObjectUuids = vsi.list('/vmkModules/vsan/dom/owners/')
	return vsanObjectUuids


def get_unmap_stats(vsanObjectUuid):
	vsiPath = '/vmkModules/vsan/dom/owners/{}/stats'.format(vsanObjectUuid)
	allUnmapStats = vsi.get(vsiPath)

	unmapStats = dict()
	unmapStats['unmapCount'] = allUnmapStats['unmapCount']
	unmapStats['unmapBytes'] = allUnmapStats['unmapBytes']

	return unmapStats


def get_vm_name(vsanObjectUuid):
	queryDomObject = pyCMMDS.CMMDSQuery()
	queryDomObject.uuid = vsanObjectUuid
	queryDomObject.type = pyCMMDS.CMMDS_TYPE_DOM_OBJECT
	queryDomObject.wildcards = {'latestRevision': 1, 'anyOwner': 1}
	entryDomObject = pyCMMDS.FindEntry(queryDomObject, pyCMMDS.CMMDS_FIND_FLAG_NONE, True)
	try:
		groupUuid = entryDomObject.content['attributes']['groupUuid']
	except:
		relatedVM = 'None found'
		return relatedVM

	queryDomName = pyCMMDS.CMMDSQuery()
	queryDomName.uuid = groupUuid
	queryDomName.type = pyCMMDS.CMMDS_TYPE_DOM_NAME
	queryDomName.wildcards = {'latestRevision': 1, 'anyOwner': 1}
	entryDomName = pyCMMDS.FindEntry(queryDomName, pyCMMDS.CMMDS_FIND_FLAG_NONE, True)
	try:
		relatedVM = entryDomName.content['ufn']
	except:
		relatedVM = 'None found'

	return relatedVM


def print_unmap_stats(vsanObjects):
	print(' Object UUID' + ' ' * 26 + '| Total number of unmaps | Total unmap bytes' + ' ' * 12 + '| Related VM')
	print('-' * 114)

	#for uuid in vsanObjects.keys():
	for uuid in sorted(vsanObjects, key=lambda x: vsanObjects[x]['unmapBytes'], reverse=True):
		unmapCountPadding = 22 - len(str(vsanObjects[uuid]['unmapCount']))
		unmapCountPaddingStr = ' ' * unmapCountPadding
		unampBytesPadding = 28 - len(str(vsanObjects[uuid]['unmapBytes']))
		unampBytesPaddingStr = ' ' * unampBytesPadding

		outputLine = ' {uuid} | {unmapCountPadding}{unmapCount} | {unampBytesPadding}{unmapBytes} | {vm}'.format(uuid=uuid, unmapCountPadding=unmapCountPaddingStr, unmapCount=vsanObjects[uuid]['unmapCount'],
				unampBytesPadding=unampBytesPaddingStr, unmapBytes=vsanObjects[uuid]['unmapBytes'], vm=vsanObjects[uuid]['vm'])

		print(outputLine)

	return True


def main():
	vsanObjects = dict()

	objectUuids = get_vsan_object_uuids()

	for uuid in objectUuids:
		vsanObjects[uuid] = get_unmap_stats(vsanObjectUuid=uuid)
		vsanObjects[uuid]['vm'] = get_vm_name(uuid)

	print_unmap_stats(vsanObjects=vsanObjects)

	return True


#
## Main
#
if __name__ == '__main__':
	main()
