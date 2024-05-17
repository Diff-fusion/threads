#!/bin/sh

./qemu-system-meta -nographic -display none -device da,exit_threads=1 -chardev stdio,id=chan1 -kernel kernel
