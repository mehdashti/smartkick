#!/bin/sh

# Start RabbitMQ in the background
rabbitmq-server &

# Wait for RabbitMQ to start
until rabbitmqctl await_startup; do
  echo "Waiting for RabbitMQ to start..."
  sleep 1
done

# Create the smartkick vhost
rabbitmqctl add_vhost smartkick

# Grant full permissions to the guest user for the smartkick vhost
rabbitmqctl set_permissions -p smartkick guest ".*" ".*" ".*"

# Keep the container running
wait
