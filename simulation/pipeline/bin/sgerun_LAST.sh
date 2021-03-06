#!/bin/bash

#
# Align query to subject
#

#$ -e logs/
#$ -o logs/
#$ -cwd
#$ -N LASTJOB

if [ -z "$JOB_ID" ]
then
	BINDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
	source $BINDIR/bash_init.sh
fi

LASTAL=external/last/bin/lastal
LASTDB=external/last/bin/lastdb
MAFCONV=external/last/bin/maf-convert

if [ -z "$JOB_ID" ] # SUBMIT MODE
then
	if [ $# -ne 3 ]
	then
		echo "Usage: <subject> <query> <output_base>"
		exit 1
	fi

	echo "Submitting run"
	TARGET=( ${1}.prj ${3} )
	#trap 'rollback_rm_files ${TARGET[@]}; exit $?' INT TERM EXIT
	CMD=`readlink -f $0`
	qsub -sync yes -V -v SUBJECT=$1,QUERY=$2,OUTPUT=$3 $CMD
	#trap - INT TERM EXIT
	echo "Finished"

else # EXECUTION MODE
	echo "Running"

    if [ ! -e ${SUBJECT}.prj ]
    then
        echo "There doesn't appaear to be a LAST DB associated with this reference data"
        echo "Creating database..."
        $LASTDB $SUBJECT $SUBJECT
    fi

	# align
	$LASTAL $SUBJECT $QUERY | $MAFCONV psl > $OUTPUT
fi
