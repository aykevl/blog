---
title: "LLVM from a Go perspective"
date: 2019-04-28T17:21:54
lastmod: 2019-05-14T15:27:19
summary: "A high-level overview of LLVM IR, showing how two simple Go functions can be translated to IR."
---
Developing a compiler is an enormous task. Luckily, the advent of compiler libraries such as LLVM make this a whole lot easier, making it possible for a single person to develop a new language that is close to C in terms of performance. Unfortunately, LLVM is an enormous piece of software with little documentation. To try to remedy that, I'll show some code samples in Go and show how they translate to [Go SSA](https://godoc.org/golang.org/x/tools/go/ssa) and then to LLVM IR using the [TinyGo](https://tinygo.org/) compiler. Both the Go SSA and the LLVM IR have been edited a bit for clarity to remove stuff that's not relevant to this explanation.

The first function that I'm going to show is this simple add function:

```go
func myAdd(a, b int) int{
    return a + b
}
```

It's very simple, it can't get much simpler than this. It is translated into the following Go SSA:

```gossa
func myAdd(a int, b int) int:
entry:
	t0 = a + b                                                          int
	return t0
```

This particular representation puts some type hints on the right, you can ignore them most of the time.

This small example already highlights one aspect of SSA: every expression is broken up into its most basic forms. In this case, `return a + b` is actually two operations: adding two numbers and returning the result.

Another thing you can see here are basic blocks, in this case just one: the "entry block". More on that later.

This Go SSA is trivially converted to LLVM IR:

```llvm
define i64 @myAdd(i64 %a, i64 %b) {
entry:
  %0 = add i64 %a, %b
  ret i64 %0
}
```

You can see that the syntax is different, but the structure of the function is basically the same. LLVM IR is a bit more like C in that it puts the return type first in a function declaration and the type of an argument comes before the name of an argument. Also, to simplify IR parsers, globals are prefixed with `@` and locals are prefixed with `%` (a function is also considered a global).

