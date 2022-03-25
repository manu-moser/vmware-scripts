#!/bin/python3.6
#
# Written by Manuel Moser (moserm)

import sys, os, re, json
import mimetypes, time
from argparse import ArgumentParser
from datetime import datetime
from glob import glob
from decimal import *

import vsancmmdsfunctions
import vsantracefunctions

mosermHomeDir = os.path.expanduser('~moserm')
sys.path.append(mosermHomeDir + '/.local/lib/python3.6/site-packages')
from matplotlib import pyplot
import numpy, pandas, seaborn

# Parsing command-line arguments
parser = ArgumentParser()

argGrpMain = parser.add_mutually_exclusive_group(required=False)
argGrpMain.add_argument('-f', '--file', metavar='vsantraces.txt', dest='trace', default='.',
		help='specify vSAN trace file to process')
argGrpMain.add_argument('-d', '--dir', metavar='vsan-trace-directory', nargs='+', dest='trace', default='.',
		help='specify vSAN trace directory to process')

parser.add_argument('-l', '--latency', dest='sortByLatency', action='store_true', default=False,
		help='sort by latency value instead of timestamp')
parser.add_argument('-p', '--plot', dest='plotGraph', action='store_true', default=False,
		help='generate a graph for the unaligned IOs')
parser.add_argument('-t', '--top', dest='top', action='store_true', default=False,
		help='list top 10 objects with unaligned IOs and their related VM names')
parser.add_argument('-c', '--cmmds', metavar='cmmds/cmmds-tool_find--f-python.txt', nargs='?', dest='cmmds', default='cmmds/cmmds-tool_find--f-python.txt',
		help='path to the CMMDS dump. Use this in conjunction with -t|--top. Default value is \'cmmds/cmmds-tool_find--f-python.txt\'')
#parser.add_argument('-r', '--rmw', dest='allRmw', action='store_true', default=False,
#		help='output all found RMW IOs; by default only unaligned IOs (non 4K aligned) are written to the output')

args = parser.parse_args()


# General variables
rmwIos = dict()					# Structure: rmwIos['<opID>']['rmw|startDate|startTime|startTS|startEpoch|endDate|endTime|endTS|lat|obj|len']
topAffObjects = dict()				# Structure: topAffObjects['<object-uuid>']['amount|groupUuid']
objects = dict()				# Structure: objects['<uuid>']['owner|objClass|groupUuid|components']
						#            objects['<uuid>']['components']['<component-uuid>']['componentState|stale|diskUuid']
domNames = dict()				# Structure: domNames['<groupUuid>'] = <domName>
domNames['0'] = 'Not in CMMDS'
resultsFile = 'results-vsan-unaligned-ios.txt'

args.allRmw = False

#
## Functions
#
def search_rmw_io(vsanTraceFiles: dict):
	'''Search for RMW (readModifyWrite) IO that was created from writeWithBlkAttr5 in the vSAN trace files'''

	regexRmw = re.compile('\[(?P<opId>[0-9a-z]+) p:[A-Z]+ p:writeWithBlkAttr5 c:[A-Z]+ c:readModifyWrite.+length-[0-9]{2}.: (?P<length>[0-9]+)\}')

	for vsanTraceFile in vsanTraceFiles.keys():
		for vsanTraceMessage in vsanTraceFiles[vsanTraceFile]:
			resultRmw = regexRmw.search(vsanTraceMessage)
			if resultRmw:
				rmwIos[resultRmw.group('opId')] = dict()
				rmwIos[resultRmw.group('opId')]['rmw'] = vsanTraceMessage
				rmwIos[resultRmw.group('opId')]['len'] = resultRmw.group('length')

	return True


