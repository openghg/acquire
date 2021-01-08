#!/bin/bash

rsync -a --verbose ../../Acquire . --exclude '__pycache__'
rsync -a --verbose ../admin . --exclude '__pycache__'

docker build --no-cache -t openghg/acquire-base:latest .

rm -rf Acquire admin

#docker push chryswoods/acquire-base:latest

#docker run --rm -it chryswoods/acquire-base:latest
