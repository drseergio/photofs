photofs
=======

photofs is a virtual file system for viewing photos. photofs lists photos in
4 different modes:

  * date -- structure follows date information, YYYY/MM/DD/..

  * sets -- groups photos using labels (extracted from XMP metadata), intended
          for events, trips, etc photo groups, like "1992 Summer trip to Alaska"

  * tags -- drill down in photos by selecting multiple tags; tags are extracted
          from IPTC keyword section; e.g.: vacation/summer/hawaii/...

  * conf -- drill down by photo settings, such as F-stop, shutter speed, ISO; e.g.:
          camera/Canon/f/2.8/iso/100/...

How it works
=======

photofs relies on Linux kernel feature FUSE that lets one create virtual file
systems entirely in user-space. photofs also utilizes inotify to update its
virtual views when new photos are added or existing photos are changed or
modified.

photofs keeps its index in a temporary sqlite3 database stored in /tmp. The
database is re-created every time upon the start so there is no state preserved
between runs. By design, photofs should be kept running and inotify feature of
the Linux kernel will ensure that all updates to the underlying files are
automatically reflected.


photofs is licensed under GPLv3

Example usage:
=======

```
$ python photofs.py -o root=/home/drseergio/Photos/ -o mode=date /home/drseergio/photofs
```

Dependencies
=======

  * GExiv2 library with enable introspection
  media-libs/gexiv2 introspection

  * pyinotify
  dev-python/pyinotify

  * sqlite3
  dev-db/sqlite

  * python fuse
  dev-python/fuse-python
