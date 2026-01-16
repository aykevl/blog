---
title: Binary Code Modulation
date: 2026-01-15
summary: Bitbanging many LEDs from a microcontroller can be very fast, when using Binary Code Modulation and some assembly.
---

This is somewhat of a continuation of my previous [post on Charlieplexing]({{< ref "charlieplexing" >}}).

Let's say you have 4 LEDs that you need to turn on for a very specific duration.

![](/assets/bitplanes-intro.svg)

Or as a table:

| LED   | "on" cycles |
| ----- | ----------- |
| LED 0 | 2           |
| LED 1 | 5           |
| LED 2 | 0           |
| LED 3 | 7           |

That is, each LED has a bitdepth of 3 (usually we use a bit depth of 8, for example for WS2812 LEDs, but to simplify things we'll use a bit depth of 3).

How do you update these LEDs efficiently on a microcontroller?

If you can connect them all to PWM channels, it's easy: set the "top" value of the PWM to 7 and connect each of the LEDs to a PWM channel with the threshold value being the number of cycles the LED should be on.

However if you do more complicated stuff like Charlieplexing or you simply ran out of PWM channels, you need to use something else. You need to manually control these LED... somehow.

## GPIO ports

The trick I describe here only works if all the LEDs are connected to a single GPIO port. This is important, because it allows you to update all the LEDs in a single "store" instruction. Usually this means writing to the `PORT` or `ODR` register, depending on your specific microcontroller.

Additionally, check how many cycles this store instruction costs. On an AVR it costs a single cycle. On some STM32 chips (for example the [STM32L031](https://www.st.com/en/microcontrollers-microprocessors/stm32l0x1.html) chip I like to use) it also costs a single cycle since the GPIO pins are connected directly to the processor via the [IOPORT](https://developer.arm.com/documentation/ddi0484/c/Functional-Description/Interfaces/Single-cycle-I-O-port). It still works if a store costs two cycles, it will just be half as fast and you need to be careful about instruction timing.

## Bitplanes

With all of this prepared, you might think you'll need at least 8 GPIO writes to turn each LED on for the right duration. After all, there are 8 vertical lines in this image where the output might change:

![](/assets/bitplanes-intro.svg)

That's quite annoying to deal with! You'll need to prepare all 8 of these values in advance, and write them one by one to the GPIO output register. Assuming your preferred chip even has 8 free registers you can use. But actually there's a simpler way called [binary code modulation](https://www.batsocks.co.uk/readme/art_bcm_1.htm) that requires far fewer writes. In this case only 4 of them with space in between. And it scales very well to higher bit depths.

Let's take a look at the values of these four LEDs again:

| LED   | value | value in bits |
| ----- | ----- | ------------- |
| LED 0 | 2     | 010           |
| LED 1 | 5     | 101           |
| LED 2 | 0     | 000           |
| LED 3 | 7     | 111           |

  * LED 0 needs to be on for 2 clock cycles.
  * LED 1 needs to be on for 5 clock cycles, which is 4+1.
  * LED 2 needs to be on for 0 clock cycles.
  * LED 3 needs to be on for 7 clock cycles, which is 4+2+1.

Put a different way:

| LED   | value | 4 cycles | 2 cycles | 1 cycle |
| ----- | ----- | -------- | -------- | ------- |
| LED 0 | 2     |          | X        |         |
| LED 1 | 3     | X        |          | X       |
| LED 2 | 0     |          |          |         |
| LED 3 | 7     | X        | X        | X       |

Or, using the graphic like above:

![](/assets/bitplanes-groups.svg)

These durations exactly match the bits above! Just look at the table with "value in bits" and now this table with the cycle durations.

We can use this to our advantage. We split the data of our four LEDs into three [bitplanes](https://en.wikipedia.org/wiki/Bit_plane), one for each of the 3 bits in our LED values. Which means we basically rotate the table above:

| bitplane | LED 0 | LED 1 | LED 2 | LED 3 |
| -------- | ----- | ----- | ----- | ----- |
| 4 cycles | 0     | 1     | 0     | 1     |
| 2 cycles | 1     | 0     | 0     | 1     |
| 1 cycles | 0     | 1     | 0     | 1     |

Or when put together as a single binary value ready for storing:

| bitplane | output register value (binary) |
| -------- | ------------------------------ |
| 4 cycles | 0101                           |
| 2 cycles | 1001                           |
| 1 cycles | 0101                           |

Now, with 3 store operations, plus one additional store at the end to reset all LEDs to 0, we will have turned on each LED exactly the number of clock cycles needed - albeit not necessarily for a continuous duration.

In pseudo-assembly, it might look like this (assuming the `str` operation is a single cycle):

```
str bitplane4, [OUTPUT]
nop
nop
nop
str bitplane2, [OUTPUT]
nop
str bitplane1, [OUTPUT]
str zeroBits,  [OUTPUT]
```

Instead of `nop` instructions, you could also do something useful there - as long as the number of cycles still matches. For example, if you store multiple 16-bit bitplanes together in a 32-bit register (with 16 bit output registers):

```
strh bitplane42, [OUTPUT]
lsrs bitplane42, #16
nop
nop
strh bitplane42, [OUTPUT]
nop
strh bitplane1,  [OUTPUT]
strh zeroBits,   [OUTPUT]
```

With careful instruction timing and ordering, you can do all sorts of things in between - as long as the instructions you use have a fixed cycle count. For example, you could load more bitplanes, prepare the `zeroBits` value, or even reorder the different bitplanes: they don't need to be "4 cycle" then "2 cycle" then "1 cycle". For example, take a look at [the implementation for my 36-LED earrings](https://github.com/aykevl/things/blob/f874ff52f69891b0c62640082d2e84ca80c07b2d/earring-ring-rgb36/bitbang.h#L645) which uses five bitplanes in the order "8 cycles", "2 cycles", "1 cycle", "4 cycles" and "16 cycles" just because this order allows me to do various other things in between.

## Conclusion

Bitbanging many LEDs at once can be very fast! With binary coded modulation and some bithacking tricks you can update all outputs in exactly as many clock cycles as the hardware allows. This can be used for [Charlieplexing]({{< ref "charlieplexing" >}}), to prepare data for a [hub75 display](https://www.adafruit.com/product/607), or just for a conventional LED matrix driven from GPIO pins.
