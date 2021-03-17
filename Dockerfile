FROM apluslms/grading-base:3.2

RUN apt_install \
    g++ \
    gcc \
    libc-dev \
    make \
    valgrind
