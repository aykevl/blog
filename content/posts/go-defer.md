---
title: "Defer is complicated"
date: 2018-12-04T13:01:50
lastmod: 2018-12-04T13:01:50
summary: "The `defer` keyword in Go does much more than you might think, leading to performance issues in some cases. Why is this?"
---
This is a simple usage of the `defer` statement in Go:

```go
func foo() error {
    f, err := os.Open("somefile.txt")
    if err != nil {
        return err
    }
    defer f.Close()

    // do something with the file

    return nil // operation was successful
}
```

As a programmer, you may naively expect this code to be transformed into the following simpler code:

```go
func foo() error {
    f, err := os.Open("somefile.txt")
    if err != nil {
        return err
    }

    // do something with the file

    f.Close()
    return nil // operation was successful
}
```

Well, not quite. This is what [the specification](https://golang.org/ref/spec#Defer_statements) has to say on the matter (emphasis mine):

> A "defer" statement invokes a function whose execution is deferred to the moment the surrounding function returns, either because the surrounding function executed a [return statement](https://golang.org/ref/spec#Return_statements), reached the end of its [function body](https://golang.org/ref/spec#Function_declarations), or because the corresponding goroutine is [panicking](https://golang.org/ref/spec#Handling_panics).

The first two constraints are relatively easy to satisfy and are fairly obvious. Most functions can indeed have the above transformation applied, as long as they don't defer anything in a loop. The third constraint is much harder to satisfy, because it involves a non-local goto. Essentially, it means the function must be transformed roughly the following way by the compiler:

```go
func foo() error {
    f, err := os.Open("somefile.txt")
    if err != nil {
        return err
    }
    runtime.deferFunction(stackPointer, foo, os.File.Close, []value{f})

    // do something with the file

    runtime.runDefers()
    return nil // operation was successful

recover:
    runtime.runDefers()
    return nil
}

// runtime functions that do magic:
func deferFunction(stackPointer uintptr, parent, deferred func (), args []value)
func runDefers()
```

Note: while a panic in good Go code is uncommon, many operations like slice indexing or pointer dereferences may potentially cause a panic. This means almost all functions may panic and the compiler doesn't know which functions don't.

With this transformation, the runtime can call deferred functions on panic while walking the stack to where the goroutine was created. Whenever a deferred function calls `recover()`, the panicking sequence is stopped and the runtime jumps to the `recover:` label to continue execution from there. All in all, `defer` is a [slow](https://github.com/golang/go/issues/14939) and complicated beast although it looks so deceptively simple.

To be clear, I really like this feature of the Go language. It means that it is much easier to free resources on error conditions without missing edge cases and without [using goto for error handling](https://eli.thegreenplace.net/2009/04/27/using-goto-for-error-handling-in-c). But it isn't as simple as it may look.
