---
title: "Internals of the MBR in Nordic SoftDevices"
date: 2018-01-16
lastmod: 2018-01-16
summary: "Nordic BLE chips contain a proprietary SoftDevice implementing the BLE stack. In this post, I will explain how the MBR region works and how to write your own."
---
For some time, I've been working on a [bootloader/DFU for Nordic BLE chips](https://github.com/aykevl/micropython/tree/nrf-dfu-mbr-wip/ports/nrf/dfu) (nRF51822, nRF52832). If you don't know, these are small microcontrollers with on-board Bluetooth Low Energy. They use a so-called SoftDevice which is a binary blob implementing BLE (see [this video](https://www.youtube.com/watch?v=tZjlixQPO-Q)). These chips are relatively cheap, yet very powerful. Certainly much nicer to work with than the [JDY-08](/2017/05/jdy-08).

The SDK contains an example bootloader, used for firmware updates. It may accept a new firmware over the air (via BLE), via a serial connection or via some other way an application programmer may think of. It needs to be separate from the application as the application itself will be completely overwritten during the update (certainly in single-bank DFU).

[![](/assets/master_boot_record_s132.svg)](http://infocenter.nordicsemi.com/index.jsp?topic=%2Fcom.nordic.infocenter.s132.sds%2Fdita%2Fsoftdevices%2Fs130%2Fmbr_bootloader%2Fbootloader.html)

Officially, a bootloader is written like any other application (with a few extra lines of glue code) and placed in a special area. The start address of this area is pointed to by a register variable called `UICR.BOOTLOADERADDR`. At reset, the so-called MBR (a part of the SoftDevice) will look at this address and call the reset handler of the bootloader. If there is no `UICR.BOOTLOADERADDR`, it will set up to forward all interrupts to the SoftDevice (which in turn may redirect them to the application) and call the reset handler of the SoftDevice.

But, just for forwarding calls and extra stuff stuff like continuing firmware updates on power loss, the MBR takes up a whole 4kB of space. We could do a lot more with that 4kB of space, if the code is optimized for code size. Wouldn't it be nice if we could put the DFU in this space, replacing the MBR? That would not take up any extra space, as there is a DFU already.

It turns out we can, and it isn't even that difficult.

This is roughly what the MBR does, according to the [product specification](http://infocenter.nordicsemi.com/index.jsp?topic=%2Fcom.nordic.infocenter.s132.sds%2Fdita%2Fsoftdevices%2Fs130%2Fmbr_bootloader%2Fmbr_bootloader.html):

* Set up the initial interrupt vector on non-bootloader boot.
* Forward interrupts to the SoftDevice, or to the bootloader if there is one.
* Finish an update on sudden power loss.

There really isn't much more to it.

What the documentation doesn't say, is how it *really* works internally. So with a bit of guessing and experimenting, I came to the following conclusions:

* The address to forward interrupts to (the ISR vector), is placed at address `0x2000_0000`. This is the first RAM address, and is the only address (4 bytes) that is reserved for the MBR.
* Both the default MBR and the SoftDevice itself use the address above, so it has to be set even though the MBR is replaced. To use BLE in the MBR it has to be set to 0 (the address of the MBR). Otherwise, to boot an application, it has to be set to 0x1000 (the address to the SoftDevice) before calling the SoftDevice Reset\_Handler.
* Every interrupt is handled by the MBR and forwarded to the currently configured ISR vector, as the base address cannot be changed in an ARM Cortex-M0 processor (used in the nRF51 chip family). Apparently Nordic decided to keep it that way for the nRF52, even though the ARM Cortex-M4F chip in it is able to change the interrupt vector address in a special register, probably for backwards compatibility.

So to write your own MBR that can use the SoftDevice (for BLE functionality):

* Set the flash area in your linker script to address 0, size 4K.
* Copy all ISR vector pointers from the SoftDevice, to replace the pointers configured in your MBR replacement. Skip the initial stack pointer and the Reset\_Handler as you'll need them, and maybe the SVC\_Handler if you intend to handle supervisor calls from the application (I don't).  
  Initially I configured the ISR vector table as usual (pointing to a Default\_Handler) and added a post processing script to adjust all ISR vector pointers in the resulting .hex file. Later on I wrote a script that extracts the ISR vector pointers from the SoftDevice into a generated header file so I could inject the required pointers at compile time.
* Decide in your Reset\_Handler whether this is a regular boot or a DFU boot. You can use the GPREGRET register for this. For example, the application can set it to 1 and reset, so if it is set to 1 you know the application requested DFU mode.
* On normal boot, adjust the ISR vector address (at 0x2000\_0000) and jump to the Reset_Handler of the SoftDevice. Before the jump, the vector address will need to contain the address of the current ISR vector: 0x1000 (the address of the SoftDevice).
* On a boot in DFU mode, adjust the ISR vector address to 0 (the address of the MBR). After that you can init the SoftDevice as usual.

Note that if you are calling SoftDevice functions (`sd_foo`), these don't like pointers in the MBR region. This means you cannot declare global structs as const, they need to live in some other place (e.g. RAM/.data).

Jumping from the reset handler in the MBR region to the reset handler of the SoftDevice (for a normal boot) is really simple. I did it with just two lines of assembly:

```c
static void jump_to_app() {
    // Adjust the current ISR vector address.
    *(uint32_t*)0x20000000 = SD_CODE_BASE

    // Jump to the ISR vector of the SoftDevice.
    uint32_t *sd_isr = (uint32_t*)SD_CODE_BASE;
    uint32_t new_sp = sd_isr[0]; // load end of stack (_estack)
    uint32_t new_pc = sd_isr[1]; // load Reset_Handler
    __asm__ __volatile__(
            "mov sp, %[new_sp]\n" // set stack pointer to initial stack pointer
            "mov pc, %[new_pc]\n" // jump to SoftDevice Reset_Vector
            :
            : [new_sp]"r" (new_sp),
              [new_pc]"r" (new_pc));
}
```

The [end result](https://github.com/aykevl/micropython/tree/nrf-dfu-mbr-wip/ports/nrf/dfu) is a DFU, completely contained in the MBR. It is about 1.2kB in size, and although it has been heavily optimized for size it is still possible to improve code size if that's needed. Also, it can be built as a conventional bootloader reducing code size even further (<1kB on the nRF51, fitting in a single flash page).

Disclaimer: the original idea came from someone else. Most of the research and the implementation is mine. I'm not sure whether I'm violating any software licenses or anything else, but I don't think so. Just remember that you're working outside of how the SoftDevice is intended to work, and things may break.
