---
title: "Debug AVR programs using simavr and avr-gdb"
date: 2020-06-22T21:03:44
lastmod: 2020-06-22T21:03:44
summary: "Quick note to get started with debugging AVR programs in a simulator"
---
Lately I've been working on improving AVR support in LLVM. While more and more people are moving to more powerful Cortex-M chips, these small 8-bit chips are still used a lot and it would be nice to have good LLVM support for this architecture so that modern programming languages can be used, which are often built using LLVM. For this, I need a good debugger to debug miscompilations.

To debug AVR chips, you often don't need a hardware debugger. In many cases (in particular compiler development) there is no need for hardware at all, a simulator will do. I particularly like [`simavr`](https://github.com/buserror/simavr), which is stable, relatively easy to use, and has broad AVR chip support.

Here is a very simple example program to get started:

```c
#define F_CPU 16000000

#include <avr/io.h>
#include <util/delay.h>

void main() {
    DDRB = 0xff;
    while (1) {
        PORTB = 0xff;
        _delay_ms(100);
        PORTB = 0;
        _delay_ms(100);
    }
}
```

Compile it with `avr-gcc`, with debug information enabled:

```
$ avr-gcc -Os -g -o blink.elf blink.c -mmcu=atmega328p
```

Now start `simavr`:

```
$ simavr -g -m atmega328p blink.elf
Loaded 178 .text at address 0x0
Loaded 0 .data
avr_gdb_init listening on port 1234
```

The `-g` flag to `simavr` tells it to wait for an incoming debug connection. The program counter will be initialized to 0 (the reset vector) but it will wait there.

Now fire up GDB, in a new shell:

```
$ avr-gdb blink.elf
GNU gdb (GDB) 8.2.1
Copyright (C) 2018 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
Type "show copying" and "show warranty" for details.
This GDB was configured as "--host=x86_64-linux-gnu --target=avr".
Type "show configuration" for configuration details.
For bug reporting instructions, please see:
<http://www.gnu.org/software/gdb/bugs/>.
Find the GDB manual and other documentation resources online at:
    <http://www.gnu.org/software/gdb/documentation/>.

For help, type "help".
Type "apropos word" to search for commands related to "word"...
Reading symbols from blink.elf...done.
(gdb) 
```

Debug symbols have been read for the binary, but there is no connection yet to simavr. This is simple enough to establish:

```
(gdb) target remote :1234
Remote debugging using :1234
0x00000000 in __vectors ()
(gdb) 
```

You can see here that the reset vector has been initialized to 0. Initialization code is usually not very interesting unless you are writing a compiler or do other low-level things, so let's just run the program until it hits main. First by setting a breakpoint (`b main`) and then by continuing the program with `c` (or `continue`):

```
(gdb) b main
Breakpoint 1 at 0x80: file blink.c, line 7.
(gdb) c
Continuing.
Note: automatically using hardware breakpoints for read-only addresses.

Breakpoint 1, main () at blink.c:7
7	    DDRB = 0xff;
(gdb) 
```

As you can see, the debugger has stopped at the first line of the main function. The line it is pointing to is the line that has not yet been run.

You can see what is in the `DDRB` register at startup using the `print` command:

```(gdb) print DDRB
$2 = 0 '\000'
(gdb) 
```

Clearly simavr has initialized the register to zero.

Now run the program and stop it at the next line:

```
(gdb) n
9	        PORTB = 0xff;
(gdb) print DDRB
$3 = 255 '\377'
(gdb) 
```

As you can see, after continuing to the next line the `DDRB` register has changed value.

As an aside, you may be wondering why it won't stop at the `while (1)` line in between. This is because there is no instruction in between where the debugger could stop. Loops don't exist at the machine code level. Instead, the last instruction of `main` is just a jump back to the start of the loop and the start of the loop doesn't take up any instructions.

I hope this quick note will be useful to some people.
