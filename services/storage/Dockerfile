FROM openghg/acquire-base:latest

USER root
WORKDIR /function

RUN mkdir $PYTHON_EXT/storage

ADD *.py $PYTHON_EXT/storage/
RUN python3 -m compileall $PYTHON_EXT/storage/*.py

# ADD route.py secret_key ./
ADD route.py ./

USER $FN_USER

ENTRYPOINT ["/python/bin/fdk", "/function/route.py", "route"]
