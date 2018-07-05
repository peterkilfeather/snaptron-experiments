#!/usr/bin/env python2.7

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
import os
import argparse
import gzip
import math
import urllib2
import re

import clsnapconf
import clsnapfunc

#splice event types
#retained intron
RI='ri'

splice_mates_map={'d+':'1','d-':'2','a+':'2','a-':'1'}
base_query_fields = set(['donor','acceptor'])
fmap = {'filters':'rfilter','metadata':'sfilter','region':'regions','samples':'sids'}
def parse_query_argument(args, record, fieldnames, groups, groups_seen, datasources, endpoints, inline_group=False, header=True):
    '''Called from parse_command_line_args;
    builds the Snaptron query string from one
    or more of the separate query arguments passed in fieldnames:
    region (range), filters (rfilter), metadata (sfilter),
    and samples (sids)'''

    query=[None]
    fields_seen = set()
    group = None
    intron_strand = None
    intron_strand_prefix = None
    region = None
    for field in fieldnames:
        if len(record[field]) > 0:
            fields_seen.add(field)
            if field == 'filters' or field == 'metadata':
                predicates = re.sub("=",":",record[field])
                predicates = predicates.split('&')
                query.append("&".join(["%s=%s" % (fmap[field],x) for x in predicates]))
            elif field == 'group':
                group = record[field]
                #dont want to print the header multiple times for the same group
                if group in groups_seen:
                    header = False
                    if args.function == clsnapconf.PSI_FUNC:
                        gidx = groups_seen[group]
                        groups[gidx] = "A1_" + group
                        group = "A2_" + group
                else:
                    groups_seen[group]=len(groups)
                groups.append(group)
            elif field == 'samples' and args.endpoint == clsnapconf.BASES_ENDPOINT:
                #if the user wants to subselect samples in a base-level query
                #switch the argument to use the fields approach, since all sample
                #constraints are ignored/will error for base level queries
                query.append("%s=%s" % ('fields',record[field]))
            elif field in base_query_fields: #or (field == 'event-type' and record[field] == clsnapconf.RETAINED_INTRON):
                endpoints.append(clsnapconf.BASES_ENDPOINT)
                datasources.append(args.datasrc)
                intron_strand = record[field]
                #use first letter of donor/acceptor
                intron_strand_prefix = field[0]
            else:
                mapped_field = field
                if field in fmap:
                    mapped_field = fmap[field]
                query.append("%s=%s" % (mapped_field,record[field]))
    #we're only making a query against the metadata
    if len(fields_seen) == 1 and "metadata" in fields_seen:
        endpoints[0] = clsnapconf.SAMPLE_ENDPOINT
    if not header:
        query.append("header=0")
    #either we got a group or we have to shift the list over by one
    if inline_group and group is not None:
        query[0] = "group=%s" % (group)
    else:
        query = query[1:]
    queries = []
    queries.append(query)
    if intron_strand is not None:
        args.function = clsnapconf.MATES_FUNC
        either = 'either=%s' % str(splice_mates_map[intron_strand_prefix+intron_strand])
        #update the junction query with the proper strand
        query.append('rfilter=strand:%s' % intron_strand)
        query.append(either)
        #base query
        mapped_field = fmap['region']
        second_query = []
        if inline_group and group is not None:
            second_query.append("group=%s" % (group))
        second_query.append("%s=%s" % (mapped_field, record['region']))
        second_query.append(either)
        args.BASE_START_COL = clsnapconf.INTERVAL_END_COL + 1
        if 'samples' in record and record['samples'] is not None:
            second_query.append("fields=%s" % (record['samples']))
            args.BASE_START_COL = 1
        queries.append(second_query)
    queries = ["&".join(q) for q in queries]
    return queries


def parse_command_line_args(args, ):
    '''Loop through arguments passed in on the command line and parse them'''

    endpoints = [args.endpoint]
    datasources = [args.datasrc]
    fieldnames = []
    for field in clsnapconf.FIELD_ARGS.keys():
        if field in vars(args) and vars(args)[field] is not None:
            fieldnames.append(field)
    groups = []
    subqueries = parse_query_argument(args, vars(args), fieldnames, groups, {}, datasources, endpoints, header=args.function is not None or not args.noheader)
    return ([subqueries], groups, datasources, endpoints)


def breakup_junction_id_query(jids):
    ln = len(jids)
    queries = []
    if ln > clsnapconf.ID_LIMIT:
        jids = list(jids)
        for i in xrange(0, ln, clsnapconf.ID_LIMIT):
            idq = 'ids='+','.join([str(z) for z in jids[i:i+clsnapconf.ID_LIMIT]])
            queries.append(idq)
    else:
        queries.append('ids='+','.join([str(z) for z in jids]))
    return queries

