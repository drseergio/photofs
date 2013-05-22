photofs
=======

photofs is a virtual file system for viewing photos. photofs lists photos in
4 different modes:

  * date -- structure follows date information, YYYY/MM/DD/..

  * albums -- groups photos using labels (extracted from XMP metadata), intended
          for events, trips, etc photo groups, like "1992 Summer trip to Alaska"

  * tags -- drill down in photos by selecting multiple tags; tags are extracted
          from IPTC keyword section; e.g.: vacation/summer/hawaii/...

  * camera -- drill down by photo settings, such as F-stop, shutter speed, ISO;
          e.g.: camera/Canon/f/2.8/iso/100/...

When you mount photofs all 4 views will be available under the root path.

A little bit more about the "albums" mode
=======

I have written "albums" mode mostly for my own photo work-flow. I typically view
photos in albums, e.g. "2011-02-01 Trip to Romania" and I am interested in
seeing all non-trashed (unfocused, flash did not fire) photos as well as
"selects" (or best pictures) only.

The root level in "albums" mode lists all available albums. As mentioned above,
album names are extracted from XMP tag "label". Under each album, all photos for
that album are listed.

In addition, in each album folder you will see a "selects" sub-folder. That is
intended for showing "selects" (or best) photos from that album. To determine if
a photo is a "select" it must have a "select" tag added to it.

How it works
=======

photofs relies on Linux kernel feature FUSE that lets one create virtual file
systems entirely in user-space. photofs also utilizes inotify to update its
virtual views when new photos are added or existing photos are changed or
modified.

photofs keeps its indexes in ".photofs" folder in user's home path. A database
is created for each unique source (root) path. It's possible to run only single
instance of photofs per given root path.

By design, photofs should be kept running and inotify feature of
the Linux kernel will ensure that all updates to the underlying files are
automatically reflected.

photofs allows the images to be edited through the virtual view. Furthermore,
there is hack to fool exiv2 library into believing that it can create temp
files in the same folder as the image. This is implemented so that qeytaks
program can operate directly in the photofs virtual view.


photofs is licensed under GPLv3

Installation
=======

photofs uses setuptools. To install photofs run the following command
```
$ sudo python setup.py install
```

Example usage:
=======

```
$ python photofs.py -o root=/home/drseergio/Photos/ /home/drseergio/photofs
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
