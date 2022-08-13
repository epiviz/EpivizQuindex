python benchmarking.py --query_range 20 --num_file -1



for RUNS in 50 500 5000 50000 500000
do
    for REPEAT in 1 2 3 4 5 6 7 8 9 10
    do

        python benchmarking.py --query_range $RUNS --num_file -1 > ./results/size/{$RUNS}.{$REPEAT}.txt

    done
done


for NUMFILES in 20 40 60 80 100 120 140
do

    for REPEAT in 1 2 3 4 5 6 7 8 9 10
    do

        python benchmarking.py --query_range 50000 --num_file $NUMFILES > ./results/num_file/{$NUMFILES}.{$REPEAT}.txt

    done

done
