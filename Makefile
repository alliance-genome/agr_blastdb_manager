#!/usr/bin/make
PERL_SPLIT = perl -n -e '($$key, $$val) = split /\s*=\s*/, $$_, 2; print $$val;'

# Get the version from the pyproject.toml file.
VERSION     := $(shell grep '^version' pyproject.toml | $(PERL_SPLIT))
DOCKER_TAG  := agr_blastdb_manager
NUM_CORES   := 2
CURRENT_UID := $(shell id -u)
CURRENT_GID := $(shell id -g)
CURRENT_DIR := $(shell pwd)

DIST_DIR    := dist
DATA_DIR    := data

all: docker-build docker-run

clean-fasta:
	rm -rf $(DATA_DIR)/fasta/*

clean-meta:
	rm -rf $(DATA_DIR)/meta/*

clean-blast:
	rm -rf $(DATA_DIR)/blast/*

clean-all-blast: clean-fasta clean-blast clean-meta

clean:
	rm -f $(DIST_DIR)/*.{gz,whl}

docker-build:
	docker build --tag $(DOCKER_TAG):$(VERSION) .

docker-run:
	docker run --user $(CURRENT_UID):$(CURRENT_GID) --rm -it -v $(CURRENT_DIR)/data:/usr/src/app/data \
               -v $(CURRENT_DIR)/logs:/usr/src/app/logs -v $(CURRENT_DIR)/.snakemake:/usr/src/app/.snakemake \
               -v $(CURRENT_DIR)/.cache:/.cache $(DOCKER_TAG)

build: $(DIST_DIR)/%.whl

$(DIST_DIR)/%.whl:
	poetry build

.PHONY: docker-build docker-run clean clean-fasta clean-blast clean-meta clean-all-blast build
