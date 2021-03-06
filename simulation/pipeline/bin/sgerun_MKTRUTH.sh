#!/bin/bash

#
# Create truth table
#

#$ -e logs/
#$ -o logs/
#$ -cwd
#$ -N TRUTHJOB

if [ -z "$JOB_ID" ]
then
	BINDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
	source $BINDIR/bash_init.sh
fi

MKTRUTH=bin/alignmentToTruth.py

if [ -z "$JOB_ID" ] # SUBMIT MODE
then

	if [ $# -ne 7 ]
	then
		echo "Usage: [afmt] [ofmt] [min len] [min cov] [min id] [alignment input] [output file]"
		exit 1
	fi

	echo "Submitting run"
	trap 'rollback_rm_file $7; exit $?' INT TERM EXIT
	CMD=`readlink -f $0`
	qsub -sync yes -V -v AFMT=$1,OFMT=$2,MINLEN=$3,MINCOV=$4,MINID=$5,INPUT=$6,OUTPUT=$7 $CMD
	trap - INT TERM EXIT
	echo "Finished"

else # EXECUTION MODE
	echo "Running"

    if [ ! -e $INPUT ]
    then
       sleep 5
    fi

    $MKTRUTH --afmt $AFMT --ofmt $OFMT --minlen $MINLEN --mincov $MINCOV --minid $MINID $INPUT $OUTPUT

fi
