#!/bin/bash
#To create a xcat service, and container in docker swarm env
docker stack deploy -c ./docker-compose.yml xcat_stack
