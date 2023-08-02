---
title: ":link and :visited are mutually exclusive"
date: 2014-12-13T00:54:34
lastmod: 2014-12-13T01:01:38
summary: "I discovered that the CSS pseudo-classes `:link` and `:visited` are mutually exclusive. This in contrast to what may seem more logical, that is, that `:link` applies to all links."
---
One thing that bit me once while writing some CSS, was the `:link` pseudo-class. Apparently, it is applied to all links *that have not yet been visited*. This is in contrast to what, for example, the MDN docs say and what I had assumed based on the name (I would assume that `:link` refers to all links, not just the not-yet-visited ones).

The [CSS specification](http://www.w3.org/TR/selectors/#link) clearly states what `:link` means:

> User agents commonly display unvisited links differently from previously visited ones. Selectors provides the pseudo-classes `:link` and `:visited` to distinguish them:
>
>  *  The `:link` pseudo-class applies to links that have not yet been visited.
>  *  The `:visited` pseudo-class applies once the link has been visited by the user.
>
> After some amount of time, user agents may choose to return a visited link to the (unvisited) ‘`:link`’ state.
>
> *The two states are mutually exclusive.*

(emphasis mine)

The usually-correct [MDN docs](https://developer.mozilla.org/en-US/docs/Web/CSS/:link) say something quite different:

> The `:link` CSS pseudo-class lets you select links inside elements. This will select any link, even those already styled using selector with other link-related pseudo-classes like `:hover`, `:active` or `:visited`. In order to style only non-visited links, you need to put the `:link` rule before the other ones, as defined by the LVHA-order: `:link` — `:visited` — `:hover` — `:active`. The `:focus` pseudo-class is usually placed right before or right after `:hover`, depending of the expected effect.

Luckily, [webplatform.org](https://docs.webplatform.org/wiki/css/selectors/pseudo-classes/:link) is right. It almost literally copies the description from the CSS specification as quoted above.
