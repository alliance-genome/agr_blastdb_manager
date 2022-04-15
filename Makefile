#!/usr/bin/make

DOCKER_TAG  := agr_blastdb_manager
NUM_CORES   := 2
CURRENT_UID := $(shell id -u)
CURRENT_GID := $(shell id -g)

clean-fasta:
	rm -rf data/fasta/*

clean-meta:
	rm -rf data/meta/*

clean-blast:
	rm -rf data/blast/*

clean: clean-fasta clean-blast clean-meta

build:
	docker build --tag $(DOCKER_TAG) .

run:
	docker run --user $(CURRENT_UID):$(CURRENT_GID) --rm -it -v $PWD/data:/usr/src/app/data \
               -v $PWD/logs:/usr/src/app/logs -v $PWD/.snakemake:/usr/src/app/.snakemake \
               -v $PWD/.cache:/.cache $(DOCKER_TAG)


.PHONY: build run clean clean-fasta clean-blast clean-meta