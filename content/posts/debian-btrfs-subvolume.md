---
title: "Installing Debian on a Btrfs subvolume"
date: 2015-11-24T12:01:55
lastmod: 2015-11-24T12:03:51
summary: "How to install Debian on a Btrfs subvolume to easily make system snapshots."
---
In Debian 8 (Jessie), installing on a Btrfs subvolume outside the root is kind of non-intuitive. There are probably other ways, but the way described here is how it works for me.

The problem is that the Debian installer has no idea of Btrfs subvolumes. So to work around it and install Debian to a subvolume, you have to create the filesystem yourself first using GParted. Then make a root subvolume and set it as default: that's where the system will be installed.

The [live images](http://gparted.org/livecd.php) worked very well for me. You can install them easily on a spare SD card with more than ±256MB free space. For [UEFI](https://en.wikipedia.org/wiki/Unified_Extensible_Firmware_Interface) this is just a matter of copying all files from the ISO (open with an archive manager) to the root of the SD card, if it is formatted as FAT.

What I discovered:

  * [GRUB](https://en.wikipedia.org/wiki/GNU_GRUB) does not have any idea of mounted subvolumes or default subvolumes. All paths in GRUB are relative to the root of the filesystem. `btrfs-install` uses the right path to the kernel (relative to the root subvolume), so placing the `/boot` directory on a subvolume can work.
  * The Debian installer does not have any idea of subvolumes either, but it installs in the subvolume set as the default (by default, this is the root).

Together, it's actually quite easy to install into a subvolume, once you understand the limitations:

  * Format the partition you want to install the system on as Btrfs
  * Mount the partition, for example on `/mnt/linux`.
  * Create a subvolume where you want to install the system to, I called it `system`. It will be accessible from `/mnt/linux/system`.
    
        # btrfs subvolume list /mnt/linux
        ID 257 gen 109 top level 5 path system
        # btrfs subvolume set-default 257 /mnt/linux/system
    
    Note that the ID can vary from system to system, so don't simply copy-paste the command.

  * Reboot into the Debian installer, and install to the Btrfs partition (without formatting the partition, this is important). Complete the installation as usual.

Now you have a working system, installed to a subvolume.

You should modify `/etc/fstab` so it doesn't depend on the currently selected default. I used the mount option `subvol=system` for `/` and `subvolid=5` (the root) for `/mnt/linux`. I also created a `home` subvolume to mount on `/home` (with option `subvol=home`).

Now you can also easily make snapshots. Whatever is in `/mnt/linux/system` will be booted. So you can create a new snapshot of `/mnt/linux/system`, and whenever you want to go back you can simply rename the snapshot (just a different kind of subvolume) back to `/mnt/linux/system` and the system will boot from that next time. It is possible to move the `system` subvolume while the system is running: I think it only looks up the name at mount time.
