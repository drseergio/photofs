#!/usr/bin/env python

'''filters.py transforms values returned by GExiv2 library.'''

__author__ = 'drseergio@gmail.com (Sergey Pisarenko)'

__license__ = 'GPL'
__version__ = '1.0.0'

from datetime import datetime
from decimal import Decimal

_DATE_FORMAT = '%Y:%m:%d %H:%M:%S'


def filter_datetime(meta, k):
  return datetime.strptime(meta.get(k), _DATE_FORMAT)


def filter_fnumber(meta, k):
  value = meta.get(k)
  if not value:
    return None
  value_split = value.split('/')
  return str(round(Decimal(value_split[0]) / Decimal(value_split[1]), 1))


def filter_lens_spec(meta, k):
  value = meta.get(k)
  if not value and meta.get_focal_length():
    return str(int(meta.get_focal_length()))
  value_split = value.split(' ')
  return value_split[0].split('/')[0] + '-' + value_split[1].split('/')[0]


def filter_label(meta, k):
  return escape(meta.get(k))


def escape(value):
  return value.replace('/', '')
