
echo "iperf -c 10.45.0.2 -i 1 -b $1 -t $4"
iperf -c 10.45.0.2 -i 1 -b $1 -t $4  &


sleep 5

echo "iperf -c 10.45.0.3 -i 1 -b $2 -t $4"
iperf -c 10.45.0.3 -i 1 -b $2 -t $4 &  

sleep 5

echo "iperf -c 10.45.0.4 -i 1 -b $3 -t $4"
iperf -c 10.45.0.4 -i 1 -b $4 -t $4  