---
title: "Interfaces in TinyGo"
date: 2018-12-08
lastmod: 2018-12-08
summary: "How TinyGo implements Go interfaces in a radically different way, avoiding most memory allocations and reducing code size."
---
Interfaces in Go are very useful in the way they make it easy to decouple code. It might even be my favorite feature, perhaps only behind goroutines+channels. Unfortunately, as you might imagine their implementation isn't very straightforward. In this post, I'll briefly explain how interfaces are implemented in the main Go compilers and what TinyGo does differently to reduce code size.

Interfaces in Go have the following operations:

* Create an interface ([`*ssa.MakeInterface`](https://godoc.org/golang.org/x/tools/go/ssa#MakeInterface)). This happens for example whenever you assign a variable of a concrete type to a variable of an interface type, or pass a variable of a concrete type to a function expecting an interface type.
* Change an interface ([`*ssa.ChangeInterface`](https://godoc.org/golang.org/x/tools/go/ssa#ChangeInterface)). Similar to creating an interface, but when assigning an existing interface value to a variable of type interface but with the same or less methods, known to be assignable at compile time.
* Type assert ([`*ssa.TypeAssert`](https://godoc.org/golang.org/x/tools/go/ssa#TypeAssert)) with a concrete type. This converts an interface value into the value of the concrete type. It may fail at runtime when this interface value does not contain a value of this concrete type. It fails by either returning a second "comma-ok" return value, or by panicking if there is no second return value.
* Type assert ([`*ssa.TypeAssert`](https://godoc.org/golang.org/x/tools/go/ssa#TypeAssert)) with an interface type. This tests whether a more generic type implements a more concrete type, for example whether a `io.Writer` implements an `io.WriteCloser`, meaning whether the underlying type also has a method with signature `Close() error`. Like a type asserts with a concrete type, this may either return a second "comma-ok" value or panic if there is no such return value.
* Interface call ([`*ssa.CallCommon`](https://godoc.org/golang.org/x/tools/go/ssa#CallCommon) with `IsInvoke()` returning true). An interface call looks up the right method to call from the interface and calls it, passing the underlying value and the list of methods as parameters. An interface call must be carefully optimized to not introduce too much overhead.

You may be missing one entry here in this list: type switches. It turns out that type switches are a front end trick and are implemented as an if/else chain using type asserts, at least in the libraries TinyGo uses. But this is no problem, as you'll see later in this post.

I'm not going to give complete details of how interfaces are implemented in the main Go compiler (`gc`). Russ Cox has already written a [great blog post](https://research.swtch.com/interfaces) about that. To summarize the `gc` implementation:

* An interface value is a two-word type. The first word contains an "itable" or "itab" which is a pointer to the underlying type descriptor and a list of function pointers. The second word either contains the value itself if the underlying value is a pointer and a pointer to the value otherwise.
* Type asserts with an interface type check whether the underlying type in the interface value contains all methods of the interface. If it does, an itable is generated dynamically.
* Interface calls simply look up the function pointer in the list of interfaces and call it. Because these function pointers are sorted by signature, the offset from the start of the itable is known statically and thus only needs two loads to look up: one to load the pointer of the itable and one to load the function pointer from the itable.
* Changing an interface without type assert is easy, because it can simply create a new itable that contains only the function pointers necessary for the new (more generic) interface.

While such an implementation is relatively easy to implement (especially with separate compilation), it has a few problems that make it less suitable for embedded devices. It needs to allocate memory on seemingly innocent operations, function pointer calls have a certain overhead because LLVM can't optimize them, and more type info of each type needs to be retained, including all methods of a type that is ever put in an interface.

For TinyGo, I thought about a different implementation that tries to avoid these issues as much as possible. The solution I came up with avoids most implicit memory allocations, does not retain methods that are never called in an interface call, does not need an itable, and may even result in interfaces being a zero-cost abstraction in the ideal case. Interface values are still two words:

```go
type _interface struct {
	typecode uintptr
	value    *uint8
}
```

What you see here is that instead of a pointer to an itable, only a typecode is used which is a small number unique to the type of the underlying value. The interface value is implemented roughly the same way as in the main Go compiler. The only difference is that in the main Go compiler, the underlying value is stored directly in this pointer when the underlying value is also a pointer. In TinyGo, however, the underlying value is always encoded into the pointer itself when it fits.

By using a small constant number for the typecode, a type assert to a concrete type can be implemented with a simple comparison against a constant which can often be lowered to a single compare and branch instruction. Perhaps more importantly, a type switch is replaced with a long list of such comparisons which LLVM recognizes and transforms into a switch statement. This switch statement is then [lowered into very efficient machine code](https://www.youtube.com/watch?v=gMqSinyL8uk).

Method calls on interfaces (internally called "invoke" instead of "call") are lowered depending on how many types used in interfaces implement this interface. For example, the following interface call:

```go
func foo(w io.Writer) {
    w.Write([]byte("foo"))
}
```

Could be translated into a direct call:

```go
func foo(w io.Writer) {
    bytes.Buffer.Write(w.value, []byte("foo"))
}
```

Or a type switch with the following pseudocode:

```go
func foo(w io.Writer) {
    io.Writer.Write(w.value, []byte("foo"), w.typecode)
}

func io.Writer.Write(value *uint8, buf []byte, typecode uintptr) (int, error) {
    switch typecode {
    case <typecode for *os.File>:
        return os.File.Write(value, buf)
    case <typecode for *bytes.Buffer>:
        return bytes.Buffer.Write(value, buf)
    default:
        // mark unreachable in LLVM
    }
}
```

If there is no concrete type implementing this interface, that particular code is marked unreachable so that LLVM can optimize accordingly.

A type assert that asserts on an interface type works very similarly. It is lowered differently depending on the number of concrete types used in an interface value that implement the asserted interface. When there are no concrete types, it is lowered to a constant false or a panic. When there is one, it is transformed into a simple comparison. And when there is more than one, a separate function is used that effectively implements a new type switch on all of those concrete types.

The only thing I haven't described yet is what happens when an interface value of a more specific type is assigned to a more generic interface. For example, what happens when you assign an `io.Writer` to an `interface{}`. You may have already figured this out, but as there is no itable to carry around it is a no-op. This might be a small optimization in itself but I doubt it has much of an impact compared to the rest.

Of course there are a few downsides to this approach:

* This implementation requires to see the full program. This is no big deal at the moment in TinyGo because it compiles the whole program as one LLVM compilation unit. In the future with true separate compilation, it will still depend on some sort of LTO and cannot generate one binary per package, for example.
* This implementation may be slower in some cases, and may cause code bloat in very few cases. I haven't tested this but I think that the ability for LLVM to optimize across interface calls makes up for the potential slowness and I am fairly certain that the potential added code bloat won't be more than what is gained by the additional dead code elimination except perhaps for some edge cases.
* Reflection will make the typecode system more difficult. I have some ideas of how to implement reflection, but haven't thought them out completely. This will likely be the subject of another post.

All in all, I'm happy with this implementation and even though it is not perfect yet, it results in very small code.
