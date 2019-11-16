#!/usr/bin/env bash

curl -o items.json "http://localhost:8080/rest/items?recursive=false&fields=name%2Clabel%2Ctype%2Ceditable%2Cmetadata&metadata=semantics%2Csynonyms"