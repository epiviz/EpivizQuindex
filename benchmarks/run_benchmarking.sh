python benchmarking.py --query_range 50 > 50_


for RUNS in 50 500 5000 50000 500000
do
    for REPEAT in 1 2 3 4 5 6 7 8 9 10
    do

    	python benchmarking.py --query_range $RUNS > ./results/{$RUNS}.{$REPEAT}.txt

    done

done