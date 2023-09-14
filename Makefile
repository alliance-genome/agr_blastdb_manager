#!/usr/bin/make
PERL_SPLIT = perl -n -e '($$key, $$val) = split /\s*=\s*/, $$_, 2; print $$val;'

# Get the version from the pyproject.toml file.
VERSION     := $(shell grep '^version' pyproject.toml | $(PERL_SPLIT))
DOCKER_TAG  := agr_blastdb_manager
NUM_CORES   := 2
CURRENT_UID := $(shell id -u)
CURRENT_GID := $(shell id -g)
CURRENT_DIR := $(shell pwd)
CONFIG_DIR := $(shell pwd)/conf
DIST_DIR    := dist
DATA_DIR    := data

all: docker-build docker-run

# Generate the BLAST database metadata schema file.
conf/metadata_schema.json:
	snakemake -c1 -f $@

conf/flybase/databases.json:
	poetry run ./scripts/create_flybase_metadata.py --email $(FB_EMAIL) --release $(FB_RELEASE) --dmel-annot $(DMEL_RELEASE) > $@

conf/wormbase/databases.json:
	wget ftp://ftp.ebi.ac.uk/pub/databases/wormbase/misc_datasets/AGR/blast_meta.wormbase.json -q -O - | jq '.' > $@

conf/sgd/databases.json:
	wget https://www.qa.yeastgenome.org/webservice/sgd_blast_metadata -q -O - | jq '.' > $@

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

docker-run-help:
	docker run --user $(CURRENT_UID):$(CURRENT_GID) --rm \
               -v $(CURRENT_DIR)/data:/workflow/data \
               -v $(CURRENT_DIR)/logs:/workflow/logs \
	       -v $(CONFIG_DIR):/conf \
               $(DOCKER_TAG):$(VERSION)

build: $(DIST_DIR)/%.whl

$(DIST_DIR)/%.whl:
	poetry build

format:
	black agr_blastdb_manager scripts

docker-run:
	docker run --user $(CURRENT_UID):$(CURRENT_GID) --rm \
               -v $(CURRENT_DIR)/data:/data \
               -v $(CURRENT_DIR)/logs:/logs \
	       -v $(CONFIG_DIR):/conf \
               $(DOCKER_TAG):$(VERSION) \
               /bin/bash -c "python src/create_blast_db.py --config_yaml=/conf/global.yaml"




.PHONY: docker-build docker-run clean clean-fasta clean-blast clean-meta clean-all-blast build format
