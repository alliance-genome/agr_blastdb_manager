FROM python:3.10

WORKDIR /usr/src/app

RUN mkdir logs

RUN wget https://ftp.ncbi.nlm.nih.gov/blast/executables/LATEST/ncbi-blast-2.13.0+-x64-linux.tar.gz \
    && tar zxvf ncbi-blast-2.13.0+-x64-linux.tar.gz

COPY dist/*.whl ./
COPY Snakefile ./
COPY conf/ ./conf/

RUN pip install -U pip wheel
RUN pip install --no-cache-dir ./*.whl

VOLUME ["/usr/src/app/data", "/usr/src/app/logs"]

CMD ["snakemake","-c1","--config", "MAKEBLASTDB_BIN=/usr/src/app/ncbi-blast-2.13.0+/bin/makeblastdb"]