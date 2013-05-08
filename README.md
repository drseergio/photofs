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

photofs keeps its indexes in ".photofs" folder in user's home path. A database
is created for each unique source (root) path. If you run multiple instances of
photofs per given root path (e.g. for different view modes) only one of the
instances will have write access to the database and will handle updates.
Remaining instances will be read-only. If the instance which has write access is
terminated one of the other instances will take over write-access.

By design, photofs should be kept running and inotify feature of
the Linux kernel will ensure that all updates to the underlying files are
automatically reflected.


photofs is licensed under GPLv3

Installation
=======

photofs uses setuptools. To install photofs run the following command
```
$ sudo python setup.py --install
```

Example usage:
=======

```
$ python photofs.py -o root=/home/drseergio/Photos/ -o mode=date /home/drseergio/photofs
```

Dependencies
=======

  * GExiv2 library version 0.6.0 or newer with enabled introspection
  (Gentoo ebuild =media-libs/gexiv2-0.6.0 with USE flag "introspection")

  * exiv2 library with XMP support
  (Gentoo ebuild media-gfx/exiv2 with USE flag "xmp")

  * pyinotify (Gentoo ebuild dev-python/pyinotify)

  * sqlite3 (Gentoo ebuild dev-db/sqlite)

  * python fuse (Gentoo ebuild dev-python/fuse-python)

  * pygobject (Gentoo ebuild dev-python/pygobject)

If not available in your distribution, GExiv2 can be downloaded from:
http://redmine.yorba.org/projects/gexiv2/wiki
