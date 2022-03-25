#!/bin/python3.6
#
# Module with functions for processing vSAN traces
#
# Written by Manuel Moser (moserm)

import sys, os
import mimetypes
from glob import glob


#
## Functions
#
def process_trace_file_arg(vsanTraceArg, traceFilePrefix: str) -> dict:
	'''Return dictionary with vSAN trace files.
	Arguments:
		vsanTraceArg: either a string containing the vSAN trace file name or a list with vSAN trace directories
		traceFilePrefix: vSAN trace file prefix, i.e. vsantraces, vsantracesUrgent, vsantracesLSOM, etc.
	Return:
		vsanTraceFiles['<filename>'] = list() -> dictionary with the vSAN trace files as keys'''

	vsanTraceFiles = dict()

	if isinstance(vsanTraceArg, str) and os.path.isfile(vsanTraceArg):
		vsanTraceFiles[vsanTraceArg] = list()
	else:
		traceFileFormat = '{prefix}*.{ending}'
		traceFileEndings = ['txt', 'log']

		print('Directory specified, looking for vSAN trace files in the format of:')
		for ending in traceFileEndings:
			print('\t%s' % (traceFileFormat.format(prefix=traceFilePrefix, ending=ending)))

		for directory in vsanTraceArg:
			print('Checking directory {} for vSAN trace files ...'.format(directory))
			if not os.path.isdir(directory):
				print('No such directory: {}'.format(directory))
				continue

			vsanTraceFiles = process_trace_dir(vsanTraceDir=directory, vsanTraceFiles=vsanTraceFiles, traceFilePrefix=traceFilePrefix, traceFileEndings=traceFileEndings)

	return vsanTraceFiles


def process_trace_dir(vsanTraceDir: str, vsanTraceFiles: dict, traceFilePrefix: str, traceFileEndings: list) -> dict:
	'''Go through the specified directory and add found vSAN trace files to an existing dictionary.
	Arguments:
		vsanTraceDir: path to the directory to look for vSAN trace files in
		vsanTraceFiles: dictionary with vSAN trace files
		prefix: string, how the vSAN trace files start (e.g. "vsantraces--")
		traceFileEndings: list of file possible file endings for the vSAN trace files
	Return:
		vsanTraceFiles['<filename>'] = list() -> dictionary with the vSAN trace files as keys'''

	traceFileFormat = '{prefix}*.{ending}'

	fileList = list()
	for ending in traceFileEndings:
		fileList = fileList + glob(vsanTraceDir.rstrip('/') + '/' + traceFileFormat.format(prefix=traceFilePrefix, ending=ending))

	if len(fileList):
		for vsanTraceFile in fileList:
			vsanTraceFiles[vsanTraceFile] = list()
	else:
		print('No vSAN trace files found in specified directory %s' % (vsanTraceDir))

	return vsanTraceFiles


def read_in_vsan_trace_files(vsanTraceFiles: dict) -> dict:
	'''Reads in all vSAN trace files in dictionary "vsanTraceFiles"

	Arguments:
		vsanTraceFiles['<filename>'] = list() -> dictionary with the vSAN trace files as keys

	Return:
		vsanTraceFiles['<filename>'] = list() -> dictionary with the vSAN trace files as keys. The list() contains the lines read in from the trace file.'''

	for vsanTraceFile in vsanTraceFiles.keys():
		mime = mimetypes.guess_type(vsanTraceFile)
		if not mime[0] == 'text/plain':
			sys.exit('Provided vSAN trace file is not in text format: %s' % (vsanTraceFile))

		with open(vsanTraceFile, 'r') as f:
			vsanTraceFiles[vsanTraceFile] = f.readlines()

	return vsanTraceFiles
