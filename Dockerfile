FROM python:3.10.2-bullseye
ARG UID=1337
ARG GID=1337

<<<<<<< HEAD
RUN pip3 install cachecontrol requests lockfile pydantic
=======
RUN pip install cachecontrol requests lockfile packaging pydantic \
    && apt-get update && apt-get install -y rsync cron
>>>>>>> 9098cb1 (fix: update dependencies)

# add our cronjob
COPY docker/update.cron /etc/cron.d/meta-update
RUN chmod 644 /etc/cron.d/meta-update \
    && crontab /etc/cron.d/meta-update

# install entrypoint
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint

RUN groupadd -g $GID user \
    && useradd -m -g $GID -u $UID user \
    && mkdir -p /home/user/.ssh \
    && ssh-keyscan github.com > /home/user/.ssh/known_hosts \
    && mkdir -p /app \
    && chown -R $UID:$GID /app /home/user/.ssh

COPY . /app/

ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["update"]
