---
title: "Fix 'jumping scrollbar' issue using only CSS"
date: 2014-09-08
lastmod: 2015-01-23
summary: "I discovered a technique to prevent page jumping when navigating between short and long pages without showing the scroll bar all the time."
---
When centering a page with CSS like `margin: 0 auto;`, there's a small gotcha: the page will 'jump' a little on certain browsers when navigating between short and long pages. This is because the scrollbar gets hidden with short pages and is shown again with longer pages, which makes the page move a little horizontally.

The [classic fix](http://css-tricks.com/eliminate-jumps-in-horizontal-centering-by-forcing-a-scroll-bar/) for this is the following css:

``` css
html {
	overflow-y: scroll;
}
```

This makes the scrollbar always appear on the page, no matter whether it's required or not. When the scrollbar is not needed, the scrollbar will be grayed out but will stay the same width. The page doesn't jump, and usability is preserved.

This is all nice, but what if we could have the cake and eat it too? In other words, what if we were able to only show the scrollbar when it's needed, and not have this jumping effect?

I found a solution using `100vw`. `100vw` is the viewport width (including the scrollbar, and `100%` width (measured on the `<html>` element) is the width of the viewport excluding the scrollbar. Using a little CSS <code>[calc](https://developer.mozilla.org/en-US/docs/Web/CSS/calc)()</code> trickery, we can give the page an (invisible) margin on the left that is exactly as wide as the scrollbar and disappears when the scrollbar disappears. That way, the margin on the right (the scrollbar) and on the left (created by us) is always the same.

```css
html {
	margin-left: calc(100vw - 100%);
	margin-right: 0;
}
```

**Note**: calculating the scrollbar width this way [only works](http://lists.w3.org/Archives/Public/www-style/2013Jan/0616.html) when the `<html>` element has `overflow: auto;`.

There's one small issue: when using [responsive web design](http://en.wikipedia.org/wiki/Responsive_web_design) (which you should!), it gets quite obvious that the margin at the left is bigger than at the right when the page is made smaller. This won't be an issue on mobile because scrollbars aren't normally shown there, but it just looks ugly on a desktop browser when the browser is resized. This can be fixed by only enabling this feature on wider viewports:

```css
@media screen and (min-width: 960px) {
	html {
		margin-left: calc(100vw - 100%);
		margin-right: 0;
	}
}
```

The `960px` is arbitrary: just use something that's somewhat bigger than your webpage (about `150px` will do).

This trick works in most new browsers, and it degrades gracefully in older browsers (the page will just keep on jumping). Older browsers won't understand the rule so they'll just skip it.

Supporting browsers include IE9+, Chrome and Firefox, but unfortunately Opera (Classic) and Safari 7 don't support it. I think Safari doesn't work due to a WebKit bug in handling `calc()` combined with the new viewport units (`vw`, `vh`, `vmin` and `vmax`). I don't know about Opera Classic, but newer Opera versions based on the Chromium source code should work as this trick works just fine in Chrome.

---

This is my first post on this blog. I hope it will be useful for someone. At the same time, this post is a proof-of-concept that the blog actually works, as I wrote the blogging engine myself.

---

## Update

Ater being picked up by [CSS-Tricks](http://css-tricks.com/), I burned through about 1GB of bandwidth. As the biggest part of the page is the ±60kb icon in the top (HTML and CSS is just a few kb each), I guess that are about 15000 unique visitors (!). I'm new to blogging, and suddenly having so many pageviews is… very surprising.

Anyway, I got a few replies to this post. I discovered them as external links in Google Webmaster Tools. I did not have an "[about me](/about)" page back then and I still haven't got [pingbacks](http://en.wikipedia.org/wiki/Pingback) or statistics of any form implemented, so GWT is the only way I can find out about links to my site.

First of all, 
[Mark Senff](http://www.marksenff.com/front-end/even-more-elegant-fix-jumping-scrollbar-issue/) investigated it and provided an alternative solution:

```css
html {
    width:100vw;
    overflow-x:hidden;
}
```

This has the side-effects that it will hide the right part of the page as the scrollbar hides that part, and it will disable horizontal scrolling. So I personally would not use it.

My scrollbar trick is only intended for *centered content*, something that may not have been clear. The example he gives includes a header that takes up the full width of the browser screen and that is mostly left-aligned. Of course, such a header wouldn't jump a lot. The text beneath, in comparison, would be well suited for it, and I found out the trick can be applied to a part of the page just fine. I've put an ugly example of that up at [Codepen.io](http://codepen.io/anon/pen/NPgbKP).

Some other mentions on the web include:

  * [Edwin Smith](http://smithy.co/who-we-are/) mentioned it on his blog on [Smithy.com](http://smithy.co/2014/12/fix-jumping-scrollbar-when-switching-pages/).
  * [Gavin Elster](http://codepen.io/elstgav/) made a live (and good-looking) example on [Codepen.io](http://codepen.io/elstgav/details/myEJNv). I forked that one to give the example above, but my version is very ugly in comparison :)

Thank you all!
