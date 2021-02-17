#!/bin/bash

cd base_image && ./build_and_push.sh && cd -
cp secret_key identity/
cd identity && bash deploy_all.sh && cd -
cp secret_key access/
cd access && bash deploy_all.sh && cd -
cp secret_key accounting/
cd accounting && bash deploy_all.sh && cd -
cp secret_key storage/
cd storage && bash deploy_all.sh && cd -
cp secret_key compute/
cd compute && bash deploy_all.sh && cd -
cp secret_key registry/
cd registry && bash deploy_all.sh
