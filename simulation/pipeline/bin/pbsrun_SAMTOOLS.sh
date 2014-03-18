#!/bin/bash

#
# Samtools on simulation
#

#PBS -q smallq
#PBS -l select=1:ncpus=1:mem=32gb
#PBS -N SAMTOOLSJOB

if [ -z "$PBS_ENVIRONMENT" ] # SUBMIT MODE
then

	echo "Submitting run"
	qsub -W block=true $0

else # EXECUTION MODE
	echo "Running"
	cd $PBS_O_WORKDIR
	
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
