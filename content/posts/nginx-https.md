---
title: "Setting up HTTPS on nginx from start to finish"
date: 2015-05-19
lastmod: 2015-05-22
summary: "Turn a plain HTTP web site served with nginx into one with HTTPS and SPDY support. Includes StartSSL, Postfix and OCSP stapling."
---
I recently switched from a hosting provider ([NearlyFreeSpeech.NET](/2015/01/nfsn), which I still recommend) to a VPS, for much more flexibility, and for some other benefits. As I was running a VPS anyway and NFSN isn't particularly fast (I'm obsessed with speed), I switched this website over to the VPS and in the process also set up HTTPS (TLS). This post documents how I set up TLS in nginx for future reference.

I used [StartSSL](https://www.startssl.com/) as certificate authority, Postfix as mail daemon and nginx as web server. StartSSL is (as far as I know) the only provider of free SSL certificates, at the cost of having to pay if you ever want to revoke the certificate. Postfix is widely used so I went with that. Nginx is just a very fast web server that support [SPDY](http://en.wikipedia.org/wiki/SPDY), which improves performance (again, I'm obsessed with speed). The system (VPS) I am installing this all on is Debian Jessie, but it should also be usable on other Linux (and *BSD?) systems.

## Prerequisites

 * Time, the whole process takes a while.
 * A server (or VPS), preferably with Debian (Jessie for this tutorial).
 * A domain name
 * A working website on that domain, served by nginx.
 * A dedicated IP for this website if you want to be compatible with Internet Explorer on Windows XP and Android <= 2.3. Newer clients all support SNI, which is like virtual hosting but for TLS.

I will use `example.com` as your domain name and `you` as your username or first name throughout the tutorial.

Note: I have not added the relevant IPv6 settings in the configuration examples. But if your server has IPv6 (it should!), then it is a matter of adding an extra `listen` line with the same values. For example:

    listen 443 ssl;
    listen [::]:443 ssl;

## Postfix

You need to be able to receive mail on postmaster@example.com, hostmaster@example.com or webmaster@example.com. That's how StartSSL verifies you really own the domain. So we use Postfix to simply send those messages to another mailadres you own.

If you haven't already, set up a `MX` record on your domain with the value `10 @`, meaning all mail will be send to the bare domain. At least that's how it works at [transip.nl](https://www.transip.nl/). If you had to change it, you probably need to wait a while (up to 24 hour) before the change becomes effective and you can receive mail on your domain.

When you're at it, also set up [SPF](http://tools.ietf.org/html/rfc7208) if you haven't already. If you don't plan on setting up a full-featured mail server (that actually sends mail from your domain) you can simply add a TXT record with `v=spf1 -all`. This is a sign that no one will send mail from this domain so that if a spammer once sends a mail from your domain (someone@example.com), the mail server knows it is fake, to prevent spam.

Install Postfix:

    $ sudo apt-get install postfix

Choose "Internet Site" as option during installation and enter your fully-qualified domain name when asked for it.

Once installed, you need to configure `/etc/postfix/main.cf`. I choose to use the same bare domain (example.com) for the mail server:

  * Set `myhostname` and `mydomain` to the bare domain name.
  * Remove that domain from `mydestination`.
  * Add the lines (changing example.com, obviously):
    
        virtual_alias_domains = example.com
        virtual_alias_maps = hash:/etc/postfix/virtual

Now configure `/etc/postfix/virtual`. Here you can alias the postmaster/hostmaster/webmaster mailadresses, like:

```
postmaster@example.com you@gmail.com
hostmaster@example.com you@gmail.com
webmaster@example.com  you@gmail.com
you@example.com        you@gmail.com
```

Now run `postmap /etc/postfix/virtual` and restart postfix and you should be able to send mail to your domain and receive it at your primary mailadres (such as Gmail)! Don't use the same Gmail address to test it, you won't receive it. Gmail filter duplicates. Instead, use another mail address (even another Gmail address will do) to send a test message to one of those new mail addresses (like postmaster@example.com) to test your configuration.

## Create a Certificate Signing Request

This will actually create your TLS private key! While you can let StartSSL generate one for you, it is more secure to generate one yourself:

    $ openssl genrsa -out example.com.key 2048

This creates a 2048 bits key, which is recommended today. 1024 bits is seen as weak and it looks like you can't even use them with StartSSL. 4096 bits is stronger, but is seen as unnecessary for the coming years (in any case, 2048 bits is strong enough as long as the StartSSL key is valid, which is one year).

**NEVER** share this key, and store it at a secure location! This key is what protects your domain. Anyone with the key will be able to perform a MITM attack.

To actually let OpenSSL sign the key, you have to also generate a [Certificate Signing Request], which is basically a blob of text encoding the public key and some other information:

    $ openssl req -new -sha256 -key example.com.key -out example.com.csr

A SHA256 hash is used, as SHA1 is now considered weak by Google Chrome (it will display a warning if you use the SHA1 as signing algorithm). SHA256 should be secure for the foreseeable future.

OpenSSL will ask a few questions, but it doesn't really matter what you fill in there, as StartSSL will only look at the public key. Just to be sure, I filled in some details.

## Create a StartSSL account

The [startssl.com](https://www.startssl.com/) website looks like it was built at least 10 years ago and never changed since then. That doesn't make a good impression but hey, they're trusted by all major web browsers and operating systems. While logged in (or signing up), don't visit another part of the website as it may screw up the whole process.

Sign up via the "Sign-up" button in the top left of the page. Fill in all the details and a private key for authentication will be installed in your browser. This is not the SSL key, just a key you can use to authenticate yourself to StartSSL. Go to your browser settings and back up this key in a secure location!

## Verify your domain

Log in to StartSSL if you aren't already logged in and choose "Domain Name Validation" in the Validation Wizard. You will need to send an email to one of the addresses created while setting up Postfix. I choose postmaster@example.com, but it doesn't really matter which one you choose.

## Sign the domain key

Now it's time to actually sign your key! Go through the Certificate Wizard in the OpenSSL website, skip "Generate Private Key" (you already have one yourself, and letting a CA generate one is insecure), and copy-paste the CSR file you generated before. It is small enough that you can just `cat` the file and paste it there.

Continue, and StartSSL will sign your key. It will display a textbox with the textual blob containing the certificate. Save it as example.com.crt.

It will also link two files: the StartSSL root CA, and the Class 1 Intermediate Server CA. Save both files as startssl.ca.pem and startssl.class1.pem respectively. You will need these files to configure nginx.

## Install the certificate in nginx

There is a [tutorial](https://www.startssl.com/?app=42) on the StartSSL website, but it is not entirely secure and corrent, somewhat outdated, and not complete. I wouldn't recommend following it, though you can still read it if you want. Instead, the steps here are up-to-date at the time of publishing this post.

Copy the files startssl.ca.pem, startssl.class1.pem, example.com.key, and example.com.crt to `/etc/ssl/private`. Additionally, make sure the keys cannot be read from outside (the .pem and .crt files are public, only the .key files should be kept secure):

    $ sudo chmod 600 /etc/ssl/private/example.com.key

Now edit your site's nginx configuration, /etc/nginx/sites-available/example.com. Add or replace the relevant settings below. Note, this is an incomplete configuration, just showing the SSL/TLS related settings:

```
server {
    listen 443 ssl;

    ssl_certificate          /etc/ssl/private/example.com.crt;
    ssl_certificate_key      /etc/ssl/private/example.com.key;
    ssl_protocols            TLSv1 TLSv1.1 TLSv1.2;
}
```

The `ssl_protocols` is required as the [default](http://nginx.org/en/docs/http/ngx_http_ssl_module.html#ssl_protocols) includes the SSLv3 protocol which is [broken](http://arstechnica.com/security/2014/10/ssl-broken-again-in-poodle-attack/) and relatively easy exploited.

Restart nginx and test your configuration!

    $ sudo service nginx reload

Does it work? Good. Unfortunately, you have to take a few more steps for performance, security and privacy reasons (but mainly performance).

First of all, the client doesn't send the CA's intermediate certificate. For that, you have to combine the example.com.crt and startssl.class1.pem files, in that order, to create example.com.bundle.crt (just use cat for that), and update `ssl_certificate`:

```
    ssl_certificate          /etc/ssl/private/example.com.bundle.crt;
```

## OCSP stapling

[OCSP](http://en.wikipedia.org/wiki/Online_Certificate_Status_Protocol) is a protocol that lets TLS clients check whether a certificate is still valid. OCSP stapling means that the (signed) response from your CA is sent to the TLS client, so it can verify that the certificate is still valid. These responses are only valid for a short time, like one or two days, so the web server must update the OCSP response from the CA regularly and automatically.

Most web browsers don't verify the revocation status of certificates as that slows down web browsing, but you should include the OCSP response anyway.

In nginx, this is relatively easy (again, only showing the relevant settings):

```
    ssl_trusted_certificate  /etc/ssl/private/startssl.class1.bundle.pem;
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4; # Google Public DNS
    resolver_timeout 1s;      # Google is fast
```

The `ssl_trusted_certificate` is a file containing both `startssl.ca.pem` and `startssl.class1.bundle.pem`, in that order. They will be used to verify the signed OCSP response.

The resolver can be any DNS, but Google Public DNS is a fast one and has always worked well for me.

Restart nginx and test OCSP:

    $ openssl s_client -connect example.com:443 -status

In the (long) response, there should be a OCSP resonse. If it says:

    OCSP response: no response sent

Then you can just try again: nginx might not have cached it already (it looks like nginx gets the OCSP response on the first request).

## SPDY!

[SPDY](https://www.chromium.org/spdy/spdy-whitepaper) is a new protocol designed by Google, and is the basis of [HTTP/2](https://http2.github.io/).

Enabling SPDY is easy. Just modify the `listen` line (including spdy this time):

    listen 443 ssl spdy;

This will improve performance, especially on TLS and on heavy sites in general.

## Redirect from HTTP to HTTPS

Redirecting is also easy. This sends a permanent redirect for all requests from example.com and www.example.com to the HTTPS-enabled variants.

```
server {
    listen 80;

    server_name  example.com www.example.com;

    return 301 https://example.com$request_uri;
}
```

## Strengthen the cipher suite

When testing in Chrome, it says "Your connection to example.com is encrypted with obsolete cryptography". Somehow, the wrong cipher suite is selected, I think because OpenSSL puts a less modern cipher as the first cipher. This issue is remedied by adding a modern cipher suite as the first cipher in the list:

    ssl_ciphers              "ECDHE-RSA-AES128-GCM-SHA256:HIGH:!aNULL:!MD5";

This cipher suite is not compatible with IE6, but that shouldn't be an issue nowadays. Even IE7 and IE8 are supported.

## Protect yourself from the LogJam attack

The new [LogJam attack](http://arstechnica.com/security/2015/05/https-crippling-attack-threatens-tens-of-thousands-of-web-and-mail-servers/) can downgrade the security of a connection so it can be downgraded, but the computation required for that is only within the reach of certain entities (like the NSA). Nonetheless, it can be a good idea to improve the security. And it increases your ranking in the SSLLabs test.

    $ openssl dhparam -out dhparams.pem 2048

This will take quite some time (about one minute on a fast computer).

Move the prime to /etc/ssl/private and configure nginx (again in the `server` block of the configuration file):

    ssl_dhparam    /etc/ssl/private/dhparams.pem;

## Testing

It is recommended to test the TLS configuration. You can do that with the [Qualys SSL Server Test](https://www.ssllabs.com/ssltest/). I got an A+ rating because I added a [HTTP Strict Transport Security](https://developer.mozilla.org/en-US/docs/Web/Security/HTTP_strict_transport_security) header to my requests. You should at least get an A rating, or A+ if you enabled the HSTS header.

## Conclusion

Setting up HTTPS may look scary at first, but once you've done it, it isn't actually that difficult. The hardest part of it may just be configuring the web server. While nginx has quite sane defaults, it isn't perfect, so you really have to manually configure some parts of it.
