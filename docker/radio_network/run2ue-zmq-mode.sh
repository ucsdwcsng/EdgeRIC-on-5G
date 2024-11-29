cd srs-4G-UE/build
./srsue/src/srsue ../.config/ue1-4g-zmq.conf --params_filename="../params1.txt" &

sleep 2
./srsue/src/srsue2 ../.config/ue2-4g-zmq.conf --params_filename="../params2.txt" 