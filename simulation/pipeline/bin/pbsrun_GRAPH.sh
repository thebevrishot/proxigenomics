#!/bin/bash

if [ -z "$PBS_ENVIRONMENT" ]
then
	BINDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
	source $BINDIR/bash_init.sh
fi

#
# Create graph files
#


#PBS -q smallq
#PBS -l select=1:ncpus=2:mem=32gb
#PBS -e logs/
#PBS -o logs/
#PBS -N GRAPHJOB

SAMTOEDGES=bin/samToEdges.py

if [ -z "$PBS_ENVIRONMENT" ] # SUBMIT MODE
then
	
	if [ $# -ne 4 ]
	then
		echo "Usage: [hic2ctg.sam] [wgs2ctg.bam] [edge out] [node out]"
		exit 1
	fi

	echo "Submitting run"
	TARGET=( $3 $4 )
	trap 'rollback_rm_files ${TARGET[@]}; exit $?' INT TERM EXIT
	qsub -W block=true -v HIC2CTG=$1,WGS2CTG=$2,EDGES=$3,NODES=$4 $0
	trap - INT TERM EXIT
	echo "Finished"

else # EXECUTION MODE
	echo "Running"
	cd $PBS_O_WORKDIR
	
	$SAMTOEDGES ${HIC2CTG} ${WGS2CTG%.bam}.idxstats $EDGES $NODES
	
fi
