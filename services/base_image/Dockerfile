# Build and install dependencies into the build container
FROM fnproject/python:3.8.5-dev as build-stage

WORKDIR $HOME

# # Install libraries needed by python dependencies
# RUN apt-get update && \
#     apt-get install --no-install-recommends -qy \
#     build-essential \
#     gcc \
#     cmake \
#     libgnutls28-dev \
#     libcurl4-gnutls-dev && \
#     apt-get clean

ADD requirements.txt .

# Fixing pip version here as the last version before the new resolver was introduced
RUN pip3 install -U pip==20.2.4 setuptools wheel
RUN pip3 install --target /python/ --no-cache --no-cache-dir -r requirements.txt
RUN rm -rf requirements.txt

ENTRYPOINT ["bash"]

# Now transfer what is needed to the production container
FROM fnproject/python:3.8.5

# Configure environment
ENV SHELL=/bin/bash \
    FN_USER=fnuser \
    FN_GID=100

ENV HOME=/function
COPY --from=build-stage /function $HOME

ADD fix-permissions /usr/bin/fix-permissions

# Create fn user with UID=1000 and in the 'users' group
# and make sure these dirs are writable by the `users` group.
RUN useradd -m -s /bin/bash $FN_USER

WORKDIR /function

COPY --from=build-stage /python /python

RUN mkdir /extralibs

ENV PYTHONPATH=/python \
    LD_LIBRARY_PATH=/extralibs:$LD_LIBRARY_PATH

# Copy in the updated version of oci's __init__.py that we
# have fixed to lazy load modules (thereby making it much quicker)
# ADD fixed/fast_oci__init__.py /python/oci/__init__.py
# ADD fixed/fast_oci_object_storage__init__.py /python/oci/object_storage/__init__.py
#ADD fixed/fast_oci_object_storage_models__init__.py /python/oci/object_storage/models/__init__.py
#ADD fixed/fast_oci__vendor__init__.py /python/oci/_vendor/__init__.py

# ADD fixed/fast_fdk__init__.py /python/fdk/__init__.py

# Add the function last as this is the thing that will change most often
ENV PYTHON_EXT=/python/acquire_services

RUN mkdir $PYTHON_EXT
ADD Acquire $PYTHON_EXT/Acquire
ADD admin $PYTHON_EXT/admin

ENV PYTHONPATH=$PYTHONPATH:$PYTHON_EXT

RUN python3 -m compileall $PYTHON_EXT/Acquire/*
RUN python3 -m compileall $PYTHON_EXT/admin/*

ENTRYPOINT ["bash"]

# Become the $FN_USER so that nothing runs as root
USER $FN_USER
