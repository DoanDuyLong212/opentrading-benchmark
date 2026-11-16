# v4.7 shared shell sandbox (decision 2026-11-16, 6b): every arm's shell command runs here, unfiltered,
# with no network and only the trial's workspace and temp folder mounted (runners/sandbox/run.ts).
FROM python@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
RUN apt-get update && apt-get install -y --no-install-recommends gawk bc && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir numpy==2.1.3 pandas==2.2.3
ENV LC_ALL=C.UTF-8 PYTHONDONTWRITEBYTECODE=1
