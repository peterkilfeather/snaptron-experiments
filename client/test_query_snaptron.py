#!/usr/bin/env python
import sys
import unittest
from argparse import Namespace
import query_snaptron
import test_data

def setUpModule():
    pass

def tearDownModule():
    pass


class TestSampleCountingPerGroup(unittest.TestCase):
    '''Test the count_samples_per_group(...) method
    which underlies many of the client high-level queries/functions
    (TS, SSC, JIR, PSI)'''

    #we'll also need to consider the 'either' modifier as another
    #source of potential bugs

    def setUp(self):
        pass
    
    def test_ssc_count_samples_per_group(self):
        group = 'C1orf100 non_validated'
        either = 2
        results = {'samples':{},'queries':[],'exons':{'start':{},'end':{}},'either':either}
        results['groups_seen']={group:1}
        results['shared']={}
        results['annotated']={group:{}}
        results['annotated'][group][results['groups_seen'][group]]=0
        results['annotations']={group:{}}

        args = Namespace(function='shared')

        with open('../tests/C1orf100.raw%d' % either,'r') as fin:
            query_snaptron.count_samples_per_group(args, results, fin.readline().rstrip(), group, out_fh=None)
            query_snaptron.count_samples_per_group(args, results, fin.readline().rstrip(), group, out_fh=None)
            
            self.assertEqual(test_data.C1orf100_results_first_time_through, results) 
        
            #keep going to the end of the file
            for line in fin:
                query_snaptron.count_samples_per_group(args, results, line.rstrip(), group, out_fh=None)

            #now check the half-through results data structure
            self.assertEqual(test_data.C1orf100_results_after_first_basic_query, results) 


                

class TestJIR(unittest.TestCase):
    
    def setUp(self):
        pass

class TestSSC(unittest.TestCase):
    
    def setUp(self):
        pass

class TestTS(unittest.TestCase):
    
    def setUp(self):
        pass


#self.assertEqual(iids, EXPECTED_IIDS[IQs[i]+str(RQs_flat[r])+str(RQs_flat[r+1])])
class TestBasicQueries(unittest.TestCase):
    def setUp(self):
        pass

if __name__ == '__main__':
    unittest.main()
