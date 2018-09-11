#!/bin/bash

if [[ $1 == 'mock' ]]; then
  foreman start -f ./Procfile.mock
else
  . .dbrc
  . venv/bin/activate
  foreman start
fi

