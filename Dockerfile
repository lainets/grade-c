FROM apluslms/grading-base:3.2

RUN apt_install \
    g++ \
    gcc \
    libc-dev \
    make \
    valgrind \
    python3 \
    python3-pip

COPY gcheck/templates /templates

COPY gcheck/gcheck /gcheck
RUN rm -rf /gcheck/.git

RUN make -C /gcheck static

ENV PYTHONPATH "${PYTHONPATH}:/gcheck/tools"

RUN python3 -m pip install jinja2 pyyaml

# The build flags
COPY gcheck/gcheck.env /gcheck.env
# Append the gcheck variables to /gcheck.env
COPY gcheck/Makefile /Makefile
RUN printf "\n" >> /gcheck.env
RUN make -s -C / >> /gcheck.env
RUN rm /Makefile

COPY gcheck/gcheck.py /entrypoint/
RUN chmod +x /entrypoint/gcheck.py
CMD ["/entrypoint/gcheck.py"]