def calcuate_rmw_io_latency(vsanTraceFiles: dict):
	'''Calculate the latency of the RMW IO'''

	unalignedIoOpIds = ''
	for opId in rmwIos.keys():
		unalignedIoOpIds = unalignedIoOpIds + '|' + opId
		unalignedIoOpIds = unalignedIoOpIds.lstrip('|')

	regexUnalignedIoStartEnd = re.compile('(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})T(?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}).+\[(?P<opId>' + unalignedIoOpIds + ').+writeWithBlkAttr5.+(?P<stage>DOMTraceOperationSendRequestToServer|DOMTraceOperationSendRequestToServerCompleted):.+objUuid.: .(?P<object>[0-9a-z]{8}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12}).+')

	timestampFormat = '%Y-%m-%d %H:%M:%S.%f'

	def store_timestamp(opId: str, tsType: str, ioDate: str, ioTime: str):
		if tsType == 'start':
			rmwIos[opId]['startDate'] = ioDate
			rmwIos[opId]['startTime'] = ioTime
			rmwIos[opId]['startTS'] = ioDate + 'T' + ioTime
			rmwIos[opId]['startEpoch'] = int(time.mktime(time.strptime(ioDate + ' ' + ioTime, timestampFormat)))
		elif tsType == 'end':
			rmwIos[opId]['endDate'] = ioDate
			rmwIos[opId]['endTime'] = ioTime
			rmwIos[opId]['endTS'] = ioDate + 'T' + ioTime
		else:
			print('Error: unknown timestamp type')
		return True

	for vsanTraceFile in vsanTraceFiles.keys():
		for vsanTraceMessage in vsanTraceFiles[vsanTraceFile]:
			resultUnalignedIoStartEnd = regexUnalignedIoStartEnd.search(vsanTraceMessage)
			if resultUnalignedIoStartEnd:
				if resultUnalignedIoStartEnd.group('stage') == 'DOMTraceOperationSendRequestToServer':
					tsType = 'start'
				elif resultUnalignedIoStartEnd.group('stage') == 'DOMTraceOperationSendRequestToServerCompleted':
					tsType = 'end'
				else:
					print('Something went wrong. Regex matched, but for some reason it\'s unknown whether it\'s start or end of the IO')

				store_timestamp(opId=resultUnalignedIoStartEnd.group('opId'), tsType=tsType, ioDate=resultUnalignedIoStartEnd.group('date'), ioTime=resultUnalignedIoStartEnd.group('time'))

				rmwIos[resultUnalignedIoStartEnd.group('opId')]['obj'] = resultUnalignedIoStartEnd.group('object')

	for opId in list(rmwIos.keys()):
		if not 'startDate' in rmwIos[opId].keys() or not 'endTime' in rmwIos[opId].keys():
			del rmwIos[opId]
			continue

		timestampStart = datetime.strptime(rmwIos[opId]['startDate'] + ' ' + rmwIos[opId]['startTime'], timestampFormat)
		timestampEnd = datetime.strptime(rmwIos[opId]['endDate'] + ' ' + rmwIos[opId]['endTime'], timestampFormat)
		rmwIos[opId]['lat'] = timestampEnd - timestampStart

	return True


def identify_unaligned_io(io: dict):
	'''Checks whether an IO is 4K aligned and returns True or False accordingly'''

	ioLength = Decimal(str(io['len']))
	if '.' in str(ioLength / 4096):
		return True
	else:
		return False


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
			objUuid, objDetails = vsancmmdsfunctions.get_object_info(entryDomObject=entry)
			objects[objUuid] = objDetails
			continue
		if entry['type'] == 'DOM_NAME':
			domNameUuid, domName = vsancmmdsfunctions.get_dom_name(entryDomName=entry)
			domNames[domNameUuid] = domName
			continue

	return True


def process_top_affected_objects():
	'''Process top affected objects, which requires processing the CMMDS dump as well, to get the related VM names'''

	cmmdsDumpOrig = args.cmmds
	cmmdsDump = '/tmp/cmmds.json'

	if vsancmmdsfunctions.fix_cmmds_dump(cmmdsDumpInput=cmmdsDumpOrig, cmmdsDumpOutput=cmmdsDump):
		call_cmmds_parser(cmmdsDump=cmmdsDump)
	else:
		sys.exit('Function to rectify ending of the CMMDS dump file didn\'t run successfully. Exiting.')

	for unalignedIo in rmwIos.keys():
		if not identify_unaligned_io(io=rmwIos[unalignedIo]):
			continue

		objUuid = rmwIos[unalignedIo]['obj']

		if objUuid in topAffObjects.keys():
			topAffObjects[objUuid]['amount'] += 1
		else:
			topAffObjects[objUuid] = dict()
			topAffObjects[objUuid]['amount'] = 1

			if objUuid in objects.keys():
				topAffObjects[objUuid]['groupUuid'] = objects[objUuid]['groupUuid']
			else:
				topAffObjects[objUuid]['groupUuid'] = '0'

	return True


