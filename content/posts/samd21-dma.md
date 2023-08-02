---
title: "DMA on the SAMD21"
date: 2019-09-19T13:05:40
lastmod: 2019-09-20T16:07:12
summary: "How to configure DMA on the SAMD21, for example to use it with SPI."
---
Recently I wanted to write a super-fast driver for SAMD21 chips to drive hub75 screens. You know, those LED matrices sold by [Adafruit](https://www.adafruit.com/product/607) and on the various Chinese web shops. I believe you don't actually need an FPGA for these screens and I want to prove that a performant microcontroller will also work. For that to work, you need SPI with DMA, otherwise you have to choose between sending data and calculating the next frame which will sacrifice performance. Therefore I needed DMA to start the transfer so most of the CPU could be dedicated to rendering the next frame instead of clocking out the bits. Unfortunately, there are very (if any) few accessible tutorials on how DMA (or DMAC) works on the SAMD21, so I decided to write my own.

<div class="video youtube">
<iframe width="560" height="315" src="https://www.youtube.com/embed/uNvYtk8wZnU" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
</div>

So, here is the gist of it. The DMA is a hardware peripheral that copies data from one address to another address. Basically like this:

```c
void copy(uint8_t *src, uint8_t *dst, int n) {
    for (int i = 0; i < n; i++) {
        *dst++ = *src++;
    }
}
```

Of course, this is not what you would write when using the DMA. It's just an example of what the hardware does.

It can be configured in all kinds of ways. For example, you can set the data size - referred in the DMA peripheral as "beat size" - to 8, 16, or 32 bits:

```c
void copy(uint32_t *src, uint32_t *dst, int n) {
    for (int i = 0; i < n; i++) {
        *dst++ = *src++;
    }
}
```

Or you can copy a buffer to a single address - useful for writing to a peripheral register like the SPI `DATA` register (note that `*dst++` has been changed to `*dst`):

```c
void copy(uint8_t *src, uint8_t *dst, int n) {
    for (int i = 0; i < n; i++) {
        *dst = *src++;
    }
}
```

You can also send the number of beats to copy (`n`) and - very importantly - a "trigger". This is when it should carry out the next copy operation, like when the previous char has been sent. Think of it like this:

```c
void copy(uint8_t *src, uint8_t *dst, int n) {
    for (int i = 0; i < n; i++) {
        while (!dst_is_ready()) {}
        *dst = *src++;
    }
}
```

But, of course, this being a complicated piece of technology you don't provide it the start address of the data to copy. You provide the end address. Don't ask me why.

```c
void copy(uint8_t *src, uint8_t *dst, int n) {
    src -= n;
    for (int i = 0; i < n; i++) {
        while (!dst_is_ready()) {}
        *dst = *src++;
    }
}
```

There are a few limitations, though. In particular, while this peripheral can access memory and peripherals, it can't access just any of them. It can only access SRAM (not flash). Also, it can only read from and write to specific registers, not just all registers in all peripherals. This means, for example, that you can't use DMA to drive the PORT peripheral directly.

Ok, so with the basics out of the way, how do you really drive this DMA peripheral? Well, this particular DMA driver really likes to work with memory. So much, that part of its configuration lives there (specifically, in SRAM). There are reasons for that, but that's only really useful for more advanced uses (related to the `descaddr` field). It uses the following struct:

```c
struct dmaDescriptor {
    uint16_t btctrl;
    uint16_t btcnt;
    uint32_t srcaddr;
    uint32_t dstaddr;
    uint32_t descaddr;
};
```

This struct is 16 bytes long, and in fact must also be aligned on a 16-byte (or 128-bit) boundary in memory.

You need two arrays of these structs. The length depends on which DMA channels you want to use. If you only need a single channel, you can simply have an array of length 1.

```c
volatile dmaDescriptor dmaDescriptorArray[1] __attribute__ ((aligned (16)));
dmaDescriptor dmaDescriptorWritebackArray[1] __attribute__ ((aligned (16)));
```

The writeback array is only used internally in the DMAC peripheral. You can theoretically do without, but I haven't managed to do that so just include that.

Now this struct needs to be configured. I didn't use the official C headers but instead used headers in Go (see [TinyGo](https://tinygo.org/)) generated from [SVD files](http://www.keil.com/pack/doc/CMSIS/SVD/html/index.html) which unfortunately didn't include the bitfields. So I wrote it myself. This is the C equivalent:

```c
dmaDescriptorArray[0].btctrl = (1 << 0) |  // VALID: Descriptor Valid
                               (0 << 3) |  // BLOCKACT=NOACT: Block Action
                               (1 << 10) | // SRCINC: Source Address Increment Enable
                               (0 << 11) | // DSTINC: Destination Address Increment Enable
                               (1 << 12) | // STEPSEL=SRC: Step Selection
                               (0 << 13);  // STEPSIZE=X1: Address Increment Step Size
dmaDescriptorArray[0].btcnt = n; // beat count
dmaDescriptorArray[0].dstaddr = dst;
dmaDescriptorArray[0].srcaddr = src + n;
```

You can leave `descraddr` alone or set it to 0. It should be 0 already when it is a global variable and hasn't yet been used. You may see that `srcaddr` is set to `src + n` instead of just `src`, this is the weirdness mentioned in the last `copy` example above.

The various fields in `btctrl` demand some extra explanation.

  * `VALID` must always be 1, otherwise it won't work.
  * `BLOCKACT` is not used if we just want to send between memory and peripherals.
  * `SRCINC` and `DSTINC` indicate which of the addresses (`src` or `dst`) should be incremented each beat (remember `*dst++` vs `*dst` in one of the examples above). In this case, the source (in RAM) should be incremented each beat to send the next byte while the destination should not be incremented: we're still writing to the same SPI `DATA` register.
  * `STEPSEL` and `STEPSIZE` are used for more advanced addressing if you want to increment by bigger amounts each time, they are not very useful for simple DMAing of SPI.

If you want to use a different send buffer on each transmission, you can leave `srcaddr` unconfigured for now and set it only when actually starting the transmission.

With all this done, it is now time to configure the peripheral to use these arrays:

```c
DMAC->BASEADDR.reg = (uint32_t)dmaDescriptorArray;
DMAC->WRBADDR.reg = (uint32_t)dmaDescriptorWritebackArray;
```

The peripheral should be disabled while you do this. This is the default at reset so just do this at the start of the program.

Now we're ready to enable the peripheral. This involves setting up the peripheral clock and enabling the peripheral (plus setting up the enabled levels, something that is only relevant to more advanced use cases):

```c
PM->AHBMASK.bit.DMAC_ = 1;
PM->APBBMASK.bit.DMAC_ = 1;
DMAC->CTRL.reg = DMAC_CTRL_DMAENABLE | DMAC_CTRL_LVLEN(0xf);
```

For some reason, the DMAC peripheral decided to not add support for addressing each individual channel. Instead, you have to select a particular channel using the `CHID` channel and can then configure that channel. We are going to use channel 0, so configuring it looks like this:

```c
DMAC->CHID.reg = 0; // select channel 0
DMAC->CHCTRLB.reg = DMAC_CHCTRLB_LVL(0) | DMAC_CHCTRLB_TRIGSRC(SERCOM0_DMAC_ID_TX) | DMAC_CHCTRLB_TRIGACT_BEAT;
```

This configures the following:

  * Select level 0. Selecting the level is only relevant when you do multiple DMA transfers at the same time and want to assign them a priority. Other than that, you can just ignore these levels.
  * Select a trigger source. This is what tells the DMAC peripheral it should send the next beat (often a byte). In this case it is configured to send the next beat when SERCOM 0 wants to send something, but you can set it to any available trigger source - depending on the peripheral you want to use DMA with.
  * Select the trigger action. In this case, it should just send a single beat, which is correct for SPI. I'm not sure what the other options are for, perhaps for doing larger memory-to-memory transfers?

Almost finished setting up DMA! Now, if you want to receive an interrupt, you can configure it here:

```c
DMAC->CHINTENSET.reg = DMAC_CHINTENSET_TCMPL;
NVIC_EnableIRQ(DMAC_IRQn);
```

Be aware that once you get an interrupt, you have to take it to avoid getting stuck in the DMA handler. That means, you have to clear it in the handler:

```c
void DMAC_Handler() {
    // Must clear this flag! Otherwise the interrupt will be triggered over and over again.
    DMAC->CHINTFLAG.reg = DMAC_CHINTENCLR_MASK;

    // continue handling the interrupt...
}
```

And finally, now it's time to start the DMA transfer:

```c
// You may want to update the source address before starting the DMA, if you send a different buffer each transfer.
//dmaDescriptorArray[0].srcaddr = src + n;
// Start the transfer!
DMAC->CHCTRLA.reg |= DMAC_CHCTRLA_ENABLE;
```

Hopefully that worked! You can check with a logic analyzer to see if the signal seems right. I'm personally a big fan of the Saleae Logic 4 - it does everything I want it to do - but unfortunately they don't sell it anymore.

If it doesn't work, here is a list of things you might want to check:

  * Does the array live in SRAM, and is it 16-byte (128-bit) aligned? This can be accomplished with the `__attribute__((align(16)))` GCC extension.
  * Has the peripheral that you want to interact with using DMA been fully configured before you enabled it?
  * Are the `src` and `dst` addresses correct? With the correct increment configuration?
  * Do you use the correct trigger source, specific to your peripheral with the right direction (tx vs rx)?

I hope that works! Once you get DMA working, you can have higher performance or just let the chip do some other processing in the meantime to improve performance.

I used a few sources to implement my hub75 driver:

  * [The SAMD21 datasheet](https://cdn.sparkfun.com/datasheets/Dev/Arduino/Boards/Atmel-42181-SAM-D21_Datasheet.pdf#page=272) (page 272)
  * http://www.lucadavidian.com/2018/03/08/wifi-controlled-neo-pixels-strips/
  * https://svn.larosterna.com/oss/trunk/arduino/zerotimer/zerodma.cpp

The source code lives [here](https://github.com/aykevl/things/blob/master/hub75/driver_samd21.go).
