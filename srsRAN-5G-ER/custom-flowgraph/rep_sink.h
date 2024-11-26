// rep_sink.h

#ifndef REP_SINK_H
#define REP_SINK_H

#include <zmq.hpp>
#include <thread>
#include <vector>
#include <complex>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <string>

class RepSink {
public:
    RepSink(const std::string& address);
    ~RepSink();

    void start();
    void stop();

    void set_data(const std::vector<std::complex<float>>& data);

private:
    void run();

    zmq::context_t context_;
    zmq::socket_t socket_;
    std::string address_;

    std::atomic<bool> stop_flag_;
    std::thread thread_;

    std::mutex buffer_mutex_;
    std::condition_variable data_condition_;
    std::vector<std::complex<float>> buffer_;
};

#endif // REP_SINK_H
