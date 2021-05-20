FROM apluslms/grading-base:3.2

RUN apt_install \
    g++ \
    gcc \
    libc-dev \
    make \
    valgrind

COPY gcheck/gcheck /gcheck
RUN rm -rf /gcheck/.git

RUN make -C /gcheck static

# Add the gcheck variables to /gcheck.env
COPY gcheck/Makefile /Makefile
RUN make -s -C / > /gcheck.env
RUN rm /Makefile
