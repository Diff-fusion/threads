#!/bin/sh

qemu_path="${1:-.}"

"${qemu_path}/configure" \
    --target-list=meta-softmmu \
    --disable-debug-tcg \
    --disable-user \
    --disable-linux-user \
    --disable-sparse \
    --disable-sdl \
    --disable-virtfs \
    --disable-vnc \
    --disable-cocoa \
    --disable-xen \
    --disable-xen-pci-passthrough \
    --disable-brlapi \
    --disable-vnc-tls \
    --disable-vnc-sasl \
    --disable-vnc-jpeg \
    --disable-vnc-png \
    --disable-curses \
    --disable-curl \
    --disable-fdt \
    --disable-bluez \
    --disable-slirp \
    --disable-kvm \
    --disable-nptl \
    --disable-vde \
    --disable-blobs \
    --disable-docs \
    --disable-vhost-net \
    --disable-spice \
    --disable-libiscsi \
    --disable-smartcard \
    --disable-smartcard-nss \
    --disable-usb-redir \
    --disable-guest-agent \
    --disable-glusterfs
