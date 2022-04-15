# Declare NCBI BLAST version before FROM statements.
ARG BLAST_VERSION=2.13.0

# Pull in NCBI container with BLAST binaries.
FROM ncbi/blast:${BLAST_VERSION} AS ncbi-blast

# Use the python 3.10 image as a base.
# The slim and alpine python images did not work.
FROM python:3.10 AS agr_blastdb_manager

# Copy BLAST binaries and lib from NCBI image into the agr_blastdb_manager image.
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

WORKDIR /usr/src/app

COPY dist/*.whl ./
COPY Snakefile ./
COPY conf/ ./conf/

RUN pip install -U pip wheel
RUN pip install --no-cache-dir ./*.whl

RUN mkdir logs .snakemake

VOLUME ["/usr/src/app/data", "/usr/src/app/logs", "/usr/src/app/.snakemake", "/.cache"]

ENTRYPOINT [ "snakemake", "--config", "MAKEBLASTDB_BIN=/blast/bin/makeblastdb" ]
CMD [ "-c1" ]
