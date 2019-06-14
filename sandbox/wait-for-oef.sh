#!/usr/bin/env bash
# wait-for-oef.sh

host="$1"
port="$2"
cmd="${@:3}"

echo "Waiting for OEF up"

until python3 sandbox/oef_healthcheck.py $host $port; do
  >&2 echo "OEF is not available - sleeping for 1 second..."
  sleep 1
done

>&2 echo "OEF is up - executing command"


echo "Executing $cmd"
exec $cmd
