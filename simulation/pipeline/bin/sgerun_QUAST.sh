#!/bin/bash

#
# Align query to subject
#

#$ -e logs/
#$ -o logs/
#$ -cwd
#$ -N QUASTJOB

if [ -z "$JOB_ID" ]
then
	BINDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
	source $BINDIR/bash_init.sh
fi

SPLITFASTA=bin/split_fasta.py
METAQUAST=external/quast/metaquast.py

if [ -z "$JOB_ID" ] # SUBMIT MODE
then
	if [ $# -ne 3 ]
	then
		echo "Usage: <REFSEQ> <CONTIGS> <OUTPUT REPORT PATH>"
		exit 1
	fi

	echo "Submitting run"
	#trap 'rollback_rm_file $4; exit $?' INT TERM EXIT
	qsub -sync yes -V -pe smp 4 -v REF=$1,CTG=$2,OUTPUT=$3 $0
	#trap - INT TERM EXIT
	echo "Finished"

else # EXECUTION MODE
	echo "Running"
	echo "Ref $REF"
	echo "Ctg $CTG"

	# refering to report.html in summary directory,
	# we have gone down two levels in hierarchy because
	# we need to refer to a final target file for SCONS.
	# this happens to be "summary/report.html"
	SUMDIR=${OUTPUT%/*}
	TOPDIR=${SUMDIR%/*}

	# split reference fasta so that genomes are treated as species for error testing
	mkdir -p $TOPDIR/refs
	$SPLITFASTA -f $REF $TOPDIR/refs

	# get the resulting files (they are named by their ids)
	REF_FILES=`find $TOPDIR/refs -type f -name "*.fasta" | sort | tr '\n' ',' | sed 's/,$//'`

	$METAQUAST -t $NSLOTS -R $REF_FILES -o $TOPDIR $CTG
fi
