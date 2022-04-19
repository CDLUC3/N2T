# N2T Python Implementation

This is a reimplementation of N2T using python.

The current[^1] status is EXPERIMENTAL, INCOMPLETE, and likely to change significantly.

N2T is an identifier resolver / redirection service that supports many identifier 
schemes. Visit the [N2T site](https://n2t.net/e/about.html) for more information 
about the current production system.

## Components

The source data for N2T is the YAML source located at: https://n2t.net/e/n2t_full_prefixes.yaml

The following are provided here:

`n2t` is a command line tool for working with the prefix list.

`lib_n2t` implements a model for resolvers and mechanisms for transforming to different formats.

`micron2t` is a minimal web service implemented with FastAPI implementing the core functionality of N2T.


## Developer Setup

```
git clone https://github.com/CDLUC3/N2T.git
cd N2T
mkvirtualenv n2t
poetry install
```

Running micron2t:

```
wget -O data/prefixes.yaml https://n2t.net/e/n2t_full_prefixes.yaml 
n2t n2t_full_prefixes.yaml topython > micron2t/data/__init__.py
cd micron2t
uvicorn --reload main:app
```

Deployment to Deta is through a GH Action. Available as a Deta micro at https://rslv.deta.dev

## `micron2t`

Provides API documentation at `/docs`

`/` Returns a list of supported prefixes

`/{identifier}` Returns information about the identifier and other behavior.

If the `identifier` has no colon, then it is treated as a prefix and prefix metadata is returned in JSON.

If the `identifier` has a colon and the pattern matches, then a redirect response is returned unless a request is made
with `Accept: application/json;profile=https://rslv.xyz/info`, in which case information about the intended action 
is returned.



[^1]: As of 2021-12-07