One difference to note here is that the `int` type in Go, which can be either 32-bit or 64-bit depending on the compiler and target, has been decided when the LLVM IR is constructed. This is one of the many reasons why LLVM IR is not platform independent, as many people think: IR constructed for one platform cannot simply be compiled for a different platform (unless [great care is taken](https://llvm.org/devmtg/2019-04/talks.html#Talk_21)).

Another interesting bit to note here is that `i64` is not a signed integer: it is sign-agnostic. Depending on the instruction, it may be signed or unsigned. For addition, it doesn't matter[^1] so there is no signed/unsigned difference there.

What happens next with this IR is not all that important right now. It is optimized (nothing to do for such a simple example) and then emitted as machine code.

The next example I'm going to show is a bit more involved. It's a function that sums a slice of integers:

```go
func sum(numbers []int) int {
    n := 0
    for i := 0; i < len(numbers); i++ {
        n += numbers[i]
    }
    return n
}
```

It is converted to the following Go SSA:

```gossa
func sum(numbers []int) int:
entry:
	jump for.loop
for.loop:
	t0 = phi [entry: 0:int, for.body: t6] #n                            int
	t1 = phi [entry: 0:int, for.body: t7] #i                            int
	t2 = len(numbers)                                                   int
	t3 = t1 < t2                                                       bool
	if t3 goto for.body else for.done
for.body:
	t4 = &numbers[t1]                                                  *int
	t5 = *t4                                                            int
	t6 = t0 + t5                                                        int
	t7 = t1 + 1:int                                                     int
	jump for.loop
for.done:
	return t0
```

This code demonstrates a few more properties of SSA form. The most obvious one is probably that there is no structured control flow anymore. The only control flow operations available are conditional and unconditional jumps, and returns if you count that as control flow.

In fact, you can see the program is not split into blocks using curly braces (like in the C family of languages), but only separated with labels like in assembly languages. SSA form calls these basic blocks. A basic block is an uninterrupted sequence of instructions that starts with a label and ends with a _terminator instruction_ like `return` and `jump`.

The other interesting part here is the `phi` instruction, which is a rather odd instruction and may take a while to grasp. Remember the name SSA? It stands for _static single assignment_. It means that every variable is assigned exactly once, and never changes. This is fine for trivial functions like our `myAdd` above, but does not work with more complicated functions like this `sum` function here. In particular, both the `i` variable as well as the `n` variable change while executing this loop.

SSA works around this using a so-called phi instruction (from the Greek character Φ). It's a bit of magic to make SSA work with languages like C. The result of the instruction is the current value of the variable (`i` or `n`) and it lists the basic blocks that it is coming from as parameters. So take this instruction for example:

```gossa
	t0 = phi [entry: 0:int, for.body: t6] #n
```

It says "if the previous basic block was the entry block, t0 is the constant 0, and if the previous block was for.body, take whatever value was in t6 in that block". This is all a bit magical and hand-wavy, but it makes SSA work. It is harder to understand for humans, but the fact that every value is only set once makes many optimizations much easier.

Note that if you write your own compiler, you will generally not have to deal with this. Even Clang does not generate these `phi` instructions, it uses something called an `alloca` (which is more like a regular local variable). A LLVM optimization pass called [mem2reg](https://llvm.org/docs/Passes.html#mem2reg-promote-memory-to-register) will then convert these allocas to SSA form. TinyGo, however, gets its input from Go SSA form which conveniently is already in SSA form.

Other new things in this piece of IR are that indexing into a slice is split into calculating the address and dereferencing the resulting pointer. You can also see constants directly emitted into the IR (like `1:int`), which weren't there in the `myAdd` example. So with that, let's move on to what it looks like in LLVM IR:

```llvm
define i64 @sum(i64* %ptr, i64 %len, i64 %cap) {
entry:
  br label %for.loop

for.loop:                                         ; preds = %for.body, %entry
  %0 = phi i64 [ 0, %entry ], [ %5, %for.body ]
  %1 = phi i64 [ 0, %entry ], [ %6, %for.body ]
  %2 = icmp slt i64 %1, %len
  br i1 %2, label %for.body, label %for.done

for.body:                                         ; preds = %for.loop
  %3 = getelementptr i64, i64* %ptr, i64 %1
  %4 = load i64, i64* %3
  %5 = add i64 %0, %4
  %6 = add i64 %1, 1
  br label %for.loop

for.done:                                         ; preds = %for.loop
  ret i64 %0
}
```

Again, the structure is the same with slightly different syntax. For example, phi nodes have swapped the value and the label. However, there are a few things to note here.

First of all, the signature is quite different. LLVM does not natively support slices, so as an optimization the TinyGo compiler (that produced this IR) has split it up in its individual pieces. It could have used a struct for the 3 elements of a slice (ptr, len, cap) but splitting it up enables some optimizations. Other compilers might represent a slice in a different way depending on the calling convention of the target platform.

Another interesting thing in this IR is the `getelementptr` instruction (often shortened to GEP). This instruction does pointer arithmetic and is used to get a pointer to an element in the slice. For example, compare it with the following C code:

```c
int* sliceptr(int *ptr, int index) {
    return &ptr[index];
}
```

Or the following, which is equivalent:

```c
int* sliceptr(int *ptr, int index) {
    return ptr + index;
}
```

Most importantly, `getelementptr` does not do any dereferencing, it only calculates a new pointer based on an existing pointer. You could think of it as a `mul` and `add` at the hardware level. For more information, see [the often misunderstood GEP instruction](https://llvm.org/docs/GetElementPtr.html).

Another interesting bit in this IR is the `icmp` instruction, which is a generic instruction to implement integer comparisons. The result is always an `i1`: a boolean. In this case, the comparison is a `slt`, which is a "signed lower than" because we're comparing two ints. If we were to compare two unsigned integers, the instruction would be `icmp ult`. Floating point comparisons use a different instruction with similar predicates: `fcmp`.

And with that, I think I've covered the most important bits of LLVM IR. There is of course much more to it. The IR has many annotations to let optimization passes know of certain facts the compiler knows but cannot be expressed in a different way in the IR. Examples are an `inbounds` flag on the getelementptr instruction or a `nsw` and `nuw` flag that can be added to the add instruction. Or a `private` linkage that tells the optimizer this function will not be referred to outside of the current compilation unit, enabling lots of interesting interprocedural optimizations like dead argument elimination.

For more information, see the following pages:

  * The [language reference](https://llvm.org/docs/LangRef.html), which you will frequently refer to when developing a LLVM-based compiler.
  * The [Kaleidoscope tutorial](https://llvm.org/docs/tutorial/), which shows how to implement a compiler for a very simple language.

Both will be very valuable sources of information when you develop your own compiler.

[^1]: In C, overflowing a signed integer causes undefined behavior so the Clang frontend adds a `nsw` flag (no signed wrap) to the operation, which signals to LLVM that it can assume the addition never overflows. This can be important for some optimizations: for example adding two `i16` values on a 32-bit platform (with 32-bit registers) needs a sign-extend operation after the addition to stay in the `i16` range. Because of this, it is often more efficient to do integer operations on the native register size.
