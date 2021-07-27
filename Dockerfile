ARG BASE_TAG=latest
FROM apluslms/grading-base:$BASE_TAG

RUN apt_install \
    g++ \
    gcc \
    libc-dev \
    make \
    valgrind \
    python3 \
    python3-pip

RUN python3 -m pip install jinja2 pyyaml

# gcheck files
COPY gcheck/run.py /gcheck/run.py
COPY gcheck/templates /gcheck/templates
COPY gcheck/gcheck /gcheck/gcheck
RUN rm -rf /gcheck/gcheck/.git

RUN make -C /gcheck/gcheck static

COPY util.py /util.py


ENV PYTHONPATH "${PYTHONPATH}:/gcheck/gcheck/tools:/"

# The build flags
COPY compile.env /compile.env
COPY compile.env /gcheck/gcheck.env
# Add the gcheck build flags to /gcheck/gcheck.env
COPY gcheck/Makefile /Makefile
RUN printf "\n" >> /gcheck/gcheck.env
RUN make -s -C / >> /gcheck/gcheck.env
RUN rm /Makefile


COPY run.py /entrypoint/
RUN chmod +x /entrypoint/run.py
CMD ["/entrypoint/run.py"]
