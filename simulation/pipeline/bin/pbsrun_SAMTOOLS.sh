#!/bin/bash

#
# Samtools on simulation
#

#PBS -q smallq
#PBS -l select=1:ncpus=1:mem=32gb
#PBS -e logs/
#PBS -o logs/
#PBS -N SAMTOOLSJOB

if [ -z "$PBS_ENVIRONMENT" ]
then
	BINDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
	source $BINDIR/bash_init.sh
fi

if [ -z "$PBS_ENVIRONMENT" ] # SUBMIT MODE
then

	echo "Submitting run"
	INPUT=("$@")
	TARGET=(  )
	trap 'rollback_rm_files ${TARGET[@]}; exit $?' INT TERM EXIT
	qsub -W block=true -v FILEPATH=$1 $0
    trap - INT TERM EXIT
	echo "Finished"

else # EXECUTION MODE
	echo "Running"
	cd $PBS_O_WORKDIR
	cd $FILEPATH
	
	# For all sams, make sorted index bams and then some stat files
	for sf in `find -maxdepth 1 -name '*.sam'`
	do
		bf=${sf%.sam}
		samtools view -bS $sf | samtools sort - $bf
		samtools index ${bf}.bam
		samtools idxstats ${bf}.bam > ${bf}.idxstats
		samtools flagstat ${bf}.bam > ${bf}.flagstat
	done
	
fi
