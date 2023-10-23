# Sciety Labs (Experimental)

[Sciety Labs](https://labs.sciety.org/) is a place for early stage experiments related to discovery of preprints and the Sciety community. We will test out some ideas before adding them to [Sciety](https://sciety.org/).

## Prerequisites

* [Google Gloud SDK](https://cloud.google.com/sdk/docs/) for [gcloud](https://cloud.google.com/sdk/gcloud/)

When using a Python virtual environment:

* [Python 3](https://www.python.org/) ([pyenv](https://github.com/pyenv/pyenv) recommended)

When using Docker:

* [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)

## Credentials

### GCP credentials

A user with access to BigQuery in the `elife-data-pipeline` GCP project. Login via:

```bash
gcloud auth application-default login
```

### Twitter API token

The `TWITTER_API_AUTHORIZATION_FILE_PATH` environment variable (set by the `Makefile`) will point to:
`.secrets/twitter_api_authorization.txt`

The file contents should look like:

```text
Bearer <Twitter API token>
```

If the file is not present, the app will still start but the Twitter related endpoint will not work.

### OpenSearch

When configured, it will use OpenSearch instead of BigQuery to look up Semantic Scholar paper ids.

| name | description |
| ---- | ----------- |
| OPENSEARCH_HOST | Hostname to OpenSearch |
| OPENSEARCH_PORT | Port to OpenSearch, e.g. 9200 |
| OPENSEARCH_USERNAME_FILE_PATH | File path to file containing the username |
| OPENSEARCH_PASSWORD_FILE_PATH | File path to file containing the password |
| OPENSEARCH_INDEX_V2_NAME | The index to use |
| OPENSEARCH_EMBEDDING_VECTOR_MAPPING_NAME | Optional. When specified, it will use the OpenSearch embedding vector mapping to provide article recommendations for a single article (not yet used for lists). Otherwise it will continue to use Semantic Scholar. |

## Configuration

The following environment variables can be used to configure the site:

| name | description |
| ---- | ----------- |
| SCIETY_LABS_COOKIEBOT_IDENTIFIER | The cookiebot identifier. (Not included if blank) |
| SCIETY_LABS_GOOGLE_TAG_MANAGER_ID | The Google Tag Manager (GTM) id. (Not included if blank) |

## Development using a Python Virtual Environment (venv)

### Install Python via pyenv

[pyenv](https://github.com/pyenv/pyenv) as recommended as it makes it easier to install multiple Python versions side by side.

The Python version for this project is configured in [.python-version](.python-version).

### First venv setup

This will create the virtual environment and install dependencies.

```bash
make dev-venv
```

### Install or update dependencies (from requirements)

```bash
make dev-install
```

### Run linting and unit tests

```bash
make dev-test
```

### Watch unit tests

```bash
make dev-watch
```

### Start server

```bash
make dev-start
```

## Development using a Docker

### Build

```bash
make build
```

### Start server (using Docker)

```bash
make start
```

### View Docker Compose logs

```bash
make logs
```

### Stop server (using Docker)

```bash
make stop
```
