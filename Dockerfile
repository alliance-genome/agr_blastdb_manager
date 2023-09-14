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

RUN pip install -U pip wheel
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry lock --no-update
RUN poetry install  --no-interaction --no-ansi

RUN file="$(ls -1 .)" && echo $file
RUN file="$(ls -1 src)" && echo $file

VOLUME ["/workflow/data", "/workflow/logs", "/conf"]
CMD ["python", "src/create_blast_db.py", "--help"]
