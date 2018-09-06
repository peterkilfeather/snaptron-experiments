#!/bin/bash
#takes a tab-delimited file of annotated exons of format:
#chr	start	end	gene_id	exon_length	strand
#and splits them into no more than 1000 bp chunks
#this enables them to be queries for base coverage
#using the Snaptron client w/o disconnects
#usage: cat recount_hg38_gencodev25_disjoint_exons.tsv | split_annotated_exons_for_client_querying.sh > recount_hg38_gencodev25_disjoint_exons.1k_splits.tsv

cat /dev/stdin | perl -ne 'BEGIN { $MIN_SZ=1000; $N=1000; } chomp; $s=$_; ($strand,$g,$chrm,$start,$end,$sz)=split(/\t/,$s); $s=join("\t",($chrm,$start,$end,$g,$sz,$strand));  if($sz <= $MIN_SZ) { print "$s\n"; next; } $n=$sz/$N; $n1=int($n); $n2=$sz-($N*$n1); $i=$start; $idx=0; while(($i+$N)-1 <= $end) { $idx_=$idx; $idx_="0".$idx if($idx<10); $nend = $i+$N-1; $nsz = ($nend - $i) + 1; print "$chrm\t$i\t$nend\t$g;$idx_\t$nsz\t$strand\n"; $i=$i+$N; $idx++; } $idx_= $idx; $idx_="0".$idx if($idx<10); $nend = $i+$n2-1; $nsz = ($nend - $i) + 1; print "$chrm\t$i\t$nend\t$g;$idx_\t$nsz\t$strand\n" if($nsz > 0);' | sort -t'	' -k4,4 -k1,1 -k2,2n -k3,3n > exons.split
mkdir jobs
mkdir runs
#cat <(echo exons.split) exons.split | perl -ne 'BEGIN { $NUM_LINES=60000; $i=0; $fc=-1; } chomp;  $f=$_; if($i==0 && $fc==-1) { $F=$f; $fc=0; open(OUT,">jobs/$F.$fc"); print OUT "region\tcontains\tgroup\n"; print "python snaptron-experiments/client/bulk_base_intervals.py --bulk-query-file jobs/$F.$fc --endpoint bases --datasrc ct_h_s --summary exon > runs/$F.$fc.run 2>&1\n"; next; } $i++; if($i > $NUM_LINES) { close(OUT); $fc++; open(OUT,">jobs/$F.$fc"); print OUT "region\tcontains\tgroup\n"; $i=1; print "python snaptron-experiments/client/bulk_base_intervals.py --bulk-query-file jobs/$F.$fc --endpoint bases --datasrc ct_h_s --summary exon > runs/$F.$fc.run 2>&1\n"; } ($c,$s,$e,$n,$sz,$n1)=split(/\t/,$f); print OUT "$c:$s-$e\t1\t$n\n"; END { close(OUT); }' > jobs.file
cat <(echo exons.split) exons.split | perl -ne 'BEGIN { $NUM_BASES=41000000; $i=0; $fc=-1; } chomp;  $f=$_; if($i==0 && $fc==-1) { $F=$f; $fc=0; open(OUT,">jobs/$F.$fc"); print OUT "region\tcontains\tgroup\n"; print "python snaptron-experiments/client/bulk_base_intervals.py --bulk-query-file jobs/$F.$fc --endpoint bases --datasrc ct_h_s --summary exon > runs/$F.$fc.run 2>&1\n"; next; } ($c,$s,$e,$n,$sz,$n1)=split(/\t/,$f); $i+=$sz; if($i > $NUM_BASES) { close(OUT); $fc++; open(OUT,">jobs/$F.$fc"); print OUT "region\tcontains\tgroup\n"; $i=$sz; print "python snaptron-experiments/client/bulk_base_intervals.py --bulk-query-file jobs/$F.$fc --endpoint bases --datasrc ct_h_s --summary exon > runs/$F.$fc.run 2>&1\n"; } ($c,$s,$e,$n,$sz,$n1)=split(/\t/,$f); print OUT "$c:$s-$e\t1\t$n\n"; END { close(OUT); }' > jobs.file