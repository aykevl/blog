---
title: "Putting a Raspberry Pi 1 SD card into a Pi 3"
date: 2017-03-19T03:34:37
lastmod: 2017-03-19T03:41:34
summary: "How to move an installed SD card from a Pi 1 to a Pi 3, or make it possible to use them both. There are a few tricks to get the network running on both devices."
---
I have an older Raspberry Pi 1B (not the 1B+, really the older 1B[^1]). It has two USB ports and a standard-size SD card (no microSD yet). But I have gotten a Raspberry 3B that I needed for school, and I didn't want to reuse my old Pi that I used as sensor and sound server.

Well, the newer Pi has many improvements, like built-in wifi and less visible lights. As it has built-in wifi and my room only has one Ethernet connection, I won't have to use a switch[^2] anymore, meaning a lot less flickering lights at night!

It turns out moving the installed SD card to the new Pi isn't as simple as just pulling it out of the old one and inserting it to the new one. It needs some software adjustments too (which will allow it to run both on the Pi 1 and the Pi 3). Between version 1 and 2, the CPU got an update from ARMv6 to ARMv7 which means a new kernel is needed (but fortunately not new userland). The Pi 3 uses ARMv8 but is compatible with the kernel from the Pi 2.

Here is what you'll need to change:

1. Install the new kernel.
    
        # apt-get install linux-image-rpi2-rpfv
    
2. Adjust `config.txt`. The bootloader has to know where to load the right kernel from! This is a minimal example:
    
    ```
    [pi1]
    kernel=vmlinuz-4.4.0-1-rpi
    initramfs initrd.img-4.4.0-1-rpi followkernel

    [pi3]
    kernel=vmlinuz-4.4.0-1-rpi2
    initramfs initrd.img-4.4.0-1-rpi2 followkernel
    ```

3. Change `eth0` to `eth1` in `/etc/network/interfaces`. I don't know why this is needed, but apparently it's `eth1` on the newer Pi. A possible reason is that the system recognizes the new ethernet controller is a different one from the last (it's a completely different device, after all). Just do it, to be sure.
    
    I have changed it in such a way that it works on both devices (with wifi not yet configured).
    
        auto lo
        iface lo inet loopback

        # Pi 1
        allow-hotplug eth0
        iface eth0 inet dhcp

        # Pi 3
        allow-hotplug eth1
        iface eth1 inet dhcp

4. Install [wireless-related drivers and software](https://github.com/debian-pi/raspbian-ua-netinst/issues/427#issuecomment-247852092).
    
        # apt-get install firmware-brcm80211 pi-bluetooth wpasupplicant

5. Set up wifi. If you want to log into the device headlessly, you probably want to do this (so that at least wifi OR ethernet works - if one of them fails).

    Add this to your `/etc/network/interfaces`:

        allow-hotplug wlan0
        iface wlan0 inet manual
        wpa-roam /etc/wpa_supplicant/wpa_supplicant.conf
        iface default inet dhcp

    Create the file `/etc/wpa_supplicant/wpa_supplicant.conf` with the following contents:

        country=NL
        ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
        update_config=1
        
        network={
                ssid="foo"
                psk="bar"
                key_mgmt=WPA-PSK
        }

    Adjust the country code, the SSID, and the password for your network.

This should be it! It took me a few tries and some googling to get this right, especially the network part. I first tried with just ethernet, which of course didn't work due to the network device name change. When I set up wifi (while running on the old Pi 1), I could finally log into the 'new' system.

I hope this saves someone some trouble.

[^1]: Of course, a month after buying the Pi 1B (that I had looked at for months as I couldn't make the decision to buy it for myself), the [B+ was launched](https://www.raspberrypi.org/blog/introducing-raspberry-pi-model-b-plus/) with many small hardware improvements.

[^2]: Which is really an old repuposed [ADSL router](https://www.telfort.nl/persoonlijk/service/specificaties-zyxel-p2602hw.htm), with DHCP disabled so it is effectively a switch.
