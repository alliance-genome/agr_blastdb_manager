#!/usr/bin/make
PERL_SPLIT = perl -n -e '($$key, $$val) = split /\s*=\s*/, $$_, 2; print $$val;'

# Get the version from the pyproject.toml file.
VERSION     := $(shell grep '^version' pyproject.toml | $(PERL_SPLIT))
DOCKER_TAG  := agr_blastdb_manager
NUM_CORES   := 2
CURRENT_UID := $(shell id -u)
CURRENT_GID := $(shell id -g)

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
	rm $(DIST_DIR)/*.{gz,whl}

docker-build:
	docker build --tag $(DOCKER_TAG):$(VERSION) .

docker-run:
	docker run --user $(CURRENT_UID):$(CURRENT_GID) --rm -it -v $PWD/data:/usr/src/app/data \
               -v $PWD/logs:/usr/src/app/logs -v $PWD/.snakemake:/usr/src/app/.snakemake \
               -v $PWD/.cache:/.cache $(DOCKER_TAG)

build: $(DIST_DIR)/%.whl

$(DIST_DIR)/%.whl:
	poetry build

.PHONY: docker-build docker-run clean clean-fasta clean-blast clean-meta clean-all-blast build