def output_top_affected_objects():
	'''Output the 10 objects with the highest amount of unaligned IOs and their related VM names'''

	i = 0
	top = 10

	print(' Number of Unaligned IOs | Object UUID                          | Related VM')
	print('-------------------------+--------------------------------------+------------')

	for objUuid in sorted(topAffObjects, key=lambda x: topAffObjects[x]['amount'], reverse=True):
		if not i < top:
			break

		paddingIo = 24 - len(str(topAffObjects[objUuid]['amount']))

		print(' ' * paddingIo + str(topAffObjects[objUuid]['amount']) + ' | ' + objUuid + ' | ' + domNames[topAffObjects[objUuid]['groupUuid']])

		i += 1

	return True


def output_findings():
	'''Write the found unaligned IOs and their details into the output file'''

	fhResults = open(resultsFile, 'w')

	def convert_timeformat_to_units(timestamp: str) -> str:
		'''Convert "0:00:00.000908" timestamp to the following format (omitting 0 values, though): 0h 00min 00s 000ms 908us
		Resulting string length is 24 characters'''

		hours, minutes, seconds = str(timestamp).split(':')
		seconds, microseconds = seconds.split('.')
		milliseconds = microseconds[0:3]
		microseconds = microseconds[3:6]

		strLatency = microseconds + 'us'

		if int(milliseconds) != 0:
			strLatency = milliseconds.lstrip('0') + 'ms ' + strLatency

		if int(seconds) != 0 :
			strLatency = seconds.lstrip('0') + 's ' + strLatency

		if int(minutes) != 0:
			strLatency = minutes.lstrip('0') + 'min ' + strLatency

		if int(hours) != 0:
			strLatency = hours + 'h ' + strLatency

		while len(strLatency) < 24:
			strLatency = ' ' + strLatency

		return strLatency

	def output_io(opId: str, io: dict, fhOutput):
		if not args.allRmw:
			if not identify_unaligned_io(io=io):
				return False

		outputStr = '{opId} | {length} | {uuid} | {tsStart} | {tsEnd} | {latency}\n'
		ioLength = io['len']

		while len(ioLength) < 6:
			ioLength = ' ' + ioLength

		fhOutput.write(outputStr.format(opId=opId, length=ioLength, uuid=io['obj'], tsStart=io['startTS'], tsEnd=io['endTS'], latency=convert_timeformat_to_units(io['lat'])))
		return True

	fhResults.write(' Op ID   | Length | Object UUID                          | Start Time                 | End Time                   | Total Latency\n')
	fhResults.write('---------+--------+--------------------------------------+----------------------------+----------------------------+' + '-' * 26 + '\n')

	if args.sortByLatency:
		sortBy = 'lat'
	else:
		sortBy = 'startEpoch'

	for unalignedIo in sorted(rmwIos, key=lambda x: rmwIos[x][sortBy], reverse=True):
		output_io(opId=unalignedIo, io=rmwIos[unalignedIo], fhOutput=fhResults)

	fhResults.close()
	os.chmod(resultsFile, 0o666)

	print('Results: %s' % (resultsFile))
	return True


def plot_graph_matplotlib():
	'''Outdated function
	Generate graph with unaligned IOs, using matplotlib
	X-axis: Time
	Y-axis: Latency'''

	graph = 'graph-vsan-unaligned-ios.png'
	timestamps = list()
	latencies = list()

	print('Plotting graph...')

	def convert_time_to_microseconds(timestamp: str) -> str:
		hours, minutes, seconds = timestamp.split(':')
		seconds, microseconds = seconds.split('.')
		milliseconds = int(hours) * 3600000 + int(minutes) * 60000 + int(seconds) * 1000
		microsecondsTotal = milliseconds * 1000 + int(microseconds)
		return microsecondsTotal

	# Create list of timestamps for x-axis and latencies for y-axis
	for io in sorted(rmwIos, key=lambda x: rmwIos[x]['startEpoch']):
		timestamp = rmwIos[io]['startDate'] + ' ' + rmwIos[io]['startTime']
		timestamps.append(timestamp)

		latencyUs = convert_time_to_microseconds(str(rmwIos[io]['lat']))
		latencies.append(latencyUs)

	df = pandas.DataFrame({'time': timestamps, 'latency': latencies})
	pyplot.figure(figsize=(20,10)) # Figure size in inches
	pyplot.plot('time', 'latency', data=df, linestyle='none', marker='o')

	pyplot.xlabel('Time - Start: {start} UTC - End: {end} UTC'.format(start=timestamps[0], end=timestamps[-1]))
	pyplot.ylabel('Latency in us - max: {maxLat}'.format(maxLat=max(latencies)))
	pyplot.title('Unaligned IO Latencies')

	pyplot.savefig(graph)
	os.chmod(graph, 0o666)

	print('Finished plotting graph: ' + graph)
	return True


