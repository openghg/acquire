#!/bin/bash
# export FN_REGISTRY=chryswoods
fn create app compute
fn --verbose deploy --local --all
rm secret_key