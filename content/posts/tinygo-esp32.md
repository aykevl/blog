---
title: "ESP32 and ESP8266 support in TinyGo"
date: 2020-09-22
lastmod: 2020-09-22
summary: "How ESP32/ESP8266 support got added to TinyGo, how we got there, and the current status of support."
---
As you might have heard, we've added ESP32 and ESP8266 support to TinyGo last week in version 0.15. Here I go into some background on how this came to be and what the challenges were to add initial support for these chips.

<blockquote class="twitter-tweet"><p lang="en" dir="ltr">Controlling WS2812 LEDs from an ESP32 using <a href="https://twitter.com/TinyGolang?ref_src=twsrc%5Etfw">@TinyGolang</a>! The entire binary is just 2064 bytes in size.<br>Source code: <a href="https://t.co/4xU2N2NIUr">https://t.co/4xU2N2NIUr</a> <a href="https://t.co/2T6kw7fhaM">pic.twitter.com/2T6kw7fhaM</a></p>&mdash; Ayke van Laethem (@aykevl) <a href="https://twitter.com/aykevl/status/1302036376570023937?ref_src=twsrc%5Etfw">September 5, 2020</a></blockquote> <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>

I've long wanted TinyGo support on the ESP32 and ESP8266 chips. These chips are incredibly popular because of their low price and enormous power and so support for them has been one of the most requested (if not the most requested feature) as long as TinyGo exists. I'm happy to say both chips now have initial support directly in TinyGo!

Adding support has not been easy. The main stumbling block has been the instruction set architecture. Unlike all other architectures supported in TinyGo, these chips use the Xtensa architecture which is not in upstream LLVM (the compiler framework used by TinyGo). Luckily Espressif has been working on [a LLVM fork](https://github.com/espressif/llvm-project) that adds support for this architecture.

Another reason it has taken so long is that the TinyGo project needs register descriptors for memory-mapped I/O to control things like the CPU speed and peripherals (I2C, SPI, PWM, etc). For Cortex-M chips, they are usually provided by the silicon vendor in SVD files which is a machine-readable listing of all available registers. This is then converted to Go code for ease of use. Unfortunately, vendors that use a different instruction set in their chips (RISC-V, Xtensa) often don't provide these files.

While it is theoretically possible to write these SVD files manually, that's a huge amount of error-prone work. Luckily the [esp-rs](https://github.com/esp-rs) community has done a huge amount of work on that front as they have the same problem as TinyGo. They have extracted most peripherals directly from [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/) which stores them in C header form and filled in the gaps by manually writing the remaining parts. So, thanks to Rust on the ESP32, we can now have Go on the ESP32!

Of course, after I got a basic blinking LED working I wanted something more interesting. So I added support for the popular WS2812 (aka [NeoPixel](https://learn.adafruit.com/adafruit-neopixel-uberguide/the-magic-of-neopixels)) LEDs [on the ESP32](https://github.com/tinygo-org/drivers/pull/198). You can see the result in the tweet above. The WS2812 has some tight timing requirements which are easiest to achieve using low-level assembly so it's not trivial to add, but the result is well worth it.

That said, there is still a lot to be done. This is just an initial port, so most of the things that make the ESP32 great haven't yet been implemented. The following things are supported on the ESP32 as of the 17th of September 2020:

  * flashing directly from TinyGo, if you have esptool.py installed (on Linux: `tinygo flash -target=esp32-wroom-32 -port=/dev/ttyUSB0`)
  * basic GPIO support that allows blinking LEDs
  * UART and SPI support
  * WS2812 (aka NeoPixel) LEDs

Many other things have not been implemented, such as many peripherals (like I2C) and advanced features like networking and deep sleep. Because this is a new architecture, goroutines also aren't yet supported. The ESP8266 has a similar level of support, except that it also lacks SPI support.

If you are just as thrilled about ESP32/ESP8266 support in TinyGo, please help us out! Adding support for all peripherals is a ton of work and we really need community help to get full support for these powerful chips. So, [join our Slack channel](https://app.slack.com/client/T029RQSE6/CDJD3SUP6) (invite [here](https://invite.slack.golangbridge.org/)) and take a look at [our contributing guide](https://github.com/tinygo-org/tinygo/blob/release/CONTRIBUTING.md) to get started!
