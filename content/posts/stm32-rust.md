---
title: "Intro to Rust on the STM32"
date: 2017-06-04T01:04:45
lastmod: 2017-06-04T22:09:52
summary: "How to write a simple Rust program for the STM32 \"blue pill\" board that's sold on AliExpress and Ebay for about $2. It turns out to be not too difficult."
---
I recently ordered a simple STM32 board, which is a microcontroller board much like Arduino. It looks a lot like the [Arduino Nano](https://www.arduino.cc/en/Main/arduinoBoardNano). Coming from the Arduino ([AVR](https://en.wikipedia.org/wiki/Atmel_AVR)) world, I had a lot to learn. And just for fun, I increased the learning curve even more by not using the industry-standard C/C++ but [Rust](https://www.rust-lang.org/en-US/). While it took a few hours to get it up and running, I was actually surprised at how easy it was.

## Background

Rust is an awesome language. I haven't used it much so far, but I hope to get more fluent in it. I think it's a pretty promising language, especially for microcontrollers used in the Internet of Things, with often [questionable security](https://twitter.com/internetofshit).

Rust is often compared to [Go](https://golang.org/) but I don't think that's fair. While both are new programming languages, they target very different programs. Go has a very big runtime, includes a garbage collector, manages memory very differently from C/C++ and seems to be mostly used as web services (which should be obvious as it comes from Google). It is also a pretty simple/"dumb" language lacking many advanced features like generics. Rust, on the other hand, is designed for memory safety while using concurrency. Mozilla is now trying to [rewrite Firefox](https://medium.com/mozilla-tech/a-quantum-leap-for-the-web-a3b7174b3c12) part for part in Rust, using the [Servo project](https://servo.org/). This means it has to be a very fast and especially very safe language to use. It is thus more low-level than Rust.

If you start looking into Rust on microcontrollers it won't be long until you run into [Jorge Aparicio](https://github.com/japaric), or japaric for short. He has done some awesome things relating to Rust on microcontrollers and he is still working on it! A lot of credit should go to him. His [blog](http://blog.japaric.io/) is also an interesting read.

So first of all, you should read [the Quickstart guide](http://blog.japaric.io/quickstart/). It covers much of the background for this article, but is fairly low-level. I have tried to just create a (relatively) short introduction article.

## Prerequisite

My hardware:

  * A [Blue Pill board](http://wiki.stm32duino.com/index.php?title=Blue_Pill) or similar. I got mine [from AliExpress](https://www.aliexpress.com/wholesale?SearchText=stm32+minimum).
  * A programmer. I'm using an [ST-Link V2 clone](https://www.aliexpress.com/wholesale?SearchText=st-link+v2).

Software:

  * Rust nightly, see the [intallation instructions](https://www.rust-lang.org/en-US/install.html)
  * OpenOCD. I think any version will do. I used 0.9.0 from [jessie-backports](https://packages.debian.org/jessie-backports/openocd) as I wasn't sure the default version was outdated.
  * The arm-none-eabi-gdb package (in Debian, this package is called gdb-arm-none-eabi).
  * Cargo packages `cargo` and `cargo-clone`, including dependencies:
    
        cargo install xargo
        cargo install cargo-clone
        rustup component add rust-src

## Setting up the crate

Now it's time to write some code. Clone the [quickstart crate](https://docs.rs/cortex-m-quickstart/). I have renamed it to `stm32-test` and updated the `Cargo.toml` file accordingly.

```
cargo clone cortex-m-quickstart
```

This quickstart template doesn't contain a working memory map. After some [digging](http://www.st.com/content/ccc/resource/technical/document/datasheet/33/d4/6f/1d/df/0b/4c/6d/CD00161566.pdf/files/CD00161566.pdf/jcr:content/translations/en.CD00161566.pdf), I found the correct values:

```
MEMORY
{
  /* NOTE K = KiBi = 1024 bytes */
  FLASH : ORIGIN = 0x08000000, LENGTH = 64K
  RAM : ORIGIN = 0x20000000, LENGTH = 20K
}

/* This is where the call stack will be allocated. */
/* The stack is of the full descending type. */
/* NOTE Do NOT modify `_stack_start` unless you know what you are doing */
_stack_start = ORIGIN(RAM) + LENGTH(RAM);

/* You can use this symbol to customize the location of the .text section */
/* If omitted the .text section will be placed right after the .vector_table
   section */
/* This is required only on some microcontrollers that store some configuration
   right after the vector table */
/* _stext = ORIGIN(FLASH) + 0x400; */
```

Note that there are reports this device actually has 128K flash storage. But I didn't want to take any risk and kept it at 64K.

Then I copied my program code: the [blinky example](https://github.com/japaric/blue-pill/blob/master/examples/blinky.rs) using the awesome-looking [RTFM framework](http://blog.japaric.io/fearless-concurrency/).

The compiler still doesn't know for which target we're building. This is easily fixed by adding some extra lines to `.cargo/config`. These lines are for the Cortex-M3 processor.

    [build]
    target = "thumbv7m-none-eabi"

And of course we have to add a few dependencies in Cargo.toml. The `cortex-m-quickstart` isn't set up to use the RTFM framework just yet and the packages also aren't yet in [crates.io](https://crates.io/) so we have to add them manually:

```
[dependencies.cortex-m-rtfm]
git = "https://github.com/japaric/cortex-m-rtfm"

[dependencies.blue-pill]
git = "https://github.com/japaric/blue-pill"
```

Now test whether it works:

    ~/src/stm32-test$ xargo build
    [snip]
    Finished dev [unoptimized + debuginfo] target(s) in 0.0 secs

If you see that, you're ready to roll! Well, until the next hurdle, that is setting up the programmer.

## Programming

Now comes the next step: actually connecting to the device. Make sure you connect the debugger correctly to the Blue Pill, see [here](wiki.stm32duino.com/index.php?title=Blue_Pill) for schematics. You have to connect 3.3V, GND, SWDIO and SWCLK. These happen to be the four pins at the bottom (surprise, surprise).

Then plug in the programmer and connect OpenOCD. It took me a while to figure out the correct configuration files, but here they are:

```
~/src/stm32-test$ openocd -f interface/stlink-v2.cfg -f target/stm32f1x.cfg
Open On-Chip Debugger 0.9.0 (2015-06-21-13:00)
Licensed under GNU GPL v2
For bug reports, read
	http://openocd.org/doc/doxygen/bugs.html
Info : auto-selecting first available session transport "hla_swd". To override use 'transport select <transport>'.
Info : The selected transport took over low-level target control. The results might differ compared to plain JTAG/SWD
adapter speed: 1000 kHz
adapter_nsrst_delay: 100
none separate
Info : Unable to match requested speed 1000 kHz, using 950 kHz
Info : Unable to match requested speed 1000 kHz, using 950 kHz
Info : clock speed 950 kHz
Info : STLINK v2 JTAG v17 API v2 SWIM v4 VID 0x0483 PID 0x3748
Info : using stlink api v2
Info : Target voltage: 3.249768
Info : stm32f1x.cpu: hardware has 6 breakpoints, 4 watchpoints
```

Note that if it doesn't work, try pressing (or holding) the reset button on the device. For example, I got this error on a different computer:

```
Error: jtag status contains invalid mode value - communication failure
Polling target stm32f1x.cpu failed, trying to reexamine
Examination failed, GDB will be halted. Polling again in 100ms
Info : Previous state query failed, trying to reconnect
```

But if you see the line about breakpoints and watchpoints, it means your device is connected and running OK. As another sanity check, connect to OpenOCD via telnet and read the board's register values. Note that you have to keep the OpenOCD session alive. You can use a different terminal for telnet.

```
~/src/stm32-test$ telnet localhost 4444
Trying ::1...
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.
Open On-Chip Debugger
> reg
===== arm v7m registers
(0) r0 (/32)
(1) r1 (/32)
(2) r2 (/32)
(3) r3 (/32)
(4) r4 (/32)
(5) r5 (/32)
(6) r6 (/32)
(7) r7 (/32)
(8) r8 (/32)
(9) r9 (/32)
(10) r10 (/32)
(11) r11 (/32)
(12) r12 (/32)
(13) sp (/32)
(14) lr (/32)
(15) pc (/32)
(16) xPSR (/32)
(17) msp (/32)
(18) psp (/32)
(19) primask (/1)
(20) basepri (/8)
(21) faultmask (/1)
(22) control (/2)
===== Cortex-M DWT registers
(23) dwt_ctrl (/32)
(24) dwt_cyccnt (/32)
(25) dwt_0_comp (/32)
(26) dwt_0_mask (/4)
(27) dwt_0_function (/32)
(28) dwt_1_comp (/32)
(29) dwt_1_mask (/4)
(30) dwt_1_function (/32)
(31) dwt_2_comp (/32)
(32) dwt_2_mask (/4)
(33) dwt_2_function (/32)
(34) dwt_3_comp (/32)
(35) dwt_3_mask (/4)
(36) dwt_3_function (/32)
```

The values in the registers will probably be different for your device because I already have a different program running on it. But if this works, you know the connection to the board is OK.

It turns out that the Blue Pill is locked by default. I don't really know why, as unlocking it is pretty easy. I found the instructions [over here](https://sourceforge.net/p/openocd/mailman/openocd-devel/thread/20141226001106204055.1d9b1832%40gpio.dk/). Run this command in the same telnet session as above.

```
> stm32f1x unlock 0
Device Security Bit Set
target state: halted
target halted due to breakpoint, current mode: Thread 
xPSR: 0x61000000 pc: 0x2000003a msp: 0xfffffffc, semihosting
stm32x unlocked.
INFO: a reset or power cycle is required for the new settings to take effect.
```

After this, you should be able to flash the program. Exit the telnet session using `exit` and start GDB. Here is the output, including the GDB invocation:

```
~/src/stm32-test$ arm-none-eabi-gdb target/thumbv7m-none-eabi/debug/stm32-test 
GNU gdb (7.7.1+dfsg-1+6) 7.7.1
Copyright (C) 2014 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.  Type "show copying"
and "show warranty" for details.
This GDB was configured as "--host=x86_64-linux-gnu --target=arm-none-eabi".
Type "show configuration" for configuration details.
For bug reporting instructions, please see:
<http://www.gnu.org/software/gdb/bugs/>.
Find the GDB manual and other documentation resources online at:
<http://www.gnu.org/software/gdb/documentation/>.
For help, type "help".
Type "apropos word" to search for commands related to "word"...
Reading symbols from target/thumbv7m-none-eabi/debug/stm32-test...done.
warning: File "/home/ayke/src/stm32-test/.gdbinit" auto-loading has been declined by your `auto-load safe-path' set to "$debugdir:$datadir/auto-load".
To enable execution of this file add
	add-auto-load-safe-path /home/ayke/src/stm32-test/.gdbinit
line to your configuration file "/home/ayke/.gdbinit".
To completely disable this security protection add
	set auto-load safe-path /
line to your configuration file "/home/ayke/.gdbinit".
For more information about this security protection see the
"Auto-loading safe path" section in the GDB manual.  E.g., run from the shell:
	info "(gdb)Auto-loading safe path"
warning: Missing auto-load scripts referenced in section .debug_gdb_scripts
of file /home/ayke/src/stm32-test/target/thumbv7m-none-eabi/debug/stm32-test
Use `info auto-load python-scripts [REGEXP]' to list them.
(gdb) target remote :3333
Remote debugging using :3333
0xfffffffe in ?? ()
(gdb) monitor arm semihosting enable
semihosting is enabled
(gdb) load
Loading section .vector_table, size 0x130 lma 0x8000000
Loading section .text, size 0x3af0 lma 0x8000130
Loading section .rodata, size 0xf54 lma 0x8003c20
Start address 0x8000130, load size 19316
Transfer rate: 16 KB/sec, 6438 bytes/write.
(gdb) continue
Continuing.
```

There are a few things that I'm doing here. I'll go through it step by step.

    target remote :3333

Connect to the OpenOCD that's running in the other shell.

    monitor arm semihosting enable

I'm not entirely sure what this does, but according to the [Keil docs](www.keil.com/support/man/docs/armcc/armcc_pge1358787046598.htm) it allows the device to enable some debug features. It does not appear to be necessary for a simple example.

    load

Here we are flashing the device! It actually was pretty fast, maybe 1.5s. The file that is loaded on the device is specified using the only parameter given to GDB.

    continue

Start the program. You should be seeing a blinking green LED. Hurray!

But because you're running in a debugger, there are many interesting things you can do. I still have to learn it, but already saw something interesting. When I try to quit using Ctrl+C ('continue' was still running), I got an actual backtrace from the device:

```
(gdb) continue
Continuing.
^C
Program received signal SIGINT, Interrupt.
cortex_m::asm::wfi () at /home/ayke/.cargo/registry/src/github.com-1ecc6299db9ec823/cortex-m-0.2.9/src/asm.rs:60
60	}
(gdb) bt
#0  cortex_m::asm::wfi () at /home/ayke/.cargo/registry/src/github.com-1ecc6299db9ec823/cortex-m-0.2.9/src/asm.rs:60
#1  0x08000c52 in stm32_test::idle (_prio=..., _thr=...) at src/main.rs:58
#2  0x08000d2a in stm32_test::main () at <tasks macros>:16
#3  0x0800242e in cortex_m_rt::lang_items::start (main=0x8000d09 <stm32_test::main>, _argc=0, _argv=0x0)
    at /home/ayke/.cargo/registry/src/github.com-1ecc6299db9ec823/cortex-m-rt-0.2.3/src/lang_items.rs:61
#4  0x08000e58 in main ()
```

This is pretty awesome!

Most of the time, we're in the `WFI` instruction which means "wait for interrupt", effectively sleeping until the next interrupt (external or, in our case, via a timer).
