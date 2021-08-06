FROM openghg/acquire-base:latest

USER root
WORKDIR /function

RUN mkdir $PYTHON_EXT/registry

ADD *.py $PYTHON_EXT/registry/
RUN python3 -m compileall $PYTHON_EXT/registry/*.py

ADD route.py secret_key ./

USER $FN_USER

ENTRYPOINT ["/python/bin/fdk", "/function/route.py", "handle_invocation"]
