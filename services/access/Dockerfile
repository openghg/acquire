FROM openghg/acquire-base:latest

USER root
WORKDIR /function

RUN mkdir $PYTHON_EXT/access

ADD *.py $PYTHON_EXT/access/
RUN python3 -m compileall $PYTHON_EXT/access/*.py

# ADD route.py secret_key ./
ADD route.py ./

USER $FN_USER

ENTRYPOINT ["/python/bin/fdk", "/function/route.py", "route"]
