---
title: "Goroutines in TinyGo"
date: 2019-02-25
lastmod: 2019-02-25
summary: "TinyGo uses LLVM coroutines to implement goroutines. This post explains what coroutines are and how they're used to implement goroutines."
---
Go uses goroutines for mostly-cooperative multitasking. In general, each goroutine has a separate stack where it can store things like temporary values and return addresses. At the moment the main Go compiler starts out with a 2kB stack for each goroutine and grows it as needed.

TinyGo is different. The system it uses for goroutines is based on the async/await model like in C#, JavaScript and now also C++. In fact, we're borrowing the C++ implementation that's used in Clang/LLVM. The big difference here is that TinyGo inserts async/await keywords automatically.

I'm using [this piece of code](https://play.golang.org/p/TiCPm5G8or1) as an example. For simplicity, I'm using `time.Sleep`, but any blocking operation could be used (example: channel operations).

```go
func main() {
	go background()
	time.Sleep(2 * time.Second)
	println("some other operation")
	n := compute()
	println("done:", n)
}

func background() {
	for {
		println("background operation...")
		time.Sleep(time.Second)
	}
}

func compute() int {
	time.Sleep(time.Second)
	println("blocking operation completed")
	return 42
}
```

Imagine you would write Go like this:

```go
async func main() {
	go background()
	await time.Sleep(2 * time.Second)
	println("some other operation")
	n := await compute()
	println("done:", n)
}

async func background() {
	for {
		println("background operation...")
		await time.Sleep(time.Second)
	}
}

async func compute() int {
	await time.Sleep(time.Second)
	println("blocking operation completed")
	return 42
}
```

Luckily, you don't have to worry about the [color of your function](http://journal.stuffwithstuff.com/2015/02/01/what-color-is-your-function/) in Go, but I've chosen to use this as an implementation strategy for TinyGo. The reason is that TinyGo also wants to support WebAssembly and WebAssembly does not support efficient stack switching like basically every other ISA does: the stack has been hidden entirely for security reasons. So I've decided to use coroutines[^1] instead of actually separate stacks.

## How does this work?

TinyGo uses [LLVM coroutines](https://llvm.org/docs/Coroutines.html) under the hood, which are also used by Clang to support C++ coroutines.

In essence, a compiler pass in TinyGo converts the above code to code with roughly this structure:

```go
func main(parent *coroutine) {              // note: parent is always nil because this is main
	hdl := llvm.makeCoroutine()             // my coroutine
	background(nil)                         // not passing a parent as it is a new independent goroutine
	runtime.sleepTask(hdl, 2 * time.Second) // mark this function as sleeping
	llvm.suspend(hdl)                       // suspend this coroutine
	println("some other operation")
	compute(hdl)                            // continuation-passing style
	llvm.suspend(hdl)
	n := hdl.data                           // note: not yet implemented
	println("done:", n)
	runtime.resumeTask(parent)              // re-activate parent (unnecessary)
}

func background(parent *coroutine) {
	hdl := llvm.makeCoroutine()
	for {
		println("background operation...")
		runtime.sleepTask(hdl, time.Second) // mark this function as sleeping
		llvm.suspend(hdl)
	}
	// code is unreachable so there is no runtime.resumeTask call.
}

func compute(parent *coroutine) {
	hdl := llvm.makeCoroutine()
	runtime.sleepTask(hdl, time.Second) // mark this function as sleeping
	llvm.suspend(hdl)
	println("blocking operation completed")
	parent.data = 42                    // note: not yet implemented
	runtime.resumeTask(parent)          // re-activate parent
}
```

Any function that does a blocking operation is considered blocking, including calling a blocking function (but not starting a blocking goroutine, that's a non-blocking operation). Non-blocking functions are left alone.

It may be hard to follow what's going on here, so here is some explanation:

  * Coroutines will be split at so-called "suspend points" by a later compiler pass implemented in LLVM. Local variables will be lost at such suspend points.
  * To keep these local variables around and to store some metadata about the coroutine, a so-called "coroutine frame" is allocated at the function start by `llvm.makeCoroutine`. This is a somewhat complicated process that does a heap allocation, I've left it out for simplicity.
  * LLVM will save local variables that are needed after the suspend point right before the suspension, and reloads them afterwards. This is completely transparent and you don't have to worry about how this works exactly.
  * Sleeping is implemented by first calling into the scheduler (`runtime.sleepTask`) to queue the coroutine for re-activation at the given time, and then suspending. The scheduler will make sure this coroutine is resumed at the given time.
  * Return is implemented by directly re-activating the parent, like [continuation-passing style](https://en.wikipedia.org/wiki/Continuation-passing_style). A value can be returned by storing it in the frame of the parent coroutine.  
    Returning a value has not yet been implemented.

In essence, every blocking function is turned into a coroutine. LLVM splits such coroutines into 3 functions: a setup function, a resume function, and a destroy function:

  * The **setup function** contains all code up to the first suspend point. It initializes the coroutine frame and executes part of the code.
  * The **resume function** is a big state machine. It contains a big switch statement that jumps to the right position in the function, before hitting a suspend point and returning again.
  * The **destroy function** frees the coroutine frame. It is not necessary in TinyGo due to the garbage collector, but LLVM includes it and there is no easy way to avoid it.

For example, the `background` function [could be transformed](https://llvm.org/docs/Coroutines.html#coroutine-transformation) into this:

```go
func background(parent *coroutine) {
	hdl := llvm.makeCoroutine()
	println("background operation...")
	runtime.sleepTask(hdl, time.Second) // mark this function as sleeping
}

func background.resume(hdl *coroutine) {
	println("background operation...")
	runtime.sleepTask(hdl, time.Second) // mark this function as sleeping
}

func background.destroy(hdl *coroutine) {
}
```

There is only a single suspend point so no need for a state machine, but a function with multiple suspend points would use a state machine here.

## What about indirect calls like function pointers?

Good question! And not a completely solved one at this time. Interface calls are already lowered to a [switch + direct call](https://aykevl.nl/2018/12/tinygo-interface) so they should be relatively easy to support, but there are some missing pieces that prevent them from working well. Function pointers are not supported at all at the moment, but I hope to fix that by determining all possible called functions statically and using that in the callgraph.

As you can see, coroutine support isn't quite finished yet.

In the end, I think I'll try to move to a different implementation on supported architectures that uses real stacks, like Cortex-M. This is not portable but will likely be more efficient on the given hardware. I would also want to avoid stack overflows that don't panic in such a scheme, but implementing that efficiently is going to be hard. However, I do think it's possible.

## Recommended reading

  * [Asynchronous Everything](http://joeduffyblog.com/2015/11/19/asynchronous-everything/)  
    How Midori OS (an experimental language and OS by Microsoft) solves concurrency. It is very similar to how TinyGo has solved it.
  * [What Color is Your Function?](http://journal.stuffwithstuff.com/2015/02/01/what-color-is-your-function/)  
    A critique on the async/await concurrency system in many programming languages.

[^1]: Meaning stackless [coroutines](https://en.wikipedia.org/wiki/Coroutine), as implemented in C#, JavaScript, C++, etc. This means: a function that has 4 operations: call, return, suspend, and resume. And contains some data. Regular functions and generators are both subsets of coroutines.
