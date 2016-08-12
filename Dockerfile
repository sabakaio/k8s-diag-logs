FROM alpine:3.4

COPY requirements.txt /opt/
RUN set -x \
    && apk update \
    && apk upgrade \

    && apk add --virtual builddeps \
        curl \

    && apk add python3 \
    && pip3 install --no-cache-dir --disable-pip-version-check -U pip \
    && pip3 install --no-cache-dir --disable-pip-version-check -r /opt/requirements.txt \

    && curl -sSL -o /usr/bin/gosu 'https://github.com/tianon/gosu/releases/download/1.9/gosu-amd64' \
    && chmod +x /usr/bin/gosu \

    && apk del --purge builddeps \
    && sh -c 'rm -fr /tmp/* /var/cache/apk/*'

COPY etc/ /etc/
COPY metrics.py /opt/metrics.py

CMD ["init"]
