// req_source.h

#ifndef REQ_SOURCE_H
#define REQ_SOURCE_H

#include <zmq.hpp>
#include <thread>
#include <vector>
#include <complex>
#include <mutex>
#include <atomic>
#include <string>

class ReqSource {
public:
    ReqSource(const std::string& address);
    ~ReqSource();

    void start();
    void stop();

    std::vector<std::complex<float>> get_data();

private:
    void run();

    zmq::context_t context_;
    zmq::socket_t socket_;
    std::string address_;

    std::atomic<bool> stop_flag_;
    std::thread thread_;

    std::mutex buffer_mutex_;
    std::vector<std::complex<float>> buffer_;
};

#endif // REQ_SOURCE_H
