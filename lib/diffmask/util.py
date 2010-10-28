#!/usr/bin/python
#	vim:fileencoding=utf-8
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

def toString(obj):
	if hasattr(obj, 'toString'):
		return obj.toString()
	else:
		return obj

class DiffmaskList(list):
	""" A list class extended with a simple toString() method. """
	def toString(self):
		return ''.join([toString(x) for x in self])

	def find(self, key):
		for e in self:
			if e == key:
				return e
		else:
			return None
