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
	docker build --tag $(DOCKER_TAG):$(VERSION) --tag $(DOCKER_TAG):latest .

docker-buildx:
	docker buildx build --platform linux/arm64,linux/amd64 --tag $(DOCKER_TAG):$(VERSION) --tag $(DOCKER_TAG):latest .

docker-run:
	docker run --user $(CURRENT_UID):$(CURRENT_GID) --rm -it -v $(CURRENT_DIR)/data:/app/data \
               -v $(CURRENT_DIR)/logs:/app/logs -v $(CURRENT_DIR)/.snakemake:/app/.snakemake \
               -v $(CURRENT_DIR)/.cache:/.cache $(DOCKER_TAG):$(VERSION)

build: $(DIST_DIR)/%.whl

$(DIST_DIR)/%.whl:
	poetry build

format:
	black agr_blastdb_manager

.PHONY: docker-build docker-run clean clean-fasta clean-blast clean-meta clean-all-blast build format
