---
title: "Using Arduino on the \"blue pill\" STM32F103 boards"
date: 2017-06-06
lastmod: 2017-06-06
summary: "As I gave up on Rust (for now), I tried setting up the Arduino environment to work with the \"blue pill\" board. It turns out to be quite easy, although there were a few small issues with the setup. You'll still need a (cheap) SWD programmer, though."
---
I have recently bought one of those "[blue pill](http://wiki.stm32duino.com/index.php?title=Blue_Pill)" development boards from the [Chinese market](https://www.aliexpress.com/wholesale?SearchText=stm32+minimum). It's a small device that's quite capable, but more importantly, it's extremely cheap. The idea was to get started in ARM Cortex-M development with something simple.

I tried using [Rust on the STM32](/2017/06/stm32-rust) but for now gave up as the toolchain is just not ready. While it's possible to create a "blinking LED" demo, anything more complex will require an intimate knowledge of the STM32 which I just don't have at the moment.

So I'll be using Arduino for now. [Roger Clark](https://github.com/rogerclarkmelbourne/) has ported the Arduino core to this device and a relatively big community has formed around it. The setup turns out to be quite easy.

Hardware required:

* The "[blue pill](https://www.aliexpress.com/wholesale?SearchText=stm32+minimum)" board
* An SWD programmer, e.g. a [clone of the ST-Link V2](https://www.aliexpress.com/wholesale?SearchText=st-link+v2).

How to get started is described [on the forum](http://www.stm32duino.com/viewtopic.php?f=2&t=873) but it's even easier than it might seem.

* Download the latest release [from GitHub](https://github.com/rogerclarkmelbourne/Arduino_STM32/releases) and place it in Arduino/hardware. I wanted to live on the bleeding edge so I decided to download from git instead but you should probably just download the latest stable release.
* Download the toolchain by installing board support for Arduino SAM boards (Arduino Due). Again, I was stubborn and did something else, namely modify `Arduino_STM32/STM32F1/platform.txt` to to use `/usr/bin/` as my `compiler.path`, so the installer uses my system-wide ARM GCC installation instead of the one provided by Arduino.

Now, it's just a matter of opening the Blink example (File > Examples > 01.Basics > Blink) and try to compile and upload it. I first tried to just compile it to make sure the toolchain was OK. Of course, it initially tried to compile without installing the SAM board support or setting the proper `compiler.path`, resulting in the following error:

    fork/exec /bin/arm-none-eabi-g++: no such file or directory
    Error compiling for board Generic STM32F103C series.

After fixing the compiler this issue went away.

The next problem was with uploading the program, using ST-Link (as selected in the upload method from the Arduino menu):

    /home/ayke/Arduino/hardware/Arduino_STM32/tools/linux/stlink/st-flash: error while loading shared libraries: libusb-1.0.so.0: cannot open shared object file: No such file or directory

This is because the st-flash binary is a 32-bit executable and I'm running a 64-bit OS. I suspect there's an issue with the Arduino IDE: apparently it picks the 32-bit executable while there's a 64-bit one available (in tools/linux64).

    $ file /home/ayke/Arduino/hardware/Arduino_STM32/tools/linux/stlink/st-flash
    /home/ayke/Arduino/hardware/Arduino_STM32/tools/linux/stlink/st-flash: ELF 32-bit LSB executable, Intel 80386, version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux.so.2, for GNU/Linux 2.6.24, BuildID[sha1]=be1b2ce303da6d9d119783a0cc9beb59d4b9a8c0, not stripped

This is easily fixed in Debian, by installing the 32-bit version of libusb-1.0-0:

    $ sudo apt-get install libusb-1.0-0:i386

Now I could upload the blinky example and see the mighty LED blink!

I have also tried to burn a bootloader on it, but I can't get it to work. If I get it to work, I'll update this post. For now, I'll just use the ST-Link.
