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


