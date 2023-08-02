---
title: "South: stateless authenticated sessions for HTTP in Go"
date: 2015-01-28T22:09:13
lastmod: 2015-06-17T15:21:03
summary: "I have written a Go package for stateless authentication using HMAC. I believe this system is in practice just as secure as session IDs without having to store state on the server, making authentication a whole lot easier."
---
Usually, when you want to provide HTTP sessions, you just use your framework's way of managing sessions. Simple and secure, as it should be. Recently I was working on a web application written in [Go](http://golang.org/) (this blog!) that doesn't use any framework. And as I didn't want a database to manage sessions (it felt too  heavy to me), I went looking for other solutions. Unfortunately, there weren't any so I did it myself, trying to copy others as much as possible as, of course, [I suck at cryptography](http://www.happybearsoftware.com/you-are-dangerously-bad-at-cryptography.html).

After first cooking up my own method (involving public key cryptography which did far more than it needed), I developed a simple system based on a HMAC. It is documented on [security.stackexchange.com](http://security.stackexchange.com/questions/30707/demystifying-web-authentication-stateless-session-cookies) but was originally introduced in an [old paper from 2001](http://cookies.lcs.mit.edu/pubs/webauth:tr.pdf). The system creates a message with the user ID and the expiry date and signs that message using a HMAC to create an authentication token. The pipe character (`|`)  indicates a field separator:

    data|expiry_date|HMAC(data|expiry_data, key)

This token can be verified by calculating `HMAC(data,expiry_data, key)` again for each request and comparing that to the HMAC in the token. If they match, this token was actually created with the specified key.

I use a slightly different system. Instead of the expiry date, I only save the creation date. How long a token will be valid is a setting of the application. Calculating the expiry date is as simple as adding the session duration to the creation date.

    user_id|creation_date|HMAC(user_id|creation_date, key)

Using the creation date instead of the expiry date has a few benefits:

  * When the session duration is changed on the server, this new duration will be automatically applied to all tokens. Shortening this duration will let all old tokens expire with the new session duration. Making the session duration longer will not normally increase the session duration for older tokens, though, as old cookies will be removed by well-behaved browsers.
  * More importantly, old tokens can be expired relatively easy. For example, after a possible security breach where the secret key wasn't affected, the server can invalidate all tokens created before the breach simply by checking their creation date. And when a user changes their password, that date can be stored with the user and the server can invalidate tokens for that user created before the password change. This way, most cases of token revocations can be easily implemented even though the server saves no session state.

Many people believe storing session tokens on the client without keeping track of those sessions on the server side may be insecure. I believe that there is no real reason for that. Either the attack is merely theoretical, or there is a practical defense.

  * *Users might be able to forge their own tokens.*  
I believe `HMAC-SHA256` (the current MAC) is very secure, at least for the time being. If it turns out it isn't, it can easily be swapped for another message authentication token without fundamentally altering the system.
  * *Authentication tokens cannot be revocated.*  
As described above, it is actually quite easy to revoke old authentication tokens when the token creation time is stored inside the token. This can be done for the whole system, for one user, or even for user groups if your system needs that. And if all else fails, you can simply generate a new key invalidating all current sessions.  
Additionally, are session-ID-based systems really that better in this regard? Have you ever actually manually expired HTTP sessions, for example in PHP?
  * *Users can tamper with the cookie.*  
Once a user tampers with the cookie, the MAC will not validate anymore.
  * *The contents of the cookie is not encrypted*  
There is no secret in the cookie. The cookie must be *authenticated*, not *encrypted*. These two are commonly confused by people new to cryptography.

There are a few issues with this protocol described in a paper called "[A secure cookie protocol](http://www.cse.msu.edu/~alexliu/publications/Cookie/cookie.pdf)", but I think they're not very relevant. Problem 1 (cookie confidentiality) is not an issue, as we're only storing the user ID and no additional (confidential) data. Problem 2 (replay attacks) is a problem with SSL and not with this protocol. Normal session IDs can be stolen just as easily (or hard) as authentication tokens. And cookies are *designed* to be replayed. Problem 3 (volume attack), finally, is something I think we don't really have to worry about until SHA256 starts to look insecure. In that case, we can just swap the cryptographic primitive and we're good to go.

I wrote a package for this protocol in Go, wich you can `go get` from [github.com/aykevl/south](https://github.com/aykevl/south). It's liberally licensed under a BSD-style license so it can be used freely. I hope it integrates well into other projects: user IDs are simple strings with a few limitations (e-mail addresses are usually fine) and tokens in and out of the package are transferred using [`http.Cookie`](http://golang.org/pkg/net/http/#Cookie).

Oh, and the obligatory disclaimer: use the package (and this blog post) at your own risk, I'm not responsible for any security issues I've overlooked. Instead, let me know about them so I can fix them :)
