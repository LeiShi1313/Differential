FROM debian:stable-slim

ARG SETUPTOOLS_SCM_PRETEND_VERSION

RUN mkdir -p /app
COPY . /app
WORKDIR /app
RUN chmod +x install.sh
RUN DIFFERENTIAL_SKIP_INSTALL=1 ./install.sh
ENV PATH=$PATH:/root/.local/bin
RUN pipx install uv
RUN SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION} uv tool install --python python3 .

CMD ["/root/.local/bin/dft"]
