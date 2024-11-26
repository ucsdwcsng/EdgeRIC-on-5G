cd srs-4G-UE/build
sudo ./srsue/src/srsue ../.config/ue1-4g-zmq.conf &

sleep 2
sudo ./srsue/src/srsue ../.config/ue2-4g-zmq.conf &

sleep 2
sudo ./srsue/src/srsue ../.config/ue3-4g-zmq.conf &

sleep 2
sudo ./srsue/src/srsue ../.config/ue4-4g-zmq.conf