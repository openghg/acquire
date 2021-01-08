FROM openghg/acquire-base:latest

# Need to be user root or Fn exits with
# {"message":"internal server error"}
USER root
WORKDIR /function

RUN mkdir $PYTHON_EXT/access

ADD *.py $PYTHON_EXT/access/
RUN python3 -m compileall $PYTHON_EXT/access/*.py

# ADD route.py secret_key ./
ADD route.py ./

# ENTRYPOINT ["python", "route.py"]
USER $FN_USER

ENTRYPOINT ["/python/bin/fdk", "/function/route.py", "route"]
