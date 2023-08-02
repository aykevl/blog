---
title: "CGo improvements in TinyGo"
date: 2021-11-18T15:32:27
lastmod: 2021-11-18T15:32:27
summary: "CGo is faster in TinyGo, here's how that works."
---
CGo support is pretty important in Go to interact with existing libraries written in C. However, it's also slow. Right? Not so in TinyGo.

Take a look at the following example:

```go
package main

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

// int add(int a, int b);
import "C"

func main() {
	top, _ := strconv.Atoi(os.Args[1])
	start := time.Now()
	n := C.int(0)
	for i := 0; i < top; i++ {
		n = C.add(n, 1)
	}
	duration := time.Since(start)
	fmt.Println("duration:", duration)
	fmt.Println("ns/op:   ", float64(duration)/float64(top))
}
```

And this C code:

```c
int add(int a, int b) {
	return a + b;
}
```

Basically what it does is measure how long the `add` function takes. It's so short that it doesn't really measure the time to add two numbers but rather the CGo call overhead. Running it with regular Go gives almost 100 nanoseconds per operation:

```
$ go build -o test && ./test 10000000
duration: 940.289394ms
ns/op:    94.0289394
```

That's quite some overhead! It's a lot faster in TinyGo:

```
$ tinygo build -o test && ./test 10000000
duration: 21.974812ms
ns/op:    2.1974812
```

That's about 43x faster! This is because TinyGo does a regular call, not a CGo call. The main Go implementation has to do a lot more work. It needs to switch to the system stack, it needs to convert to the C calling convention, and after the call it needs to switch back to the goroutine stack that called the function.

Of course, they do this for good reasons. It brings several nice benefits:

  * It allows goroutines to run on a small stack at first that grows when needed.
  * It allows for a more sophisticated scheduler between goroutines, where many goroutines are scheduled on just a few system threads.

This significantly lowers the resources needed per goroutine. TinyGo can't do any of this - at least right now. Therefore, it doesn't need all the complex machinery to switch between Go and C code and is therefore a lot faster.

However, this is about improvements. What's the improvement? It's this. When you move the C code inside the `import "C"` block like this (supported in TinyGo starting with version 0.21.0):

```go
// int add(int a, int b) {
//     return a + b;
// }
import "C"
```

You get some rather strange result:

```
$ tinygo build -o test && ./test 10000000
duration: 911ns
ns/op:    9.11e-05
```

This code is claiming that each CGo call takes up 0.0000911ns! That's not possible with any modern CPU. Instead, what is happening is that this call got inlined and the compiler converts this loop:

```go
	start := time.Now()
	n := C.int(0)
	for i := 0; i < top; i++ {
		n = C.add(n, 1)
	}
	duration := time.Since(start)
```

To this after inlining:

```go
	start := time.Now()
	n := C.int(0)
	for i := 0; i < top; i++ {
		n = n + 1
	}
	duration := time.Since(start)
```

And then to this, because the loop can be optimized away:

```go
	start := time.Now()
	n := C.int(top)
	duration := time.Since(start)
```

Well, of course it's going to run fast. It isn't doing anything there. Which is exactly what we want from the optimizer.

And for another new addition to TinyGo, take a look here:

```
$ GOOS=windows tinygo build -o test.exe && wine ./test.exe 10000000
duration: 900ns
ns/op:    9e-05
```

This is CGo, cross compiling a binary from a Linux host to Windows and running it in Wine. The timing is a bit off because the Windows API we use for timing isn't that precise (only up to 100ns granularity) but the overall result still stands.
