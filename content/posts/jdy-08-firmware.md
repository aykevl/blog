---
title: "Flashing the HM-10 firmware on a JDY-08"
date: 2017-05-12
lastmod: 2017-05-12
summary: "Use CCLoader to flash the official HM-10 firmware on a cheap Chinese JDY-08 device. Unfortunately, the process doesn't result in a working device, but at least I got somewhere."
---
In my [previous post](/2017/05/jdy-08) I looked into the JDY-08 trying to put it to some use. I actually got it working but the default firmware is very crippled and (for me most importantly) lacks any power saving features. I managed to write the official HM-10 firmware to it, although that's as far as I've come... The device didn't do much afterwards.

**Warning:** this will most likely brick your JDY-08. I'm documenting it here just in case someone comes along and manages to get it to work anyway.

## Connecting

So here's the connection table. See my [previous post](/2017/05/jdy-08) for how to solder them. Also see the [forum thread](https://forum.arduino.cc/index.php?topic=393655.0) with much more detailed instructions.

| pin name | JDY-08 | Arduino UNO
| --- | --- | --- |
| `RESET_N` | `RST` | pin 4
| `DEBUG_CLOCK` | `P22` | pin 5
| `DEBUG_DATA` | `P21` | pin 6

Of course also connect `VCC` and `GND` and **use a level shifter** (the JDY-08 is not 5V tolerant).

# Getting the tools ready

So the next step is getting the tools ready. Upload the [Arduino sketch](https://github.com/RedBearLab/CCLoader/blob/master/Arduino/CCLoader/CCLoader.ino) to your Arduino (I've used an UNO) and download the [CCLoader software](https://github.com/RedBearLab/CCLoader) for your OS. I've used Linux for which I compiled it manually, as there was no Linux binary provided and I would rather check and compile the source code myself instead of downloading and running a binary blob from the internet.

The command accepts 3 arguments, with `device code` being 0 for the Uno (ATmega328) and 1 for the Leonardo (ATmega32u4):

```
$ ./ccloader <serial port> <firmware.bin> <device code>
```

This is the first output I got:

```
$ ./ccloader /dev/ttyACM0 HMSoft.bin 0
Comport open:
Device  : Default (e.g. UNO)

Baud:115200 data:8 parity:none stopbit:1 DTR:off RTS:off
File open success!
Block total: 496
Enable transmission...
Request sent already! Waiting for respond...
```

It turns out it is necessary to connect a 10µF capacitor between the GND and reset pins. This took me a while to figure out. CCLoader opens a new serial connection which causes the UNO to restart, probably missing the first few bytes it sends.

So, my next try:

```
$ ./ccloader /dev/ttyACM0 HMSoft.bin 0
Comport open:
Device  : Default (e.g. UNO)

Baud:115200 data:8 parity:none stopbit:1 DTR:off RTS:off
File open success!
Block total: 496
Enable transmission...
Request sent already! Waiting for respond...
No chip detected!
Program successfully!
File closed!
Comport closed!
```

If you have read my previous post, you may know the `P22` pin was broken. Well, I scratched open some of the blue surface to get to the trace leading away from it. Now I knew the Arduino was actually working as a CCLoader device, I actually tried holding a jumper wire on it... this required a pretty steady hand.

```
$ ./ccloader /dev/ttyACM0 HMSoft.bin 0
Comport open:
Device  : Default (e.g. UNO)

Baud:115200 data:8 parity:none stopbit:1 DTR:off RTS:off
File open success!
Block total: 496
Enable transmission...
Request sent already! Waiting for respond...
Begin programming...
1  2  3  4  5  6  7  8  9  10  11  [...snip...]  494  495  496  Program successfully!
File closed!
Comport closed!
```

Finally, a successful upload! This whole process took 1½ minute, uploading all the blocks. Due to a bug in `ccloader` there was not much output during the upload (it wouldn't flush stdout). But it looks like it did the job.

Unfortunately, I can't get it to work. The device doesn't show up in the [nRF Toolbox](https://play.google.com/store/apps/details?id=no.nordicsemi.android.nrftoolbox) and I can't get serial to work. I tried basically every baud rate on both pins `P02`/`P03` and `P16`/`P17` (the latter ones being the UART pins according to the [HM-10 datasheet](http://fab.cba.mit.edu/classes/863.15/doc/tutorials/programming/bluetooth/bluetooth40_en.pdf).

Maybe someone else gets a bit closer? For now, I've given up on the device. It's practically bricked and while it's cheap, it costs me too much effort to get it to work.
