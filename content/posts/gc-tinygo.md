---
title: "Garbage collection in TinyGo"
date: 2020-09-24
lastmod: 2020-09-24
summary: "An explanation of how garbage collectors work including some pseudocode how a real GC could be implemented."
---
Garbage collection is often seen like a kind of dark magic. And while it is possible to make it very complex, it is possible to write a simple and understandable GC that is still useful in practice.

TinyGo has a number of strategies to deal with memory management, and some differ again by architecture. There is a simple bump-pointer heap implementation for when you only need to allocate some memory during initialization, there is a heap implementation for when you want to work with an external heap (`malloc` in C) but the one that is used most on baremetal systems like microcontrollers is a conservative mark/sweep garbage collector.

In this post I will describe how this conservative collector works, but first I will give some background and describe the bump-pointer collector so you can get a feel for how memory allocators work.

## Memory layout

![memory layout](/assets/gc-tinygo-memory.svg)

This is the RAM memory layout usually used by TinyGo on a microcontroller, from bottom to top:

  * The call stack is put at the bottom of memory. For an explanation why this is a good thing, see [this blog post](https://blog.japaric.io/stack-overflow-protection/). In short, it provides hardware checking for stack overflows even on hardware without special support for it. Most toolchains will default to putting the stack at the top instead, which means an overflowing stack will write to arbitrary other memory instead of causing an error. I hope to explain this more in-depth in a future blog post.  
  * Next follows the `.data` section, which contains global variables that are not entirely zero.
  * Next follows the `.bss` section, which contains all the zero global variables. This split is useful because it means initializing this is very simple (simply zeroing the memory). The name "bss" is a historical curiosity and has no meaning nowadays, just think of it as zero-initialized memory (see [Wikipedia on .bss](https://en.wikipedia.org/wiki/.bss#Origin)).
  * Next follows a large empty space, used as heap.

Remember that the RAM is just that - random access memory. The chip does not care what goes where, so in principle you could choose any memory layout you want with linker scripts. For example, you could change the order of the data, bss, and the heap - but the layout here is simple and there is no reason to change it.

More specifically, this means you can treat the empty heap area as a big block of memory that you can allocate however you want. But the hard question is of course, how would you implement functions such as `malloc` and `free`, or even more relevant to this blog post: how do you implement a garbage collector on top of this?

## The bump pointer allocator

By far the simplest working heap is a so-called bump pointer allocator. The implementation is very simple, I can show it here:

```go
// Ever-incrementing pointer: no memory is freed.
var heapptr uintptr = heapStart

func alloc(size uintptr) unsafe.Pointer {
	size = align(size)
	addr := heapptr
	heapptr += size
	if heapptr >= heapEnd {
		panic("out of memory")
	}
	ptr := unsafe.Pointer(addr)
	memzero(ptr, size)
	return ptr
}

func free(ptr unsafe.Pointer) {
	// Memory is never freed.
}
```

The variables `heapStart` and `heapEnd` contain the addresses determined by the linker. As you might guess, `heapStart` points to the first address usable as the heap while `heapEnd` points to just beyond the heap. You could determine the size of the entire heap in bytes with `heapEnd - heapStart`.

The functionality is super simple. Whenever it is called to get a chunk of heap memory, it reserves the requested amount of memory by increasing `heapStart` (or "bumping the pointer"). If there is no memory left to reserve, it panics. And before returning the memory, it zeroes the memory as required by Go (a C `malloc` would skip the zeroing). The `alloc` function itself is not directly called by the program but calls are inserted automatically by the compiler whenever a local value must be allocated on the heap (such as with `return &point{x: 2, y: 3}`).

Of course, this won't get us very far in actual programs. Programs often allocate memory and shortly after don't need it anymore. While C can get away with requiring a program to call `free` whenever a chunk of memory is not used anymore, in Go and many other modern languages we need some form of automatic memory management.

There are two general ways to implement automatic memory management: reference counting and tracing garbage collectors. Both have their pros and cons, and there are still fierce debates over which approach is better. However, most programming languages favor one over the other: tracing garbage collection is used by languages such as Java, JavaScript, Go, C#, and many others, while reference counting (in some form) is used by Swift and Rust - with Rust making memory management the most explicit and even part of the type system.

As Go favors tracing garbage collection, this is what is used in TinyGo.

## Tracing garbage collectors

This is what is generally referred to when people talk about a "garbage collector". The general idea is the following:

  * When the application wants to get a chunk of memory for its use, it requests such a chunk of memory from the heap (aka the GC). The memory area will be marked as being in use.
  * When memory is getting full, a _garbage collection cycle_ is performed. This may happen either periodically, when the memory is full, or when the application requests it. In more advanced garbage collectors, there is also a distinction between full GC cycles and incremental GC cycles but I won't go into this here.

A garbage collection cycle usually has two phases, depending on the GC design: a "mark" phase in which all reachable objects are marked, and a "sweep" or "compact" phase (depending on the GC) where all unreachable objects are freed: their memory area is no longer marked as allocated and can thus be used in the future for allocation.

During the first (mark) phase, all _reachable_ objects are marked. Ideally we'd like to know _live_ objects, that is, objects that are again needed in the program. Unfortunately this is impractical to determine without solving the halting problem, so we'll settle for something that is actually possible: determining which objects are reachable. Reachable means that some other reachable memory contains a pointer to this reachable object. More specifically, an object is reachable if:

  * A global variable contains a pointer to it.
  * A local variable in one of the goroutines points to it.
  * Another reachable object points to it.

As you can see, the mark phase is recursive. TinyGo avoids this, but I'll leave that out for simplicity.

## A simple garbage collection algorithm

What I will describe here (and what is used in TinyGo and in [MicroPython](https://micropython.org/), from which the GC was [derived](https://github.com/micropython/micropython/wiki/Memory-Manager)) is a conservative mark/sweep garbage collector.

  * **Conservative** means that we don't know exactly what is a pointer and what isn't. 
  * **Mark/sweep** means that the GC cycle is split into two: a marking phase and a sweep (or freeing) phase where unreachable objects are freed.

First of all, the heap is split into blocks. In this case each block is the size of four pointers, but that's an implementation detail. Each block can be in four states: free, head, mark, and tail. The states free, head and tail are used outside a GC cycle. The mark state is used during a GC cycle to mark reachable objects and is otherwise the same as the head state.

Block states are not kept together with the blocks themselves. They are all packed together at one side in heap memory (right now at the start, but it's possible this will change to move to the end of heap memory instead). Think of it as an array of bytes at the start (or end) of the heap area, where each 8-bit byte contains the block state for four blocks: as there are four states each block state can be stored in just two bits. For example, the state of block number 20 is stored in the lowest two bits of the fifth byte, or `blockStates[4] & 0b11`.

![memory layout](/assets/gc-tinygo-memory-heap.svg)

When the heap is initialized at startup, the GC calculates a split between the two so that every block in the heap has an associated state. The GC itself knows how many blocks there are in total and knows where the blocks start, so with some simple math it can determine the address of each block and the address+offset of each block state.

Allocating a block of memory is quite simple. The GC loops through all the available blocks, checks whether they are free, and if it finds a span that's large enough it will allocate it by setting the first block to head and the following blocks (if any) to tail. If it can't find a span, it will run a GC cycle. If it still can't find a span, it will give up with an out of memory panic.

Before we get to the GC cycle, I want to explain what _conservative_ means here. In an ideal case the GC knows exactly for every word of raw memory whether it is a pointer or not. In practice, this may be hard to implement. First of all because it needs a ton of extra metadata and second because it can be hard to know this at all: it needs close cooperation with the compiler to get all this metadata (for example, for the stack). Such cooperation is not possible for a language like C, which can also use a garbage collector[^1].

Instead, what conservative garbage collectors do is that they simply look through the raw memory of an object and check for possible pointers. On most architectures, pointers are aligned which means that for a block that is the size of four pointers, exactly four checks need to be done. It knows something is probably a pointer if it is in the range where blocks are stored on the heap. If it is not in that range it is definitely _not_ a pointer. This means that there will occasionally be false positives: values that are assumed to be pointers even though they are just plain numbers. Luckily, this is not very common on Cortex-M chips which might just have 64kB RAM in a 4GB address space.

Such a false positive is unfortunate, but not a big problem. The worst that can happen is that it accidentally points to an otherwise unreachable object and keeps it longer alive than necessary, potentially reducing the amount of available memory. What is more worrying is a false negative, where something is considered not a pointer but actually is. In practice this is extremely unlikely, the only way I can imagine such a situation could arise is when someone deliberately creates it by using `unsafe` in Go.

So let's look at the algorithm for the mark phase. The basic algorithm is as follows, in Python-like pseudocode:

```python
# This is the mark phase, and is called during a GC cycle just before the sweep.
def mark():
    for ptr in stack:
        if looksLikePointer(ptr):
            markPointer(ptr)
    for ptr in globals:
        if looksLikePointer(ptr):
            markPointer(ptr)

# This is a conservative garbage collector, so if it looks like a pointer assume it is.
def looksLikPointer(ptr):
    return ptr >= heapStart && ptr < heapEnd

# We'll assume we found an object, so iterate through all pointers in the object.
def markPointer(object):
    # The object pointer might not point to the start of the object in Go,
    # so try to figure out where it really starts.
    if blockState(object) == free:
        # This is not a pointer, just a random value that happens to look like a pointer.
        return
    object = findHead(object)
    if blockState(object) == head:
        setBlockState(object, mark)
    else:
        # This object has already been marked, so nothing to do here.
        return
    # Now go through all the fields in the object by inspecting the raw memory:
    for ptr in object:
        if looksLikePointer(ptr):
            markPointer(ptr)
```

I'll describe the algorithm in words too:

  * The mark phase starts with calling `mark()`. It looks through the GC roots: the globals and the stack. It calls `markPointer` for each potential pointer it finds.
  * The function `markPointer` is called for every possible pointer that is found. It first checks whether it points to an allocated object at all, if it doesn't then it must be dealing with something that is not a pointer and it can ignore it. If it does point into an object, it checks the state of the object. If it has been marked already, there is no need to mark it again. The real action happens when it is not yet marked, in which case `markPointer` will inspect the raw memory for the object in search for possible pointers.
  * `looksLikePointer` simply checks whether a given address could be a heap pointer by checking whether it lies within the boundaries of the heap (see above regarding conservative collectors).

After `mark` returns, all reachable objects are found and can be freed. This is a very straightforward algorithm. The GC iterates through all the blocks on the heap, and if it is in state "head" (and not mark, free, or tail) it is the start of an unmarked object. This means the object can be freed. Freeing means the state is changed "head" to "free", and all following tail blocks are marked "free" too. In pseudocode:

```python
# Sweep goes through all memory and frees unmarked memory.
def sweep():
	freeCurrentObject = False
	for block in blocks:
		if blockState(block) == head:
			# Unmarked head. Free it, including all tail blocks following it.
			markFree(block)
			freeCurrentObject = True
		if blockState(block) == tail:
			if freeCurrentObject:
				# This is a tail object following an unmarked head.
				# Free it now.
				markFree(block)
		if blockState(block) == mark:
			# This is a marked object. The next tail blocks must not be freed,
			# but the mark bit must be removed so the next GC cycle will
			# collect this object if it is unreferenced then.
			setToHead(block)
			freeCurrentObject = False
```

## Conclusion

That's all! This is an entire, working, garbage collector. There is no magic involved, it just works directly on a block of raw memory. The GCs in TinyGo and MicroPython are slightly more advanced, but not by much. The main change is some way to avoid recursion which is something to avoid on an embedded device.

Of course, this is a very simple GC. Almost all production GCs such as in Go, Java, Chrome, Firefox, .NET, etc are vastly more complex, tailored to the specific language, and know how to deal with virtual memory. So here are some advantages and disadvantages of this simple GC compared to more advanced garbage collectors:

  * It is very small (in code size), which makes it possible to use on even small microcontrollers.
  * It is relatively slow, with sometimes visible pause times. The Go GC can instead do most of the work of the garbage collector while the application is running with minimal pause times. There are of course tradeoffs but in many cases having low pause times is much preferred. For more information, see [this talk](https://blog.golang.org/ismmkeynote).
  * It is conservative, which means that non-pointer data such as integer slices will still get scanned for pointers and allows for false positives (as described above). On the other hand, this allows for easy interoperability with C as C doesn't have this either: on bare metal devices, the TinyGo heap is also used for `malloc`.
  * Memory never moves, unlike some other GCs (but like the Go GC). Being able to move memory has the big advantage that if the heap is fragmented, you can compact all the used memory together to make sure there is one large free area. This avoids out-of-memory situations when the free memory is scattered over the heap and no chunk is large enough. Unfortunately, it's very hard to allow moving memory when you also have interrupts that can fire any time and may need access to the heap.
  * It cannot currently deal with virtual memory. When it is used on Linux (which is not the default as of this writing), it will simply allocate a bunch of memory on startup and use that as if that is all the memory it has.

If you want to learn more about garbage collectors, I highly recommend [The Garbage Collection Handbook](http://gchandbook.org/). It gives an overview of all the important algorithms that exist with different trade-offs and gives a short overview of some production garbage collectors and how they combine multiple algorithms for specific trade-offs.

[^1]: For example, the [Boehm GC](https://en.wikipedia.org/wiki/Boehm_garbage_collector). It is not so well known that GCC, a compiler toolchain written mostly in C, [uses a garbage collector for memory management](https://gcc.gnu.org/onlinedocs/gccint/Type-Information.html).
