FROM python:3.10 AS agr_blastdb_manager
ARG BLAST_VERSION=2.13.0
ARG BLAST_TARBALL=ncbi-blast-${BLAST_VERSION}+-x64-linux.tar.gz
ARG BLAST_URI=https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/${BLAST_VERSION}/${BLAST_TARBALL}

WORKDIR /blast

# Download and extract NCBI BLAST
RUN wget --quiet $BLAST_URI && \
    tar zxf $BLAST_TARBALL && \
    mv ncbi-blast-${BLAST_VERSION}+/* ./

ENV PATH=/blast/bin:${PATH}

WORKDIR /workflow

COPY . .

# uv, pinned. The project moved to uv in 2025-08 but this file kept driving
# poetry, which no longer has a [tool.poetry] section to read -- so the image
# was resolving dependencies by a different route than uv.lock describes.
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /bin/uv

# --locked fails rather than silently re-resolving, so the image and uv.lock
# cannot drift apart. --no-dev keeps black, pillow, locust and the rest of the
# test tooling out of a production image; they were being installed before.
RUN uv sync --locked --no-dev

ENV PATH=/workflow/.venv/bin:${PATH}

VOLUME ["/workflow/data", "/workflow/logs", "/conf"]
CMD ["python", "src/create_blast_db.py", "--help"]
