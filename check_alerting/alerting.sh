#!/bin/bash

echo "Start trace receiver"
.venv/bin/trace_receiver &

echo "Start notifier"
.venv/bin/notifier