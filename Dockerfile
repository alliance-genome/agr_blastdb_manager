FROM python:3.10

WORKDIR /usr/src/app

COPY dist/*.whl ./

RUN pip install -U pip wheel
RUN pip install --no-cache-dir ./*.whl


CMD ["python","-m","agr_blastdb_manager"]