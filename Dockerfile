FROM debian:stable-slim

ARG PDM_BUILD_SCM_VERSION

RUN mkdir -p /app
COPY . /app
WORKDIR /app
RUN chmod +x install.sh
RUN ./install.sh
ENV PATH=$PATH:/root/.local/bin
RUN pipx install pdm
RUN PDM_BUILD_SCM_VERSION=${PDM_BUILD_SCM_VERSION} pdm install --check --prod --no-editable --global --project .

CMD ["/root/.local/bin/dft"]