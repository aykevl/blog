---
title: "Safely Embedding JSON in JavaScript"
date: 2015-07-10
lastmod: 2015-07-10
summary: "How do you embed JSON in JavaScript? The naive approach turns out to have a XSS and DoS vulnerability, but this is easily fixed with a simple filter."
---
One commonly cited advantage of JSON is that it is a subset of JavaScript and thus you can insert it easily in a `<script>` tag. Unfortunately, that's not completely true and even opens the door for [XSS](https://www.owasp.org/index.php/Cross-site_Scripting_(XSS) attacks, as I discovered recently. But with a little escaping you can safely embed JSON in `<script>` tags.

This is what the [official json.org web page](http://www.json.org/fatfree.html) says:

> JSON has become the X in Ajax. It is now the preferred data format for Ajax applications. There are a number of ways in which JSON can be used in Ajax applications. The first is to include JSON text in the original HTML.
> 
> ```markup
> <html>...
> <script>
> var data = JSONdata;
> </script>...
> </html>
> ```
> 
> This is useful in cases where the JSON text is significantly smaller than its HTML representation. By completing the HTML generation in JavaScript, the page can be delivered more quickly.

But consider this example:

```markup
<script>
var data = {"message": "</script><script>alert('XSS');"};
</script>
```

This does exactly what it says. Which is certainly not what you want.

So when you control all the JSON data, this is safe, but it's not when any part of it can be modified by a user of your web application. And are you sure nobody but you will ever be able to influence that data? Better be safe than sorry, so escape everything. It's easy and painless (just escape `<`, `>` and `&`), but read on for some more issues and a proper fix.

There is a second problem: JSON is *not* a true subset of JavaScript, unlike what [json.org](http://www.json.org/fatfree.html) claims (emphasis mine):

> JSON (or JavaScript Object Notation) is a programming language model data interchange format. It is minimal, textual, and **a subset of JavaScript**. Specifically, it is a subset of ECMA-262 (The ECMAScript programming Language Standard, Third Edition, December 1999). It is lightweight and very easy to parse.

JSON allows the Unicode code points `U+2028` and `U+2029` in strings, while JavaScript doesn't. Why is this? Well, [Douglas Crockford missed that part of the JavaScript specification](https://www.youtube.com/watch?v=hQVTIJBZook&t=59m07s) (oops!). And what does this difference mean? Well, it's possible to craft strings (like `{"JSON":"ro cks!"}`) that are valid JSON but not valid JavaScript. Try executing `({"JSON":"ro cks!"})` in a shell and see what happens:

<img src="/assets/json-javascript-syntaxerror.png" width="489" height="97"/>

There is a small character between the 'o' and the 'c' which usually isn't visible but will result in a syntax error.

This may not seem like a big issue, but this means that if there is any user-submitted text in the JSON, they can cause a kind of [DOS](https://www.owasp.org/index.php/Denial_of_Service). Imagine what happens if the JSON is part of the main page, and some critical JavaScript follows it degrading the usability of the website.

So, in addition to `<`, `>` and `&`, there are `U+2028` and `U+2029` which need escaping. Luckily, escaping is very simple: the only place these characters can appear is in strings. And any character in a string can be escaped to it's Unicode code point.

Character | Replacement
----------- | ----------
`<` | `\u003c`
`>` | `\u003e`
`&` | `\u0026`
`U+2028` | `\u2028`
`U+2029` | `\u2029`

The result is completely valid JSON, so you really should do this 'by default' on all your JSON output that might ever be used inside a `<script>` tag. The resulting JSON is slightly longer, but safe.

```markup
<script>
var data = {"message": "\u003c/script\u0026\u003cscript\u0026alert('XSS');"};
</script>
```

Credits:

  * [The timeless repository: JSON: The JavaScript subset that isn't](http://timelessrepo.com/json-isnt-a-javascript-subset)  
    My starting point.
  * [golang.org: encoding/json package](http://golang.org/pkg/encoding/json/#HTMLEscape)  
    My source of the replacement characters.
