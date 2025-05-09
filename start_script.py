#!/bin/sh
while true; do
    python3 /root/paladin/paladin.py
    sleep 10  # Restart if it crashes
done

