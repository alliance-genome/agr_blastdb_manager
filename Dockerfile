FROM python:3.10

WORKDIR /usr/src/app

COPY dist/*.whl ./
COPY Snakefile ./
COPY conf/ ./conf/

RUN pip install -U pip wheel
RUN pip install --no-cache-dir ./*.whl

VOLUME ["/usr/src/app/data"]

CMD ["snakemake","-c1"]