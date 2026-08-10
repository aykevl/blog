---
title: Syncthing on a Kobo
date: 2026-08-10
summary: How to install Syncthing on a Kobo e-reader
---

I have a new Kobo Clara BW e-reader (since my previous Kobo Aura sadly broke), and have installed Syncthing on it. It was surprisingly easy actually, roughly following the steps of [this blog post](https://mkecountyblog.com/install-koreader-nickelmenu-and-syncthing-on-a-kobo-ereader) but modifying them a bit since some things changed or just got a lot easier since then.

In this guide I assume you're familiar with basic Linux tools, in particular how to use SSH.

 1. [Install NickelMenu](https://pgaskin.net/NickelMenu/).
 2. Add at least the following entry to the NickelMenu (just put it in a file in `.adds/nm`, for example `.adds/nm/menu`):

        menu_item :main :IP Address :cmd_output :500:/sbin/ifconfig | /usr/bin/awk '/inet addr/{print substr($2,6)}'

    What this does is add a menu entry to quickly get the IP address of the Kobo when it is connected over WiFi. You'll need this later.
 3. Enable the built-in SSH server.  
    Kobo devices (at least starting with [firmware version 4.42.23296](https://www.mobileread.com/forums/showthread.php?t=368442#post4516671)) have a built-in SSH server that is easy to enable.
     1. Rename `.kobo/ssh-disabled` to `.kobo/ssh-enabled` (you may need to reboot afterwards, I don't remember).
     2. While connected to wifi, run `ssh root@<IP>` where the IP is the IP address that can be obtained from the "IP Address" NickelMenu entry. Make sure that your computer and Kobo are connected to the same WiFi network for this to work.
     3. Enter a new root password when prompted. Make sure you remember this one! Or, just make it an impossibly long random password to forget and use SSH keys with the next step.
     4. Now that you have SSH and are logged in to the device, you can add a [SSH key](https://www.digitalocean.com/community/tutorials/how-to-configure-ssh-key-based-authentication-on-a-linux-server) to the e-reader (I assume you already know how to do that, or you can read the linked tutorial). Weirdly, the home directory for the root user is `/` so the SSH key is stored in `/.ssh/authorized_keys`.
  4. Download [Syncthing for Linux ARM 32-bit devices](https://syncthing.net/downloads/) and put it in `.adds/syncthing` (note that the normally accessible part of the Kobo is stored in `/mnt/onboard`, so the full path would be `/mnt/onboard/.adds/syncthing`).
  5. Copy a valid ca-certificates.crt file to the e-reader, and store it in `/etc/ssl/certs/ca-certificates.crt`. The one on Fedora Linux (also stored at `/etc/ssl/certs/ca-certificates.crt`) seems to work well enough. This step is necessary for Syncthing to connect to relays (so the various devices can find each other) and check for updates.
  6. Add a valid initial configuration file. Put the following configuration file (copied from the original blog) in `/.local/state/syncthing/config.xml`, creating the parent directories first:
  ```xml
  <configuration version="18">
      <gui enabled="true" tls="false" debugging="false">
          <address>0.0.0.0:8384</address>
      </gui>
  </configuration>
  ```
 7. Now you can run Syncthing from the command line! It should be as simple as running the following command:
    
        /mnt/onboard/.adds/syncthing
    
    You can access it on a web browser at `http://<IP>:8384/` where `<IP>` is the Kobo IP address. (Unfortunately the built-in web browser appears to be too far out of date to be able to open the Syncthing configuration page). It should work as you'd expect with Syncthing, though perhaps a little slower.
 8. Configure Syncthing. Set a login password, add directories, etc. I recommend putting synced folders in a subdirectory of `/mnt/onboard`, for example `/mnt/onboard/Books`.
 9. Add the following NickelMenu entries (perhaps in the same `.adds/nm/menu` file), to easily start and stop Syncthing:
 
    ```
    menu_item :main :Syncthing Start :cmd_spawn :quiet:/mnt/onboard/.adds/syncthing serve &
    chain_success :dbg_toast :Started Syncthing
    menu_item :main :Syncthing Stop :cmd_spawn :quiet:/usr/bin/pkill syncthing
    chain_success :dbg_toast :Stopped Syncthing
    ```
    
    Also, I recommend adding the following entry to easily re-scan the local library (accessible from My Books -> dots in the top right):
    
    ```
    menu_item :library :Import books       :nickel_misc        :rescan_books
    ```
    
    The Kobo won't automatically import new books, since normally books are added only when it is connected over USB or when synced by the official firmware. So we have to manually trigger the import with the above menu entry.

That's it! You can start and stop Syncthing at will, access the web UI if needed, and rescan books after they've been synced to the e-reader.

I have originally based myself on the blog post mentioned above, but changed a few things:

  * This guide uses the built-in SSH server instead of the one from KOReader. This is much easier to set up, and should work on recent firmware versions (at least on the Kobo Clara BW, don't know about other models).
  * I've put the commands directly in the NickelMenu entries, instead of through separate shell scripts. I think it's easier to modify this way.
  * I've updated the various configuartion paths. The original post assumed that the root user would use `/root` as the home directory (as is conventional), but for some reason the root user on my e-reader uses `/` as the home directory. So I've had to update the various paths.
