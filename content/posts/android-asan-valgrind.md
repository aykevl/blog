---
title: "Using AddressSanitizer and Valgrind on Android recovery"
date: 2017-06-02
lastmod: 2017-06-02
summary: "How to use memory checking tools inside an Android recovery to detect things like buffer overflows. A recovery system like TWRP is quite different from a normal Android image, so the official guides apply only partially and it needs some manual work to make these tools work. Here's how I did it."
---
Debugging memory issues can be very hard or almost impossible when done by hand. Luckily it's relatively easy to detect memory issues with the proper tools. Unfortunately, using them while working on an Android recovery like TWRP is much harder, as the environment is very limited and a bit different from a normal Android system.

There are many kinds of memory errors, not all of which are detected. For example:

* NULL-pointer dereferences
* Buffer overflows (read/write)
* Reading from uninitialized memory
* Race conditions: reading from one thread while writing from another thread
* ...and many more

There are two important tools to detect these issues supported by the Android build system: [AddressSanitizer](https://source.android.com/devices/tech/debug/asan) (or ASan) and [Valgrind](https://source.android.com/devices/tech/debug/valgrind). They work a bit differently and have their pros and cons.

* **AddressSanitizer** is a simple compile flag (`-fsanitize=address`) for Clang[^1] and a runtime library + linker. It is very fast as it inserts only simple checks in the output.
* **Valgrind** operates on unmodified binaries. It acts like a VM interpreting the whole binary but checks every memory operation for safety, thus using it incurs a big slowdown. The advantage is that you don't have to recompile binaries. In my limited experience it's more thorough but can sometimes change how the program behaves. It also needs a library to run but not a modified linker.

Which one you choose mostly depends on which is easier to setup or provides the required features.

**NOTE:** This guide only applies to Android recovery images (like [TWRP](https://twrp.me/)), not to regular Android ROMs. Some of the information might still be useful for regular ROM development, though.

## Differences in a recovery

I'm working with [TWRP](https://twrp.me/) so your recovery might be different.

Recovery images are very limited and are a bit different from regular Android ROMs. The relevant differences are:

* The root directory is not `/system` but `/sbin`.
* Binaries and libraries are not in a separate directory. They are both stored directly inside `/sbin`, and not in a subdirectory like in the full Android image (`/system/bin` and `/system/lib`).

## Valgrind

Setting up Valgrind is actually pretty easy. First of all, build the binary:

    $ mmma external/valgrind

You'll find the resulting binary in `out/target/product/<device>/system/bin/valgrind` and the library in `out/target/product/<device>/system/lib/valgrind`. What I have done is to copy the binary to `/sbin/valgrind` and the library to `/sbin/valgrind-lib`.

As the binary expects the library somewhere else (probably `/system/lib`), you have to tell where it is. Luckily, that's very easy. Just set the [`VALGRIND_LIB`](https://unix.stackexchange.com/a/239453/234161) environment variable, like so:

    $ VALGRIND_LIB=/sbin/valgrind-lib valgrind ls

But this won't work just yet. It'll give the confusing error `not found`. It's not the Valgrind binary that isn't found, or the library, or the `ls` binary it tries to run. It's something it expects in `/system/bin`. Symlinking it to `/sbin` solves the issue:

    $ ln -s /sbin /system/bin

Make sure `/system` isn't mounted before you do this[^2].

And now you can see Valgrind in action in all it's glory:

```
~ # VALGRIND_LIB=/sbin/valgrind-lib valgrind ls
==2142== Memcheck, a memory error detector
==2142== Copyright (C) 2002-2015, and GNU GPL'd, by Julian Seward et al.
==2142== Using Valgrind-3.11.0.SVN.aosp and LibVEX; rerun with -h for copyright info
==2142== Command: ls
==2142== 
WARNING: linker: /sbin/valgrind-lib/vgpreload_core-arm-linux.so: unsupported flags DT_FLAGS_1=0x421
WARNING: linker: /sbin/valgrind-lib/vgpreload_memcheck-arm-linux.so: unsupported flags DT_FLAGS_1=0x421
acct                      etc                       oem                       sepolicy
boot                      external_sd               preload                   service_contexts
bugreports                file_contexts             proc                      sideload
cache                     file_contexts.bin         property_contexts         storage
charger                   fstab.universal3470       recovery                  supersu
config                    init                      res                       sys
d                         init.rc                   root                      system
data                      init.recovery.service.rc  sbin                      tmp
default.prop              init.recovery.usb.rc      sdcard                    twres
dev                       license                   seapp_contexts            ueventd.rc
efs                       mnt                       selinux_version           ueventd.universal3470.rc
==2142== 
==2142== HEAP SUMMARY:
==2142==     in use at exit: 17,686 bytes in 258 blocks
==2142==   total heap usage: 547 allocs, 289 frees, 42,878 bytes allocated
==2142== 
==2142== LEAK SUMMARY:
==2142==    definitely lost: 11,280 bytes in 46 blocks
==2142==    indirectly lost: 328 bytes in 2 blocks
==2142==      possibly lost: 0 bytes in 0 blocks
==2142==    still reachable: 6,078 bytes in 210 blocks
==2142==         suppressed: 0 bytes in 0 blocks
==2142== Rerun with --leak-check=full to see details of leaked memory
==2142== 
==2142== For counts of detected and suppressed errors, rerun with: -v
==2142== ERROR SUMMARY: 0 errors from 0 contexts (suppressed: 0 from 0)
```

## AddressSanitizer

Using AddressSanitizer is very similar. The big difference is that you have to add support for individual binaries. Most of the information from the [official documentation](https://source.android.com/devices/tech/debug/asan) still applies, but there are some extra things you need to set on a recovery image.

First, build AddressSanitizer:

    $ mmma external/compiler-rt/lib/asan

And build your binary using ASan. This is simply a matter of adding this to your program's `Android.mk`:

    LOCAL_SANITIZE:=address
    LOCAL_CLANG:=true

I would recommend taking the binary somewhere inside `out/target/product/<phone>/obj/RECOVERY_EXECUTABLES` as these aren't stripped of debug symbols. Use `find` to well... find it.

Then copy the required runtime libraries to your phone. These are the library (`out/target/product/<phone>/system/lib/libclang_rt.asan-arm-android.so`) and the special linker (`out/target/product/<phone>/system/bin/linker_asan`). Store them both in `/sbin`.

Now ASan, of course, expects them to be stored in `/sytem/bin` and `/system/lib`, so we have to make two symlinks:

    $ ln -s /sbin /system/bin
    $ ln -s /sbin /system/lib

Now you should be able to run the binary on your phone using AddressSanitizer. I don't have an example, unfortunately, as I don't want to recompile everything.

I hope you'll find this guide useful. It took me a while to figure this out so maybe it helps someone. Using these tools I've found a few memory issues in the new [adb backup functionality of TWRP](https://github.com/omnirom/android_bootable_recovery/commit/ce8f83c48d200106ff61ad530c863b15c16949d9) that caused errors during restore for me on the Samsung Galaxy S5 mini (but apparently nobody else). I hope these fixes will soon land in TWRP.

[^1]: It has also been [ported to GCC](https://github.com/google/sanitizers/wiki/AddressSanitizerClangVsGCC) but I haven't seen it used in Android that way, and using Clang instead of GCC is pretty easy anyway.

[^2]: You can also try installing Valgrind/AddressSanitizer to the ROM and using them from there, but I haven't tried this.
