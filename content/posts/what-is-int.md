---
title: "What's the int type?"
date: 2021-06-25
lastmod: 2021-06-25
summary: "The int type is present in many programming languages, but their meaning varies. Unlike what many people think, it only indirectly related to pointer size or architecture word size."
---
Many programming languages have an `int` type. It's an integer type but the name itself doesn't say much about what kind of numbers it can hold. Also, the meaning can vary a lot between programming languages. Let's take a look at what they mean across languages.

## C/C++

C and C++ define `int` in the size of numbers it can hold, not in how many bits it is made out of. It is defined as being able to hold all number from -32767 to 32767, inclusive. This definition gives the most flexibility to implementors, as either [two's complement](https://en.wikipedia.org/wiki/Two%27s_complement) and [one's complement](https://en.wikipedia.org/wiki/Ones%27_complement) can be used when an int is 16-bits (even though practically everybody nowadays uses two's complement).

[In practice](https://en.cppreference.com/w/cpp/language/types), `int` is almost always 32-bits, having a range from -2147483648 to 2147483647. This is true for almost all modern systems, including 64-bit systems which still use 32-bit integers (probably for compatibility reasons). There are few exceptions, notably AVR (a mixed 8/16-bit architecture) for which `int` is normally implemented as a 16-bit integer. You might have used the AVR architecture before because it is used on the popular [Arduino Uno](https://store.arduino.cc/arduino-uno-rev3).

## Java

Java is a bit interesting, as it uses the same naming convention as C (`short`, `int`, `long`) but defines these data types precisely. An int is always a 32-bit number and a `long` is always a 64-bit number.

## Go

Go deviates slightly here, in that it defines `int` as either 32-bit or 64-bit and [leaves it at that](
https://golang.org/ref/spec#Numeric_types):

>  There is also a set of predeclared numeric types with implementation-specific sizes:
> 
>     uint     either 32 or 64 bits
>     int      same size as uint
>     uintptr  an unsigned integer large enough to store the uninterpreted bits of a pointer value

The first stable release of Go (version 1.0) used a 32-bit int on all platforms. In [Go 1.1](https://golang.org/doc/go1.1#int) this was changed so that `int` is now a 64-bit integer. This is necessary because Go doesn't have a separate type for array or slice sizes (like `size_t` in C or `usize` in Rust) and uses `int` for this purpose. If `int` were to remain 32-bits on 64-bit platforms, it would not be possible to work with slices that contain more than 2^32-1 entries.

[TinyGo](https://tinygo.org/) follows this convention and uses a 32-bit int even on AVR, as required by the Go specification.

From this, it should be clear that Go and C can have a differently sized integer on the same architecture. This means that `C.int` (when using [CGo](https://blog.golang.org/cgo)) is not necessarily the same size as a Go `int`.

## Conclusion

So what's the `int` type? I'd say it's just a shorthand for an integer type when you don't care a lot about which numbers it can hold.

It should also be clear from this that there are differences between languages and that `int` in one language is not necessarily the same size as `int` in another language. Assuming this could lead to surprises. And `int` most certainly doesn't need to match the underlying pointer size: it might, but in all languages I've mentioned in this post there are cases where it won't.
