echo "iperf -c 10.45.0.2 -u -i 1 -b $1 -t $6"
iperf -c 10.45.1.2 -u -i 1 -b $1 -t $6  &


sleep 5

echo "iperf -c 10.45.0.3 -u -i 1 -b $2 -t $6"
iperf -c 10.45.1.3 -u -i 1 -b $2 -t $6 &  

sleep 5

echo "iperf -c 10.45.0.4 -u -i 1 -b $3 -t $6"
iperf -c 10.45.1.4 -u -i 1 -b $3 -t $6 &

sleep 5

echo "iperf -c 10.45.0.5 -u -i 1 -b $4 -t $6"
iperf -c 10.45.1.5 -u -i 1 -b $4 -t $6 &


sleep 5

echo "iperf -c 10.45.0.6 -u -i 1 -b $5 -t $6"
iperf -c 10.45.1.6 -u -i 1 -b $5 -t $6