# -*- encoding: utf-8 -*-

'''walker.py: traverses real file-system and extracts photo meta-data.'''

__author__ = 'drseergio@gmail.com (Sergey Pisarenko)'

import logging
import os

from gi.repository import GExiv2

from photofs.filters import escape
from photofs.filters import filter_datetime
from photofs.filters import filter_fnumber
from photofs.filters import filter_label
from photofs.filters import filter_lens_spec


class PhotoWalker(object):
  _METADATA_NAME_MAP = {
      'Exif.Photo.DateTimeOriginal': 'datetime',
      'Exif.Photo.FNumber': 'f',
      'Exif.Photo.ISOSpeedRatings': 'iso',
      'Exif.Image.Make': 'make',
      'Exif.Image.Model': 'camera',
      'Exif.Photo.LensModel': 'lens_model',
      'Exif.Photo.LensSpecification': 'lens_spec',
      'Xmp.xmp.Label': 'label'}
  _METADATA_FILTER_MAP = {
      'Exif.Photo.DateTimeOriginal': filter_datetime,
      'Exif.Photo.FNumber': filter_fnumber,
      'Exif.Photo.LensSpecification': filter_lens_spec,
      'Xmp.xmp.Label': filter_label}

  def __init__(self, path, db):
    self.path = path
    self.db = db

  def Walk(self):
    for dirname, _dirnames, filenames in os.walk(self.path):
      for filename in filenames:
        full_path = os.path.join(dirname, filename)
        try:
          meta = self.ReadMetadata(full_path)
        except Exception, e:
          logging.error('Failed adding %s', full_path)
          logging.exception(e)
          continue
        self.db.StorePhoto(full_path, meta)

  def ReadMetadata(self, path):
    meta = {}
    gexiv2_meta = GExiv2.Metadata(path)

    for k in self._METADATA_NAME_MAP:
      name = self._METADATA_NAME_MAP[k]

      if k in self._METADATA_FILTER_MAP:
        meta[name] = self._METADATA_FILTER_MAP[k](gexiv2_meta, k)
      else:
        meta[name] = escape(gexiv2_meta.get(k))

    meta['tags'] = [escape(t) for t in
        gexiv2_meta.get_tag_multiple('Iptc.Application2.Keywords')]
    meta['exposure'] = escape(str(gexiv2_meta.get_exposure_time()))
    meta['focal_length'] = escape(str(int(gexiv2_meta.get_focal_length())))
    meta['year'] = meta['datetime'].strftime('%Y')
    meta['month'] = meta['datetime'].strftime('%m')
    meta['day'] = meta['datetime'].strftime('%d')
    meta['datetime'] = meta['datetime'].strftime('%Y%m%d%H%M%S')
    meta['path'] = path

    return meta
