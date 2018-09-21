#!/usr/bin/env python

# Copyright 2016, Christopher Wilks <broadsword@gmail.com>
#
# This file is part of Snaptron.
#
# Snaptron is free software: you can redistribute it and/or modify
# it under the terms of the 
# Creative Commons Attribution-NonCommercial 4.0 
# International Public License ("CC BY-NC 4.0").
#
# Snaptron is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# CC BY-NC 4.0 license for more details.
#
# You should have received a copy of the CC BY-NC 4.0 license
# along with Snaptron.  If not, see 
# <https://creativecommons.org/licenses/by-nc/4.0/legalcode>.

import sys
try:
    from urllib.request import urlopen
    from urllib.error import HTTPError
    from urllib.error import URLError
    from http.client import IncompleteRead
except ImportError:
    from urllib2 import urlopen
    from urllib2 import HTTPError
    from urllib2 import URLError
    from httplib import IncompleteRead
from SnaptronIterator import SnaptronIterator
import clsnapconf
import clsnaputil


class SnaptronIteratorHTTP(SnaptronIterator):

    def __init__(self,query_param_string,instance,endpoint):
        if endpoint == 'sample' or endpoint == 'annotation':
            endpoint += 's'
        SnaptronIterator.__init__(self,query_param_string,instance,endpoint) 

        self.SERVICE_URL=clsnapconf.SERVICE_URL
        self.construct_query_string()
        self.execute_query_string()

    def construct_query_string(self):
        self.query_string = "%s/%s/%s?%s" % (self.SERVICE_URL,self.instance,self.endpoint,self.query_param_string)
        return self.query_string
    
    @clsnaputil.retry((HTTPError,URLError), tries=17, delay=2, backoff=2)
    def my_urlopen(self):
       return urlopen(self.query_string)

    def execute_query_string(self):
        sys.stderr.write("%s\n" % (self.query_string))
        self.response = self.my_urlopen()
        return self.response

    def fill_buffer(self):
        #extend parent version to catch HTTP specific error
        try:
            return SnaptronIterator.fill_buffer(self)
        except IncompleteRead as ir:
            sys.stderr.write(ir.partial)
            raise ir

if __name__ == '__main__':
    it = SnaptronIteratorHTTP('regions=chr1:1-100000&rfilter=samples_count>:5', 'srav1', 'snaptron')
    for r in it:
        sys.stdout.write("%s\n" % r)
