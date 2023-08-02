---
title: "What RGB and sRGB mean"
date: 2019-12-29T16:42:06
lastmod: 2019-12-29T16:42:06
summary: "What RGB really means, what sRGB and gamma are and how to correctly blend colors."
---
Say you have a gray color, something like `rgb(127, 127, 127)`. What's the amount of light that comes out of that pixel, relative to white pixels? You might be thinking it is 50% - after all, it's halfway between 0 and 255 and it _looks_ halfway there. But it isn't. The light output of an average monitor would be more like 18% relative to a fully white pixel.

Why is this? It's mostly for historic reasons  (CRT monitors) but nowadays the reason is the "looks" part (and compatibility, of course). Whenever a pixel is captured in some way (cameras, scanners, etc.) it is often captured with a higher dynamic range than 8 bits can provide. However, eyes are very much nonlinear and are much better seeing differences in darker colors than they are in lighter colors, so these colors are effectively put in a lossy compression algorithm called sRGB. Whenever a color is displayed on a screen or printed, it is again decompressed with hopefully the same algorithm to get a close approximation of the original color back - and you probably can't tell the difference.

So basically whenever you talk about RGB that could mean two very different things:

  * **sRGB**: used almost everywhere. Almost all image formats use this format such as JPEG, PNG, GIF, HTML colors, you name it. It is a format optimized for the human eye: if you make a linear gradient from `rgb(0, 0, 0)` to `rgb(255, 255, 255)` the color seems to be increasing roughly monotonically.
  * **Linear**: the colors that are actually being displayed on the screen. `rgb(127, 127, 127)` really means 50% brightness, even though it _looks_ like about 73% brightness. Apart from being the input to cameras and the output from displays, this format is also used in computer graphics that need realistic lighting (such as raytracing) and whenever you work directly with display-like hardware such as [RGB LEDs](https://hackaday.com/2019/03/26/can-you-live-without-the-ws2812/).

You can convert between the two formats, but keep in mind that sRGB is a lossy compression. The real formula is more difficult, but a close approximation uses the "gamma" number which is an exponent (sRGB has a gamma of roughly 2.2). So if you want to know the linear value for `rgb(127, 127, 127)`, that's `Math.pow(127/255, 2.2)` is about 21.6%. And back again: `Math.pow(0.216, 1/2.2)*255` equals about `rgb(127, 127, 127)`. For non-gray colors, simply apply this formula to each component individually.

In practice, it seems like you could just stop thinking about this, live blissfully in a sRGB world thinking everything is linear. Unfortunately, you'll hit this whenever you try to work with colors in some way, such as blending colors (transparency!) or doing a linear interpolation between colors (gradients!). Take a look at the following picture:

<img src="/assets/red-blue-srgb.svg"/>

Here you can see two bright colors on either side: red and blue. In the middle, you can see the purple blend of the two. The top color is correctly blended. It is about as bright as the red and blue on either side. However, the bottom is not: it is clearly darker than any other color in the picture. Here are the RGB values of all the colors in the image:

| color | sRGB value | linear value | brightness |
| --- | --- | --- | --- |
| red | `rgb(255, 0, 0)` | `rgb(1, 0, 0)` | 1 |
| blue | `rgb(0, 0, 255)` | `rgb(0, 0, 1)` | 1 |
| correct purple | `rgb(186, 0, 186)` | `rgb(0.5, 0, 0.5)` | 1 |
| dark purple | `rgb(127, 0, 127)` | `rgb(0.22, 0, 0.22)` | 0.44 |

If we ignore for a bit that eyes are not equally sensitive to every color, you can see that the total light output of the correct purple (0.5+0.5=1) is the same as that of red and blue (1), and therefore it looks about as bright. On the other hand, the incorrectly mixed dark purple only has a light output of 0.22+0.22=0.44, which is less than half that of the bright color on either side.

If you want to do correct blending between two colors, here is what you'll need to do:

 1. Decode both colors from sRGB to linear. Linear colors are often stored in a set of floating point numbers but you could also use 32-bit integers if that is faster on some hardware (think embedded devices without FPU).
 2. Blend the two colors together in whatever way you like, as you would otherwise do naively.
 3. Encode the resulting color again into sRGB.

It's worth noting that the alpha channel is not part of this conversion: it represents the position in a linear gradient between two colors (the background and the color to be blended) and not a color component itself. Therefore, sRGB conversion rules don't apply to it.

The sad ending of this story is that while game engines by necessity work in linear colors to get accurate lighting, the vast majority of software that deals with images (including Photoshop and all popular web browsers!) get it wrong. Because even scaling, zooming, and antialiasing need to take care of gamma to produce good-looking results. But now that you know about gamma, _please_ make sure you won't fall in the same trap.

If you want to read more about this, please go read [this awesome post](https://blog.johnnovak.net/2016/09/21/what-every-coder-should-know-about-gamma/). It should include everything you need to know about colors and how to work with them in computer graphics.
