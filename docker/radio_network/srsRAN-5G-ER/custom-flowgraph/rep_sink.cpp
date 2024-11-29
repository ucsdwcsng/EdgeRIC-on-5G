// rep_sink.cpp

#include "rep_sink.h"
#include <iostream>

RepSink::RepSink(const std::string& address)
    : context_(1), socket_(context_, ZMQ_REP), address_(address), stop_flag_(false)
{
    socket_.bind(address_);

    // Set socket options using older API
    int timeout = 5000; // 5-second timeout
    socket_.setsockopt(ZMQ_RCVTIMEO, &timeout, sizeof(timeout)); // Receive timeout
    socket_.setsockopt(ZMQ_SNDTIMEO, &timeout, sizeof(timeout)); // Send timeout

    int linger = 0; // Close socket immediately
    socket_.setsockopt(ZMQ_LINGER, &linger, sizeof(linger));
}

RepSink::~RepSink()
{
    stop();
}

void RepSink::start()
{
    thread_ = std::thread(&RepSink::run, this);
}

void RepSink::stop()
{
    stop_flag_ = true;
    data_condition_.notify_all(); // Wake up any waiting threads
    if (thread_.joinable())
        thread_.join();
}

void RepSink::run()
{
    try {
        while (!stop_flag_) {
            // Wait for a request
            zmq::message_t request;
            bool received = socket_.recv(&request);

            if (received) {
                std::cout << "RepSink (" << address_ << "): Received request." << std::endl;

                // Retrieve data to send
                std::vector<std::complex<float>> data_to_send;
                {
                    std::unique_lock<std::mutex> lock(buffer_mutex_);
                    // Wait until data is available or stop_flag_ is true
                    data_condition_.wait(lock, [this] { return !buffer_.empty() || stop_flag_; });
                    data_to_send = buffer_;
                }

                if (!stop_flag_ && !data_to_send.empty()) {
                    zmq::message_t reply(data_to_send.size() * sizeof(std::complex<float>));
                    memcpy(reply.data(), data_to_send.data(), reply.size());
                    socket_.send(reply);
                    std::cout << "RepSink (" << address_ << "): Sent " << data_to_send.size() << " samples." << std::endl;
                } else {
                    // Send empty message if no data
                    zmq::message_t reply(0);
                    socket_.send(reply);
                    std::cout << "RepSink (" << address_ << "): No data to send, sent empty message." << std::endl;
                }
            } else {
                std::cerr << "RepSink (" << address_ << "): No request received or timeout occurred." << std::endl;
            }

            std::this_thread::yield();
        }
    } catch (const zmq::error_t& e) {
        std::cerr << "ZeroMQ Error in RepSink (" << address_ << "): " << e.what() << std::endl;
    }
}

void RepSink::set_data(const std::vector<std::complex<float>>& data)
{
    {
        std::lock_guard<std::mutex> lock(buffer_mutex_);
        buffer_ = data;
    }
    data_condition_.notify_all();
}
