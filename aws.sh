#!/bin/bash
set -e
export AWS_PROFILE=''

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <>.dkr.ecr.us-east-1.amazonaws.com

images=('busybox' 'alpine' 'swarm' 'kong' 'hello-world')
tags=( '2' '3' '4' '5')
for image in "${images[@]}"
do
    echo $image
    # aws ecr create-repository --repository-name ${image}
    # docker pull ${image}:latest
    for tag in "${tags[@]}"
    do
        # docker tag ${image}:latest <>.dkr.ecr.us-east-1.amazonaws.com/${image}:${tag}
        docker push <>.dkr.ecr.us-east-1.amazonaws.com/${image}:${tag}
    done
done