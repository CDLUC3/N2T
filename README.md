# N2T Python Implementation

This is a reimplementation of N2T using python.

The current^1 status is EXPERIMENTAL, INCOMPLETE, and likely to change significantly.

N2T is an identifier resolver / redirection service that supports many identifier 
schemes. Visit the [N2T site])https://n2t.net/e/about.html_ for more information 
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
wget https://n2t.net/e/n2t_full_prefixes.yaml 
n2t n2t_full_prefixes.yaml topython > micron2t/data/__init__.py
cd micron2t
uvicorn main:app
```


^1: As of 2021-12-07