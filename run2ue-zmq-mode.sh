cd srs-4G-UE/build
sudo ./srsue/src/srsue ../.config/ue1-4g-zmq.conf --params_filename="../params1.txt" &

sleep 2
sudo ./srsue/src/srsue2 ../.config/ue2-4g-zmq.conf --params_filename="../params2.txt" 