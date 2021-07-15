#!/bin/bash

cd base_image && ./build_and_push.sh && cd -
cd identity && bash deploy_all.sh && cd -
cd access && bash deploy_all.sh && cd -
cd accounting && bash deploy_all.sh && cd -
cd storage && bash deploy_all.sh && cd -
cd compute && bash deploy_all.sh && cd -
cd registry && bash deploy_all.sh