def samples_changed(args,cache_file):
    response = urllib2.urlopen("%s/%s/samples?check_for_update=1" % (clsnapconf.SERVICE_URL,args.datasrc))
    remote_timestamp = response.read()
    remote_timestamp.rstrip()
    remote_timestamp = float(remote_timestamp)
    stats = os.stat(cache_file)
    local_timestamp = stats.st_mtime
    if remote_timestamp > local_timestamp:
        return True
    return False

def download_sample_metadata(args, split=False):
    '''Dump from Snaptron WSI the full sample metadata for a specific data compilation (source)
    to a local file if not already cached'''

    sample_records = {}
    sample_records_split = {}
    cache_file = os.path.join(args.tmpdir,"snaptron_sample_metadata_cache.%s.tsv.gz" % args.datasrc)
    gfout = None
    if clsnapconf.CACHE_SAMPLE_METADTA:
        if os.path.exists(cache_file) and not samples_changed(args,cache_file):
            with gzip.open(cache_file,"r") as gfin:
                for (i,line) in enumerate(gfin):
                    line = line.rstrip()
                    fields = line.split('\t')
                    sample_records[fields[0]]=line
                    sample_records_split[fields[0]]=fields
                    if i == 0:
                        sample_records["header"]=line
            if '' in sample_records:
                del sample_records['']
                del sample_records_split['']
            return (sample_records, sample_records_split)
        else:
            gfout = gzip.open(cache_file+".tmp","w")
    response = urllib2.urlopen("%s/%s/samples?all=1" % (clsnapconf.SERVICE_URL,args.datasrc))
    all_records = response.read()
    all_records = all_records.split('\n')
    for (i,line) in enumerate(all_records):
        fields = line.split('\t')
        sample_records[fields[0]]=line
        sample_records_split[fields[0]]=fields
        if i == 0:
            #remove lucene index type chars from header
            line = re.sub('_[itsf]\t','\t',line)
            line = re.sub('_[itsf]$','',line)
            sample_records["header"]=line
        if gfout is not None:
            gfout.write("%s\n" % (line))
    if gfout is not None:
        gfout.close()
        os.rename(cache_file+".tmp", cache_file)
    if '' in sample_records:
        del sample_records['']
        del sample_records_split['']
    return (sample_records, sample_records_split)

def median(mlist):
    sl = len(mlist)
    if sl == 0:
        return None
    s = sorted(mlist)
    if sl % 2 == 0:
        return (s[sl/2]+s[(sl/2)-1])/2.0
    return s[sl/2] 

def round_like_R(num, ndigits=0):
    '''Attempt to do IEC 60559 rounding half-way cases to nearest even (what R uses) to be equivalent to recount''' 
    p = 10**(max(0,ndigits-1))
    absx = math.fabs(num*p)
    y = math.floor(absx)
    diff = absx - y
    if diff > 0.5 or (diff == 0.5 and y % 2 != 0):
        return math.copysign((y / p) + 1.0, num)
    return math.copysign(y / p, num)

#assumes you already have the AUCs and junction sum total coverages per sample
#AUCs pulled out using:
#wiggletools print non_unique_base_coverage.bw.auc AUC non_unique_base_coverage.bw
def normalize_coverage(args, record, divisor_col, scaling_factor):
    fields = record.rstrip().split('\t')
    if fields[1] == 'snaptron_id':
        return record
    #do he full normalization + scaling here
    fields[clsnapconf.SAMPLE_IDS_COL] = ",".join( \
        [y for y in \
         [x.split(':')[0]+":"+str(int(round_like_R( \
             (scaling_factor * float(x.split(':')[1]))/float(args.sample_records_split[x.split(':')[0]][divisor_col])))) \
          for x in fields[clsnapconf.SAMPLE_IDS_COL].split(',') \
          if x != '' and x.split(':')[0] in args.sample_records_split] \
         if y.split(':')[1] != "0"])
    #need to recalculate summary stats with normalized (and possibly reduced) sample coverages
    normalized_counts = [int(x.split(':')[1]) for x in fields[clsnapconf.SAMPLE_IDS_COL].split(',')]
    fields[clsnapconf.SAMPLE_COUNT_COL] = len(normalized_counts)
    fields[clsnapconf.SAMPLE_SUM_COL] = sum(normalized_counts)
    fields[clsnapconf.SAMPLE_AVG_COL] = fields[clsnapconf.SAMPLE_SUM_COL]/float(fields[clsnapconf.SAMPLE_COUNT_COL])
    fields[clsnapconf.SAMPLE_MED_COL] = float(median(normalized_counts))
    fields[clsnapconf.SAMPLE_IDS_COL] = ',' + fields[clsnapconf.SAMPLE_IDS_COL]
    
    return "\t".join([str(x) for x in fields])
