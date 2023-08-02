---
title: "Optimizing constant bitshifts on AVR"
date: 2021-02-24T17:54:42
lastmod: 2021-02-24T17:54:42
summary: "The AVR architecture does not natively support arbitrary bit shifts. Therefore, compilers will have to be creative to make shifts short and fast. This post explores how a compiler could emit such constant shifts inline."
---
The AVR instruction set used on microcontrollers from Atmel (now Microchip), does not have shift instructions like most other instruction sets. It can only shift by a single bit at a time, although compilers are often smart enough to shift in a more efficient way.

Lately I've been thinking about how to produce optimal shift instructions in the AVR backend of LLVM, the compiler toolkit that is used by [TinyGo](https://tinygo.org/), Clang, Rust, Swift, and many other compilers. At the moment, it often produces pretty bad (but correct) code that's both big and slow. Recently [Ben Shi](https://reviews.llvm.org/p/benshi001/) has been working on improving this but we're not yet at the point of matching avr-gcc.

In this post I'll investigate how to emit the most efficient sequence of instructions to shift by a constant amount, for any supported integer width. I think there is a strategy to always emit the most compact and efficient instructions, especially if shift expansion is done before register allocation (which appears not to be the case in avr-gcc and is certainly not yet the case in LLVM).

Here I'm only going to describe left shift operations. Right shifting unsigned integers is almost identical but with everything in reverse. Right shifting signed integers is slightly more complicated. I won't cover right shifting here but the basic principles are more or less the same. I also will only cover shifting by a constant amount, as shifting by an amount unknown at compile time is basically just repeatedly shifting by one until enough bits are shifted. Yeah, that's pretty bad but sadly the AVR instruction set doesn't have a better way to do it.

I'll use `i8`, `i16`, `i24` and `i32` as used in LLVM, meaning that these are simple integers. You might be familiar with them if you know Rust, but compared to Rust these integers are sign-less (they are not signed or unsigned). Luckily this signed/unsigned distinction doesn't matter for left shifting.

Regarding registers, I will be using `r0`..`r3` with `r0` containing the least significant byte and `r3` containing the most significant byte. Because the AVR is an 8 bits processor, an `i32` will be contained in four registers.

Warning: I have not tested any of the code samples in this post. While I think they are correct, I haven't verified them so they might be wrong.

## Shift by 1

Let's take a look at what compilers can do to lower shift instructions. Shifting left an `i8` is simple enough:

```
lsl r0
```

The `lsl` instruction (logical shift left) simply shifts the value in `r0` left by one, filling in the empty space with a zero bit. Now let's take a look at shifting an `i16`:

```
lsl r0
rol r1
```

That's slightly more involved. The instruction `lsl r0` not only shifts `r0` left by one, it also stores the most significant bit that got shifted out in the carry flag (C) of the status register. The `rol` instruction (rotate left) is not a regular rotate instruction, it does indeed rotate all the bits but instead of moving the most significant bit to the least significant bit it fills the least significant bit with the carry flag and stores the most significant bit in the carry flag. Therefore, it rotates around nine bits, not eight, including the carry flag. This behavior makes it possible to shift larger integers, for example an `i24`:

```
lsl r0
rol r1
rol r2
```

Or an `i32`:

```
lsl r0
rol r1
rol r2
rol r3
```

You get the idea. I won't be showing many `i32` examples because from `i16` and `i24` it's usually easy to extend the behavior to any integer with a bit width that's a multiple of eight.

## Shift by 2 and 3

Shifting by two or three isn't exactly sophisticated, it's basically the above but repeated. Shifting an `i8` by two:

```
lsl r0
lsl r0
```

Shifting an `i16` by two:

```
lsl r0
ror r1
lsl r0
ror r1
```

Shifting an `i24` by three:

```
lsl r0
ror r1
ror r2
lsl r0
ror r1
ror r2
lsl r0
ror r1
ror r2
```

Sadly there's not a more sophisticated way to do it.

## Shift by 4

Shifting an `i8` can be done somewhat more efficiently using the `swap` instruction:

```
swap r0
andi r0, 0xf0
```

The `swap` instruction swaps the lower 4 bits and the upper 4 bits of the byte. The `andi` instruction then clears the lower 4 bits. This has the same effect as shifting left by four. (Note that I'm only using `r0` here for ease of reading, the `andi` instruction only supports registers `r16..r31`).

Doing the same for `i16` and bigger is a lot more complicated:

```
swap r1
andi r1, 0xf0
swap r0
eor r1, r0
andi r0, 0xf0
eor r1, r0
```

The first two instructions are the same as for `i8` and shift the value in `r1` left by four. However, then there is a complicated dance of XORs:

1. `swap r0` does a similar swap.
2. `eor r1, r0` effectively does `r1 ^= r0` (XOR). This moves the upper four bits of `r0` (that are now in the lower four bits of `r0` due to the swap) into the previously zero lower four bits of `r1`, thereby shifting left by four bits. The upper bits are now garbage, but that will be restored in step 4.
3. `andi r0, 0xf0` zeroes the lower four bits of `r0`, making `r0` fully shifted left.
4. `eor r1, r0` will do the same `r1 ^= r0` operation again, but this time the bottom four bits of `r0` are zero. Remember that `r1` had the correct bits in the lower four bits and had the upper four bits XORed with the upper four bits of `r1`. This operation (`eor r1, r0`) has no effect on the lower four bits in `r0` (which were already correct) but fixes the upper four bits, which now contain the expected value.

All in all, this sequence of instructions can shift two bytes left by four in six instructions.

Going further towards `i24` repeats the same pattern.

```
; shift r2
swap r2
andi r2, 0xf0
; shift r1
swap r1
eor r2, r1
andi r1, 0xf0
eor r2, r1
; shift r0
swap r0
eor r1, r0
andi r0, 0xf0
eor r1, r0
```

## Shift by 5

Shifting by 5 is basically a shift by four plus a shift by one. For `i8`:

```
swap r0
andi r0, 0xf0
lsl r0
```

For `i16`:

```
; shift r1 by 4
swap r1
andi r1, 0xf0
; shift r0 by 4
swap r0
eor r1, r0
andi r0, 0xf0
eor r1, r0
; shift r1 and r0 by 1
lsl r0
rol r1
```

You can also do the `lsl` and `rol` at the start like GCC does.

## Shift by 6

Shifting left an `i8` is still relatively easy:

```
ror r0
ror r0
ror r0
andi r0, 0xc0
```

Remember that `ror` rotates among nine bits, so to rotate two bits across eight bits you need three `ror` operations. At that point the upper two bits contain the previously lower two bits (as intended) and the rest is unimportant so is zeroed using `andi`. The lower six bits contain five of the old bits and the carry bit that was in the status register before so it is really just garbage.

Shifting an `i16` or bigger left by 6 bits is more efficiently done by shifting right by two into a temporary register and then moving them all back. I will indicate the temporary register with `__tmp_reg__`.

```
; clear temporary register
clr __tmp_reg__
; shift by one
lsr r1
ror r0
ror __tmp_reg__
; shift again by one
lsr r1
ror r0
ror __tmp_reg__
; move registers back
mov r1, r0
mov r0, __tmp_reg__
```

This could be done more efficiently before register allocation: you would create a new virtual register for the temporary register and could avoid the two `mov` instructions at the end to move the register back. Later instructions would simply treat the value as being in different registers.

## Shift by 7

Shifting an `i8` is again relatively short and simple:

```
lsr r0
clr r0
ror r0
```

The first `lsr` shift right by one, but more importantly moves the least significant bit into the carry bit of the status register. Then the `clr` will clear the register (but not the carry bit) and the `ror` will shift a zero register with the effect that it moves the carry bit into the most significant bit of `r0`.

Note that we could use a different register after the first instruction. Because all data  is contained in the status register as the carry flag, we could use something like this:

```
lsr r0
clr r5
ror r5
```

If you do this expansion before register allocation, you could assign a new virtual register here to allow the register allocator a bit more freedom in assigning registers. This will be important later for shifting an `i16` by 15.

There are other variations possible too, like this:

```
bst r0, 0
clr r0
bld r0, 7
```

This loads the least significant bit into the T bit of the status register, clears the register, and then copies that bit again into bit 7 (the most significant bit).

Shifting more than 8 bits is a little more complicated, like shifting by 6 this involves shifting right by one and moving registers around, effectively shifting one to the right and then 8 back to the left:

```
; clear temporary register before use
clr __tmp_reg__
; shift 1 to the right into the temporary register
lsr r1
ror r0
ror __tmp_reg__
; shift left by 8
mov r1, r0
mov r0, __tmp_reg__
```

Or shifting an `i24`:

```
; clear temporary register before use
clr __tmp_reg__
; shift 1 to the right into the temporary register
lsr r2
ror r1
ror r0
ror __tmp_reg__
; shift left by 8
mov r2, r1
mov r1, r0
mov r0, __tmp_reg__
```

Again, this can be optimized when it is done before register allocation. In fact, in that case it can be optimized even further by reusing the most significant register as the (new) least significant register. This is done as follows for `i16`:

```
lsr r1
ror r0
clr newreg
ror newreg
```

In this case the register allocator can recognize that `r1` is not used afterwards and optimize to code like this:

```
lsr r1
ror r0
clr r1
ror r1
```

After this operation, the registers are reversed: `r0` contains the most significant bits and `r1` contains the least significant bits.

## Shifting multiples of 8

Shifting multiples of 8 is basically just moving registers around and clearing some registers. For example, to shift an `i16` left by 8:

```
mov r1, r0
clr r0
```

And this is where doing these expansions before register allocation really shines. Instead of moving these registers around, the register allocator could just use `r0` in later instructions that want the upper byte and use the fixed zero register as the lower byte. In the ideal case, that would make this shift zero cost! It even frees an existing register, lowering register pressure and potentially reducing necessary spills and reloads.

Shifting an `i24` left by 8 is similar:

```
mov r2, r1
mov r1, r0
clr r0
```

Or shifting an `i24` left by 16:

```
mov r2, r0
clr r1
clr r0
```

You get the idea. Shifting by multiples of 8 only involves register moves and zeroing registers so is very cheap.

## Shift by more than 8

Shifting by different amounts is as simple as first doing a multiple-of-8 shift and then shifting the remaining registers. For example, shifting an `i24` by 10:

```
; shift left by 8
mov r2, r1
mov r1, r0
clr r0
; shift left by 2 (top 16 bits)
lsl r1
ror r2
lsl r1
ror r2
```

Or shifting an `i16` left by 15:

```
; shift left by 8
mov r1, r0
clr r0
; shift upper register by 7
lsr r1
clr r1
ror r1
```

GCC produces similar code:

```
; shift left by 8, leaving r0 dirty
mov r1,r0
; shift upper register by 7
ror r1
clr r1
ror r1
; zero lower register that was previously left dirty
ldi r0,0
```

However, this code is not perfect, this shift could have been done in just four instructions:

```
lsr r0
clr r1
ror r1
clr r0
```

I _think_ a smart register allocator could figure this out when given the proper hints. As I described above, the two instructions after `lsr` do not have to be the same register and should therefore be given a different virtual register. The register allocator therefore sees something like this:

```
lsr r0
clr newreg1 ; newreg is a new virtual register
ror newreg1
clr newreg2
```

Like before, the `clr` to zero the lower bits could possibly be replaced with a direct use of the zero register by its users, possibly reducing this shift to just three instructions instead of the five that avr-gcc generates.

Shifting an `i24` or larger left by 8+6 or 8+7 is more difficult. The naive (but correct) method to shift an `i24` left by 8+7 (=15) would be as follows:

```
; shift left by 8
mov r2, r1
mov r1, r0
clr r0
; shift left by 7 (see above)
clr __tmp_reg__
lsr r2
ror r1
ror __tmp_reg__
mov r2, r1
mov r1, __tmp_reg__
```

There are four `mov` instructions, certainly there must be a more efficient way to do it:

```
; shift left by 16
mov r2, r0
; shift 16 bits right by 1, using r1 as __tmp_reg__
lsr r1
ror r2
clr r1 ; clear "__tmp_reg__" before use
ror r1
; clear bottom 8 bits
clr r0
```

This makes use of the fact that a shift left by 7 is really just a shift right by 1 over one extra register.

I'm sure this can be further generalized, but I don't see an easy solution. The same pattern sadly doesn't work for shifting an `i32` left by 15. But as always, there is the fallback of first doing the modulo-8 register move and then doing a shift left by 7:

```
; shift left by 8
mov r3, r2
mov r2, r1
mov r1, r0
clr r0
; shift left by 7 (see above)
clr __tmp_reg__
lsr r3
ror r2
ror r1
ror __tmp_reg__
mov r3, r2
mov r2, r1
mov r1, __tmp_reg__
```

I _think_ a good register allocator could, like before, optimize this if given the proper hints. That said, I've checked avr-gcc and it doesn't do a good job of optimizing `i24` and `i32` either (`__int24` and `long`). For `i24` it often produces calls to `__mulpsi3` and for `i32` it usually expands to a loop even though a faster solution should be available.

## Code size optimizations

As you can see, these sequences of code can be relatively long. Instead, the above can in all cases be emitted as a loop instead. For example for an `i8`:

```
ldi __tmp_reg__, 5 ; could be any shift amount
1:
lsl r0
dec __tmp_reg__
brne 1b
```

For `i16`:

```
ldi __tmp_reg__, 5
1:
lsl r0
rol r1
dec __tmp_reg__
brne 1b
```

For `i24`:

```
ldi __tmp_reg__, 5
1:
lsl r0
rol r1
rol r2
dec __tmp_reg__
brne 1b
```

This can easily be extended to any modulo-8 bit width.

The total number of instructions is the number of registers used by the number plus 3, so for shifting an `i16` you need 2+3=5 instructions. For `i8` you need 4 instructions. Because all expansions above for `i8` only need up to 4 instructions, expanding to a loop is never advantageous. For `i16` it can be advantageous sometimes, such as when shifting by 5 (which would otherwise take up 6 instructions). Of course, loops are practically always slower so there is a code size / performance tradeoff. Because of that, avr-gcc will usually expand inline when optimizing for speed (`-O2`) and will use a loop when optimizing for size and the loop uses fewer instructions.

## Comparison with GCC

While writing this post, I ran a lot of code snippets in avr-gcc, making extensive use of [Compiler Explorer](https://godbolt.org/z/7PhqTY). I wanted to figure out whether there was any pattern in the instruction sequences it emits for various shift amounts. And I believe I've found some patterns, which I've already mostly described above. However, I also found a number of limitations (some of which I already mentioned previously). I'll go through them one by one.

First, avr-gcc appears to do shift expansion after register allocation. This is clearly visible in a sample like this:

```c
void foo(int n, int *ptr) {
    *ptr = n << 6;
}
```

The output (with `n` in `r24:r25` and `ptr` in `r22:r23`) is:

```
clr  __tmp_reg__
lsr  r25
ror  r24
ror  __tmp_reg__
lsr  r25
ror  r24
ror  __tmp_reg__
mov  r25, r24
mov  r24, __tmp_reg__
movw r30, r22
std  Z+1, r25
st   Z,   r24
ret
```

The two `mov` instructions at the end aren't necessary, it would have been possible to store the underlying registers directly. Like this:

```
clr  __tmp_reg__
lsr  r25
ror  r24
ror  __tmp_reg__
lsr  r25
ror  r24
ror  __tmp_reg__
movw r30, r22
std  Z+1, r24
st   Z,   __tmp_reg__
ret
```

In some other examples, it does appear to be a bit smarter than this but still I suspect a lot of expansions are done after register allocation.

Another issue with avr-gcc is that while it supports shifting `i8` and `i16` values well, it barely supports `i24` and `i32` (usable as `__int24` and `long`). `i24` is often lowered using calls to `__mulpsi3` (an `i24` multiply function) instead of doing an inline expansion, even with `-O2`. And `i32` is often lowered using many more instructions than necessary or using a loop even though more efficient solutions should be available.

## Conclusion

I've dug deep into how arbitrary constant shifts can be implemented on AVR. I think that when these are implemented before register allocation, they can be as short and efficient as possible. However, even after register allocation I think shift instructions can be lowered close to the optimal sequence.
