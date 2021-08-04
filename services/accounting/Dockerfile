FROM openghg/acquire-base:latest

USER root
WORKDIR /function

RUN mkdir $PYTHON_EXT/accounting

ADD *.py $PYTHON_EXT/accounting/
RUN python3 -m compileall $PYTHON_EXT/accounting/*.py

ADD route.py secret_key ./

USER $FN_USER

ENTRYPOINT ["/python/bin/fdk", "/function/route.py", "handle_invocation"]
