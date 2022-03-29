#!/bin/bash

BASEDIR=`pwd`
VSAN_TRACE_READER="./vsanTraceReader"
VSAN_TRACE_READER2="../../../usr/lib/vmware/vsan/bin/vsanTraceReader"

if [ -f $VSAN_TRACE_READER ]
then
	ls | grep "vsantraces.*gz" | while read TRACE
	do
		FILE=`echo $TRACE | cut -d "." -f 1`

		gzip -d -f -c $TRACE | $VSAN_TRACE_READER > ${FILE}.txt
	done
elif [ -f $VSAN_TRACE_READER2 ]
then
	chmod 775 $VSAN_TRACE_READER2

	ls | grep "vsantraces.*gz" | while read TRACE
	do
		FILE=`echo $TRACE | cut -d "." -f 1`
		gzip -d -f -c $TRACE | $VSAN_TRACE_READER2 > ${FILE}.txt
	done
else
	ls | grep "esx-" | grep -v "tgz" | while read BUNDLE
	do
		if [ -d "${BUNDLE}/var/log/vsantraces" ]
		then
			EXTRACTED=`ls ${BUNDLE}/var/log/vsantraces | grep "vsantraces.*.txt" | head -n 1`

			if [ "$EXTRACTED" == "" ]
			then
				cd ${BUNDLE}/var/log/vsantraces/

				ls | grep "vsantraces.*\.gz" | while read TRACE
				do
					NAME=`echo $TRACE | cut -d "." -f 1`

					if [ -f $VSAN_TRACE_READER ]
					then
						gzip -d -f -c $TRACE | $VSAN_TRACE_READER > ${NAME}.txt
					else
						chmod 775 $VSAN_TRACE_READER2
						gzip -d -f -c $TRACE | $VSAN_TRACE_READER2 > ${NAME}.txt
					fi
				done

				cd $BASEDIR
			fi
		fi
	done
fi