def plot_graph():
	'''Generate graph with RMW and/or unaligned IOs, using seaborn
	X-axis: Time
	Y-axis: Latency'''

	graph = 'graph-vsan-unaligned-ios.png'
	timestamps = list()
	latencies = list()

	print('Plotting graph...')

	def convert_time_to_microseconds(timestamp):
		hours, minutes, seconds = timestamp.split(':')
		seconds, microseconds = seconds.split('.')
		milliseconds = int(hours) * 3600000 + int(minutes) * 60000 + int(seconds) * 1000
		microsecondsTotal = milliseconds * 1000 + int(microseconds)
		return microsecondsTotal

	def add_data_point(ioOpId: str):
		timestamp = rmwIos[ioOpId]['startDate'] + ' ' + rmwIos[ioOpId]['startTime']
		timestamps.append(timestamp)
		latencyUs = convert_time_to_microseconds(str(rmwIos[ioOpId]['lat']))
		latencies.append(latencyUs)
		return True

	# Create list of timestamps for x-axis and latencies for y-axis
	for io in sorted(rmwIos, key=lambda x: rmwIos[x]['startEpoch']):
		if args.allRmw:
			add_data_point(ioOpId=io)
		else:
			if identify_unaligned_io(io=rmwIos[io]):
				add_data_point(ioOpId=io)

	seaborn.set()
	df = pandas.DataFrame({'time': timestamps, 'latency': latencies})
	pyplot.figure(figsize=(20,10)) # Figure size in inches
	seaborn.regplot(x='time', y='latency', data=df, fit_reg=False)

	pyplot.xlabel('Time - Start: {start} UTC - End: {end} UTC'.format(start=timestamps[0], end=timestamps[-1]))
	pyplot.ylabel('Latency in us - max: {maxLat}'.format(maxLat=max(latencies)))
	pyplot.title('Unaligned IO Latencies')

	pyplot.savefig(graph)
	os.chmod(graph, 0o666)

	print('Finished plotting graph: ' + graph)
	print('Graph URL: ' + get_srviwer_url(graph))
	return True


def get_srviwer_url(fileName):
	fullOSPath = os.path.abspath(os.getcwd())

	regexPath = re.compile('/scripts/data/srdata[0-9]+/(?P<sr>[0-9]{12})(?P<remain>.*)')
	resultPath = regexPath.search(fullOSPath)

	if not resultPath:
		print('Couldn\'t detect SR number in current working directory.')
		return False

	srNum = resultPath.group('sr')
	remain = resultPath.group('remain')

	srviewerBase = 'http://srviewer.vmware.com/sfdc-scripts/4/'
	srDir = '/'.join(re.findall('...', srNum))

	srviewerUrl = srviewerBase + srDir + '/' + remain.lstrip('/') + '/' + fileName

	return srviewerUrl


def main():
	vsanTraceFiles = vsantracefunctions.process_trace_file_arg(vsanTraceArg=args.trace, traceFilePrefix='vsantraces--')
	vsanTraceFiles = vsantracefunctions.read_in_vsan_trace_files(vsanTraceFiles=vsanTraceFiles)

	search_rmw_io(vsanTraceFiles=vsanTraceFiles)
	calcuate_rmw_io_latency(vsanTraceFiles=vsanTraceFiles)
	output_findings()

	if args.top:
		print('Processing top affected objects...\n')
		process_top_affected_objects()
		output_top_affected_objects()

	if args.plotGraph:
		plot_graph()


#
## Main
#
if __name__ == '__main__':
	main()
