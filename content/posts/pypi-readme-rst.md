---
title: "Uploading README.rst to PyPI"
date: 2017-07-23
lastmod: 2017-07-23
summary: "My experience with making a Python package and uploading it to PyPI. Sometimes, such systems aren't as sophisticated as one might expect."
---
TL;DR: if you just want to add a `README.rst` file to a PyPI package, do something like this:

```python
from distutils.core import setup
import os

ROOT = os.path.abspath(os.path.dirname(__file__))

setup(
      [....snip...]
      long_description=open(ROOT + '/README.rst').read(),
      [...snip...]
     )
```

---

Every package should have a README, right? Right. So it should be easy to add a README to a package. I'm now talking about publishing a package to [PyPI](https://pypi.python.org/pypi), the Python package index (sort-of like npm for [Node.js](https://nodejs.org/) and [crates.io](https://crates.io/) for [Rust](https://www.rust-lang.org/en-US/)). This was written after I published my [zipseeker](https://pypi.python.org/pypi/zipseeker) package to PyPI. And it's a bit of a rant.

Every PyPI package includes a setup.py file, containing some metadata. Something like this:

```python
from distutils.core import setup
import os

VERSION='1.0.10'

setup(name='zipseeker',
      packages=['zipseeker'],
      version=VERSION,
      description='Create a streamable and (somewhat) seekable .ZIP file',
      author='Ayke van Laethem',
      url='https://github.com/aykevl/python-zipseeker',
      keywords=['zip', 'http', 'streaming'],
     )
```

So I published the package, but unfortunately the README was left out. Of course, the Python people prefer reStructuredText while I prefer [Markdown](https://daringfireball.net/projects/markdown/syntax). I even write this blog post in [Markdown](https://github.com/russross/blackfriday), as it is easy to convert to HTML and I prefer a text-based format to a WYSIWYG editor anyway. But enough about Markdown.

So they want [reStructuredText](https://docs.python.org/devguide/documenting.html). Fine. I'll [convert](https://github.com/aykevl/python-zipseeker/commit/e170dca3b3217659368af87113a293c6f063c99c) my easy-to-write Markdown file to that somewhat strange format. But then again, I'm not very used to reST it so maybe it's just a matter of experience. And as distutils apparently doesn't include the README.rst file automatically I'll add `include *.rst` to the [MANIFEST.in](https://packaging.python.org/tutorials/distributing-packages/#manifest-in) file. And publish again (with a new version number of course, they don't accept the same number again).

Still this doesn't work. Of course. Apparently it's not enough to include the file, you have to actually *read it's contents* and put it in a `long_description` parameter. And here is where the fun starts.

First, I tried just adding the most obvious `long_description` parameter, with the hope it would work well. Something [like this](https://github.com/aykevl/python-zipseeker/commit/2390b1f6786cf1c8c18544510171710dd66409d6):

```python
       description='Create a streamable and (somewhat) seekable .ZIP file',
￼       long_description=open('README.rst').read(),
￼       author='Ayke van Laethem',
```

Uploading works fine (the `open` call succeeds) but installing using `pip` doesn't work: `setup.py` is run with a different working directory so the file README.rst can't be found. We have to find where the `setup.py` file is located so we can actually open using the right path.

The [solution](https://github.com/aykevl/python-zipseeker/commit/6f785538a5e05610b4aade8ad69bcebda613316e) I came up with is:

```python
ROOT = os.path.dirname(__file__)
if not ROOT:
    ROOT = '.'

setup(
      [...snip...]
      long_description=open(ROOT + '/README.rst').read(),
      [...snip...]
     )
```

Finally, this works!

The [sample project](https://github.com/pypa/sampleproject) uses a slightly different system, which I eventually [adopted](https://github.com/aykevl/python-zipseeker/commit/7374c14466cc5d88db45aaeb11e0cfaae7dcd956):

```python
here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    [...snip...]
    long_description=long_description,
    [...snip...]
)
```

Of course, I could have found this if I had looked for the sample project. It's linked right there in the [official documentation](https://packaging.python.org/tutorials/distributing-packages/#readme-rst). But I used a [different tutorial](http://python-guide-pt-br.readthedocs.io/en/latest/writing/structure/) which didn't make such things clear. And really, if all Python files are included automagically (of course) why not just assume default locations for standard files like a README.rst or a `LICENSE.txt`? \</rant>
