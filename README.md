# Alliance BLAST Database Manager

## Requirements

Items marked with '(dev)' indicate dependencies that are only needed if running natively outside the Docker container.

* Unix / OS X (x86_64 or arm64 platforms)
* Docker
* Python 3.10+ (dev)
* [Poetry](https://python-poetry.org/) (dev)
* gunzip (dev)
* xargs (dev)
* makeblastdb - NCBI BLAST 2.12.0+ (dev)
* git
* wget (dev)
* jq (formatting database metadata from MOD)

## Getting Started

The following requires that you have Docker installed and running on your system.
The `make docker-build` or `make docker-buildx` targets build the container image and the `make docker-run` runs 
the pipeline.

On `x86_64`
```shell
git clone https://github.com/alliance-genome/agr_blastdb_manager.git
cd agr_blastdb_manager
make docker-build
make docker-run
ls -l data/fasta/* data/blast/*
```

On `arm64`
```shell
git clone https://github.com/alliance-genome/agr_blastdb_manager.git
cd agr_blastdb_manager
make docker-buildx
make docker-run
ls -l data/fasta/* data/blast/*
```

`make docker-buildx` builds a multi-platform container.

* Note: You may need to activate the custom docker builder with `docker buildx create --use` first.


## Description

A Snakemake pipeline for automating the aggregation of model organism datasets and production of BLAST databases.

## How to add a new model organism database

1. Create a new `databases.json` file and place it in `conf/<MOD_NAME>/databases.json`. e.g. `conf/flybase/databases.json`.

See the [./conf/metadata_schema.json](metadata schema file) for full details on the format and other existing files for examples.

2. Add a new entry under `mods` for the new configuration file to `conf/global.yaml`.

This tells Snakemake to process this file.

Follow the instructions under **Getting Started**.

