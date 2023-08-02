---
title: "Using PvGrub2 on Debian"
date: 2017-12-04T19:04:48
lastmod: 2018-01-10T15:06:38
summary: "Using pvgrub2 on Debian is very easy, and there is a little bit of documentation on the 'net, but not enough to cover all needs. I had to do some workarounds to enable pvgrub2 with btrfs."
---
Recently I wanted to move my Xen domU over to [pvgrub2](https://wiki.xenproject.org/wiki/PvGrub2), the [grand old bootloader](https://en.wikipedia.org/wiki/GNU_GRUB) ported to Xen. It shouldn't be hard, but as I am using btrfs on my domU with a /boot inside a /system subvolume, I'm making it a bit harder for myself.

## Configuration on the domU

1. Check that you have a kernel installed. In Debian, this usually requires the `linux-image-amd64` package. You may already have one or more kernel packages installed, but this `linux-image-<arch>` package is required for (security) updates.
2. Install the `grub-xen` package.
3. Run `update-grub`.
4. Only if you have /boot in a non-standard location: make sure there is a `boot` symlink in the root of your filesystem to the correct boot directory, in my case `/system/boot`.

There may be other things you need to configure. For example, you may need to install `linux-headers-foo` (e.g. `linux-headers-amd64`) to make the initramfs updater happy. And when you're at it, you might want to remove old kernels left over from previous versions of Linux, if you have them.

## Configuration on the dom0

1. Make sure you have the `grub-xen-host` package installed. This package is most likely already installed as it is Recommended as part of Xen.
2. **Backup** you guest configuration file!
3. Adjust the guest configuration. I have a configuration like the following:

```
kernel      = '/usr/lib/grub-xen/grub-x86_64-xen.bin'
root        = ''
extra       = '(xen/xvda2)/boot/grub/grub.cfg'
```

The `extra` parameter must contain the full path to the `grub.cfg` file, as GRUB sees it. If it's wrong, your guest will be stuck in a GRUB prompt (`grub>`) and waste CPU cycles.

Note that the `root` parameter has to be empty.

## Troubleshooting

There are a few things that can go wrong, which will land you in a grub prompt. A great resource is the [Ubuntu documentation](https://help.ubuntu.com/community/Grub2/Troubleshooting) for GRUB. But here are a few ideas.

If your guest doesn't seem to start and just wastes CPU, it is probably stuck on the command line. Start the guest with a console using `xl create -c /path/to/configfile.cfg`, which should land you in a GRUB console.

If you are in the `grub>` console, there are two things you can do to troubleshoot:

1. Issue `ls` to see which root directories GRUB knows about. These are device names in parentheses. For me, these were (among others) `(xen/xvda1)` and `(xen/xvda2)`. The `disk` parameter in the guest configuration gives an indication which is which, but you can also put a path behind the device name to see what's in there (e.g. `(xen/xvda2)/` and `(xen/xvda2)/boot`). Find the grub.cfg file this way, try to `cat` it. The full path has to match the `extra` path parameter in the guest configuration. Edit it, shutdown (using `halt`), and recreate the guest.
2. If this still doesn't boot your guest, try to load the configuration using `source <path>`. There may be an error while reading grub.cfg. In my case, it tried to load a file from `/boot` which didn't exist on my system (possibly a bug in GRUB).

## Resources

  * [pvgrub2 wiki page](https://wiki.xenproject.org/wiki/PvGrub2), especially the [notes on Debian](https://wiki.xenproject.org/wiki/PvGrub2#Debian)
  * [Debian pvgrub2 wiki](https://wiki.debian.org/PvGrub)
  * [Ubuntu GRUB troubleshooting](https://help.ubuntu.com/community/Grub2/Troubleshooting)
