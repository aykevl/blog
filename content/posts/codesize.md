---
title: "Code size optimization for microcontrollers"
date: 2018-04-27T18:28:44
lastmod: 2018-04-27T18:28:44
summary: "How to optimize code size for microcontrollers, including compiler options and lots of coding habits that produce smaller and often more efficient code."
---
Microcontrollers can vary greatly in the amount of available flash (32kB - 512kB is common) and thus how big the programs can be running on them. This means a common problem is not having enough ROM/flash for a project. While working on [MicroPython](https://micropython.org/) and building a [boot loader](/2018/01/mbr-softdevice-internals) for a microcontroller I've figured out all kinds of ways to reduce code size. Here is what I've found out so far, from easy to hard.

First of all: **measure everything**! Code size is very easy to measure, just by using the `size` command on the resulting binary. For example:

    $ arm-none-eabi-size firmware.elf

To easily keep an eye on code size, put something like this in your Makefile right after generating the ELF binary so you'll see it with every build. And it helps to make sure you only apply the optimizations that are actually helpful and don't accidentally increase code size.

I'm going to assume GCC here. Most options should be easy to translate to Clang. The proprietary ARM compiler is nowadays based on Clang so shouldn't be very difficult either, but I have no experience with it. More arcane compilers may be more difficult (IAR anyone?) and you might reconsider your choice of compiler anyway.

## Compiler

First of all, the easy stuff: compiler options. Easy to apply in most cases and well-written code won't be affected by these changes (except perhaps LTO for legitimate reasons, see below). Changing a few flags will generally provide a quite large improvement.

* Optimize for code size: `-Os`. This enables most of the optimizations of `-O2` and changes a few options in favor of code size. This should be the bare minimum of compiler optimizations. Clang also has `-Oz` which is more aggressive, but I haven't tried it.
* Eliminate dead code: put `-ffunction-sections -fdata-sections` in your `CFLAGS` and `-Wl,--gc-sections` in your `LDFLAGS`. Dead code elimination also improves code readability: most uses of conditional compilation are unnecessary with it and I guess most C programmers will agree less preprocessor statements is a good thing. Be warned that this may eliminate code that is actually required, even the whole binary! You'll see it quick enough in the output of `size`: if the output suddenly gets unrealistically low you know what's going on. Fix this with a [`KEEP` command](https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/4/html/Using_ld_the_GNU_Linker/sections.html#INPUT-SECTION-KEEP) in the linker script. In ARM microcontrollers it's enough to `KEEP` the initialization vector.
* Link-time optimization: a far more aggressive way to optimize code is [link time optimization (LTO)](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html#index-flto). It should also improve performance. What GCC basically does, is compile the C source code form into an intermediary form (called GIMPLE) and store that in the .o file, instead (or along) the regular relocatable machine code. Then, at link time, the linker recognizes it is dealing with this intermediary representation with a plugin and finishes the last step of compiling. The advantage of this is that at link time the compiler/linker can inline across all functions, so that for example `main()` is inlined in `_start()` and `_start()` is inlined in `Reset_Handler`.  
  Be warned, though: LTO can sometimes *increase* code size due to inlining. I haven't found a way yet to avoid such inlining (you could try `-finline-limit`). Also, as dead-code elimination is now done by the compiler instead of the linker you have to tell the compiler about used symbols in assembly. In GCC, this is done with `__attribute__((used))` applied to the called function.
* A nice trick to reduce code size is with `-fshort-enums`. This is uncommon on desktops but often done on embedded devices to reduce memory size. Note that this *breaks ABI compatibility* so should only be enabled if you know all compiled code has this flag (think of the runtime library or binary libraries from the silicon vendor). Read more about the dangers [over here](https://oroboro.com/short-enum/).
* I've read about the option `-finline-limit` but I haven't tried it myself. It should be able to reduce code size in some cases by not inlining some functions.
* Change a library for a smaller one (think of libc, libm, and silicon vendor provided libs). Also, don't link against libraries you're not actually using.
* Some code has extra logs and asserts for development builds. These should probably be disabled on release builds, or when you're not debugging.
* If you're using floats and don't require double precision, make sure you're actually using floats. By default, literal floats are interpreted as doubles unless they have an `f` suffix (like `3.14159f`). To make sure they're interpreted as floats use `-fsingle-precision-constant -Wdouble-promotion`. Also, check the math library you're using: by default functions like `sqrt` operate on doubles, not float (use an `f` suffix there as well, e.g. `sqrtf`). Using floats instead of doubles will reduce code size and increase performance on microcontrollers, especially as some have support for floats but not doubles (like the Cortex-M4F).

## The code itself

The way you write code affects how big the resulting machine code will be. Here is a list of suggestions that you can try:

* Learn to read assembly code and learn how the linker and startup code works - this knowledge is invaluable! I've used `objdump -d` (and variations like `objdump -Dz`) many times to debug code size issues. Startup code may sound scary, but on the Cortex-M series of microcontrollers it's actually not that difficult: you can do all of it in C. The only thing it really does is setting up some peripherals (vendor-specific), applying fixes for product anomalies (again vendor specific) but most importantly it initializes global variables (`.bss` and `.data`) and then calls `_start()` or `main()`.
* Check the product anomalies of your chip and whether the workarounds implemented (usually in the startup code) are still relevant. Most modern microcontrollers have tens of design mistakes or anomalies which require software workarounds. You may be able to remove some of them if you have a newer and fixed chip variant.
* Make local functions and global variables static if they are used in the same source file. This makes the work of the optimizer a lot easier, as it now knows all the places where these functions/variables are used. Static is less useful when using LTO.
* Manually unroll (or even re-roll) very small loops. Experiment with this to see what results in the most optimal code.
* Use the default data types of the machine. For example, using `uint32_t` will often result in smaller code than `uint16_t` on a 32-bit machine as it doesn't need to emulate overflow behavior on arithmetic operations like add. Similarly, use the smallest possible integer size (usually `uint8_t`) on 8-bit microcontrollers.
* Avoid unnecessary abstractions. Even though a lot of abstractions can be optimized away by the compiler (in which case you should pick the most readable option!), some abstractions will bloat the code. You could also try to rearchitect the abstractions you've chosen to make the abstraction layer as small as possible (without leaking).
* Use float instead of double, and call floating point math library functions (with an `f` suffix).
* Make as much global data `const` as possible. Marking a global variable `const` tells the compiler that it can be put in flash instead of RAM, greatly reducing RAM consumption and usually reducing flash consumption as well. Note that the `size` command may show a bigger `.text` section but that's only because it doesn't include them in `.data` anymore: the actual binary should be smaller.
* Try to use global `const` variables instead of locals.
* Try to use local stack variables instead of globals. Allocating on the stack is usually cheaper than referencing a global variable, but watch out for increased stack usage.
* Mark unreachable code as unreachable by inserting the `__builtin_unreachable()` pseudo-call. This helps the optimizer to eliminate dead code.
* Try to mark functions inline or define them as preprocessor statements. This should not be needed, but compilers aren't always so smart about inlined functions (looking at you, GCC).
* Try multiple small variations of the same algorithm and pick the one that produces the smallest code.
* Do not zero-initialize global variables. Uninitialized global variables are always zeroed. This is specified by the C standard and done in the startup code so you can rely on it. If you're not sure, set them to an initial zero value which has the same effect.
* Try to make global variables zero-initialized if they need to have some initial value. A large struct with just one non-zero element will waste .data so might be better split off into a separate global variable. If you have a variable containing the state of something (uninitialized, initialized, powered on, transmitting) make sure the initial value is zero.
* Avoid `memset` to 0 for stack-allocated structs. You're usually better off manually initializing every member. But watch out for 'backwards-compatible' changes to struct definitions in library code: some libraries may expect you to zero-initialize all members so old code is compatible with new libraries.
* Extract common code from multiple functions and put it in a single function.
* Make sure struct members do not leave "holes" due to alignment. An easy way to ensure this is by ordering them by size. An excellent explanation of why this is the case and how to avoid it has been [written by Eric S. Raymond](http://www.catb.org/esr/structure-packing/). Don't add `__attribute__((packed))`: most microcontrollers do not allow unaligned memory accesses and it is often slower on high-end processors.

Some of the suggestions above may decrease code readability but this does not have to be so! Most can be done just fine while keeping the code readable, they just shuffle things around a bit. And remember: a small output does not mean a small input. It is perfectly possible to have a multi-line statement that constructs a constant to write to a register which is transformed into a single constant. Rely on the compiler optimizing things to make the code easy to read and refactor and help it where it cannot figure out stuff on it's own. And remember that code that is easy to read and understand is also easy to optimize at a later time.

## My compiler options

I have a few standard compiler options I use almost always:

* `-Wall -Werror`: Enabling warnings will help you catch bugs earlier, although it may in some cases be a bit frustrating during development. I have found many bugs much earlier due to these warnings.
* `-Os`: Nothing to say here. For desktops I tend to use `-O2` instead, which produces far better code and is better tested than the default (`-O0`).
* `-flto`: Enabling link-time optimization often leads to smaller code but it also enables better habits by allowing good coding practices like putting functions in different source files without harming code size.
* `-g`: Enabling debugging symbols won't affect the binary size unless you messed up your linker scripts and will make debugging much easier. Leave it on by default so you won't have to worry about it. It will make 'undefined symbol' errors from the linker a lot easier to read, for example.

## Closing

That's it for now! There are probably many more things you can do but these are the main things I've found. But please remember: measure everything and don't sacrifice code readability for a small gain.
