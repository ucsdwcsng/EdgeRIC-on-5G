cd srs-4G-UE/build
./srsue/src/srsue ../.config/ue1-4g-zmq.conf &

sleep 2
./srsue/src/srsue ../.config/ue2-4g-zmq.conf &

sleep 2
./srsue/src/srsue ../.config/ue3-4g-zmq.conf &

sleep 2
./srsue/src/srsue ../.config/ue4-4g-zmq.conf