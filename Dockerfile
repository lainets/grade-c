FROM apluslms/grading-base:3.1

RUN apt_install \
    g++ \
    gcc \
    libc-dev \
    make
