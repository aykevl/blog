---
title: Autoplay video on an analog TV using a Raspberry Pi 3
date: 2025-03-09
summary: How to configure a Raspberry Pi to auto-play videos from a USB stick, without needing any input. It's not yet entirely working as intended, but this is what I got working so far.
---

I've been helping my girlfriend with a project to auto-play video on a CRT TV from a Raspberry Pi 3.

**Goal**: to automatically play videoclips from a folder on a USB stick at boot in a randomized order. We're not quite there yet, but getting closer.

We've been using a Raspberry Pi 3 (I think a 3B+), with Raspberry Pi OS with desktop (Debian bookworm) installed.

## First try: HDMI scaler

It turns out that it's quite tricky to get the analog output to work well!

Our first attempt therefore was by using a converter that converts a HDMI signal to a SCART output that can then be shown on the TV. This works decently well, but is not ideal since it requires an extra device. However, HDMI output on the Raspberry Pi seems to be a lot less finnicky to get work.

This doesn't need a lot of configuration. HDMI is the default output and the converter scales the HDMI resolution to something appropriate for an analog TV. We really only changed two things:

 1. I picked a lower resolution, I think 720p, so that the output of the Raspberry Pi is closer to the output of the TV. Also, it was one of the few 4:3 output options, most were 16:9 which weren't appropriate for the TV.
 2. [Kodi (the video player we're using here) has a way to calibrate overscan very precisely](https://kodi.wiki/view/Settings/System/Display#Video_calibration), which is very nice! Go to display settings, enable expert mode in the top left, choose "video calibration", and set overscan exactly as you prefer.  
    There is also an option in `raspi-confi` to enable overscan (called underscan in there) but it doesn't allow any precise calibration as far as I could find. It would be nice to configure it from there, because that way overscan would be configured not just for Kodi but also for the desktop. Right now, the edges of the desktop are cut off.

## Second try: native analog video output

Native analog video output is a bit more tricky. The way we got it to work is as follows:

 1. Start `raspi-config` (`sudo raspi-config` in a terminal).
 2. Go to Display Options, and select Composite.
 3. Confirm that you want to enable composite output.
 4. Remove the HDMI cable, and reboot.

There is a scary warning when you enable composite output, saying that HDMI output will be disabled. This doesn't appear to be the case with our Raspberry Pi and OS version. Instead, it autodetects HDMI on boot and if it doesn't find a connected display, it will switch to composite instead. This also means that if you mess up, you can connect a HDMI display and fix the problem. It also means that if you don't remove the HDMI cable, composite output won't work.

It's also possible to do the same thing by changing `/boot/firmware/config.txt` and change the `dtoverlay` option to add `,composite`:

```
dtoverlay=vc4-kms-v3d,composite
```

This may be helpful if you made a mistake and need to fix the configuration from a different computer (by editing the config.txt file on the SD card).

Unfortunately, the default output appears to be NTSC while we are using a PAL TV. It shows an output, but it's all grayscale. After some searching, this can be fixed by adding an option to the Linux command line: add `vc4.tv_norm=PAL` to the end of `/boot/firmware/cmdline.txt`.

The documentation for this is [on the Raspberry Pi website](https://www.raspberrypi.com/documentation/computers/config_txt.html#composite-video-mode), but for some reason was less straightforward to find using Google.

Unfortunately, when I tried this, the Pi could boot to the desktop but whenever Kodi started the screen would go blank. I suspect Kodi is messing with display settings and breaking composite output. To be investigated next time!

## Autoplay video 

Normally the Raspberry OS variant we're using boots to a desktop. However, we actually want to boot to the Kodi video player directly.

To do this, install Kodi (if you haven't already), and modify the file `/etc/xdg/lxsession/LXDE-pi/autostart` and put a line `@kodi` at the top. Then reboot to see whether it works.

For this to work, you may also need to switch from Wayland to X11. Start `raspi-config`, go to Advanced Options -> Wayland, and select "W1 X11". For more information, see [this Stack Exchange answer](https://raspberrypi.stackexchange.com/questions/69003/how-to-autostart-kodi-at-boot/114597#114597).

Note that you can exit back to the desktop by exiting Kodi in the power menu in the top left. That way, you can still access the desktop even though Kodi is the default. You can start Kodi again from the main menu on the desktop.

This starts Kodi, but doesn't start any videos yet on boot. You can however insert an USB stick and play a folder from there. So we're not quite there yet, but I think this is possible using an [Autoexec Service](https://kodi.wiki/view/Autoexec_Service). To be investigated the next time!
