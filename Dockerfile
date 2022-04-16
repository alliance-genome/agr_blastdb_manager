# Stage 1 - Poetry build process to build the wheel install file.
FROM python:3.10 AS builder
WORKDIR /app

# Files required for the python package.
COPY pyproject.toml poetry.lock README.md LICENSE /app/
COPY agr_blastdb_manager /app/agr_blastdb_manager

# Setup poetry and run the build.
RUN pip install -U pip wheel && \
    pip install poetry && \
    poetry config virtualenvs.in-project true && \
    poetry install --no-ansi && \
    poetry build --format wheel --no-ansi

# Stage 2 - Building base application image.
# Use the python 3.10 image as a base.
# The slim and alpine python images did not work.
FROM python:3.10 AS agr_blastdb_manager
ARG BLAST_VERSION=2.13.0
ARG BLAST_TARBALL=ncbi-blast-${BLAST_VERSION}+-x64-linux.tar.gz
ARG BLAST_URI=https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/${BLAST_VERSION}/${BLAST_TARBALL}

WORKDIR /blast

# Download and extract NCBI BLAST
RUN wget --quiet $BLAST_URI && \
    tar zxf $BLAST_TARBALL && \
    mv ncbi-blast-${BLAST_VERSION}+/* ./

WORKDIR /app

# Copy python wheel install file into the agr_blastdb_manager image.
COPY --from=builder    /app/dist /app/dist/

# Add BLAST binaries to PATH.
ENV PATH=/blast/bin:${PATH}

# Copy Snakemake pipeline files.
COPY Snakefile ./
COPY conf/ ./conf/

# Install the wheel package.
RUN pip install -U pip wheel && \
    pip install --no-cache-dir ./dist/*.whl && \
    mkdir logs .snakemake

VOLUME ["/app/data", "/app/logs", "/app/.snakemake", "/.cache"]

ENTRYPOINT [ "snakemake", "--config", "MAKEBLASTDB_BIN=/blast/bin/makeblastdb" ]
CMD [ "-c1" ]
