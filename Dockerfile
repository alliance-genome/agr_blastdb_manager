# Declare NCBI BLAST version before FROM statements.
ARG BLAST_VERSION=2.13.0

# Stage 1 - Poetry build process to build the wheel install file.
FROM python:3.10 AS builder
WORKDIR /app

# Files required for the python package.
COPY pyproject.toml poetry.lock README.md LICENSE /app/
COPY agr_blastdb_manager /app/agr_blastdb_manager

# Setup poetry and run the build.
RUN pip install poetry
RUN poetry config virtualenvs.in-project true
RUN poetry install --no-ansi
RUN poetry build --format wheel --no-ansi

# Pull in NCBI container with BLAST binaries.
FROM ncbi/blast:${BLAST_VERSION} AS ncbi-blast

# Use the python 3.10 image as a base.
# The slim and alpine python images did not work.
FROM python:3.10 AS agr_blastdb_manager

WORKDIR /app

# Copy python wheel install file and BLAST libraries/binaries from NCBI image into the agr_blastdb_manager image.
COPY --from=builder    /app/dist /app/dist/
COPY --from=ncbi-blast /blast/lib /blast/lib/
COPY --from=ncbi-blast /blast/bin/blast_formatter /blast/bin/
COPY --from=ncbi-blast /blast/bin/blastdbcmd /blast/bin/
COPY --from=ncbi-blast /blast/bin/blastn.REAL /blast/bin/blastn
COPY --from=ncbi-blast /blast/bin/blastp.REAL /blast/bin/blastp
COPY --from=ncbi-blast /blast/bin/blastx.REAL /blast/bin/blastx
COPY --from=ncbi-blast /blast/bin/makeblastdb /blast/bin
COPY --from=ncbi-blast /blast/bin/tblastn.REAL /blast/bin/tblastn
COPY --from=ncbi-blast /blast/bin/tblastx.REAL /blast/bin/tblastx

# Add BLAST binaries to PATH.
ENV PATH=/blast/bin:${PATH}

# Copy Snakemake pipeline files.
COPY Snakefile ./
COPY conf/ ./conf/

# Install the wheel package.
RUN pip install -U pip wheel
RUN pip install --no-cache-dir ./dist/*.whl

RUN mkdir logs .snakemake

VOLUME ["/app/data", "/app/logs", "/app/.snakemake", "/.cache"]

ENTRYPOINT [ "snakemake", "--config", "MAKEBLASTDB_BIN=/blast/bin/makeblastdb" ]
CMD [ "-c1" ]
