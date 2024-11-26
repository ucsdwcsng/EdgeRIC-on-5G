// req_source.cpp

#include "req_source.h"
#include <iostream>

ReqSource::ReqSource(const std::string& address)
    : context_(1), socket_(context_, ZMQ_REQ), address_(address), stop_flag_(false)
{
    socket_.connect(address_);

    // Set socket options using older API
    int timeout = 5000; // 5-second timeout
    socket_.setsockopt(ZMQ_RCVTIMEO, &timeout, sizeof(timeout)); // Receive timeout
    socket_.setsockopt(ZMQ_SNDTIMEO, &timeout, sizeof(timeout)); // Send timeout

    int linger = 0; // Close socket immediately
    socket_.setsockopt(ZMQ_LINGER, &linger, sizeof(linger));
}

ReqSource::~ReqSource()
{
    stop();
}

void ReqSource::start()
{
    thread_ = std::thread(&ReqSource::run, this);
}

void ReqSource::stop()
{
    stop_flag_ = true;
    if (thread_.joinable())
        thread_.join();
}

void ReqSource::run()
{
    try {
        // Send initial request
        zmq::message_t request(0);
        socket_.send(request);
        std::cout << "ReqSource (" << address_ << "): Sent initial request." << std::endl;

        while (!stop_flag_) {
            // Receive data
            zmq::message_t reply;
            bool received = socket_.recv(&reply);

            if (received && reply.size() > 0) {
                size_t num_samples = reply.size() / sizeof(std::complex<float>);
                std::vector<std::complex<float>> samples(num_samples);
                memcpy(samples.data(), reply.data(), reply.size());

                // Store data in buffer
                {
                    std::lock_guard<std::mutex> lock(buffer_mutex_);
                    buffer_ = std::move(samples);
                }

                std::cout << "ReqSource (" << address_ << "): Received " << num_samples << " samples." << std::endl;
            } else {
                std::cerr << "ReqSource (" << address_ << "): No data received or timeout occurred." << std::endl;
            }

            // Send request for next data
            zmq::message_t request(0);
            socket_.send(request);
            std::cout << "ReqSource (" << address_ << "): Sent request for next data." << std::endl;

            std::this_thread::yield();
        }
    } catch (const zmq::error_t& e) {
        std::cerr << "ZeroMQ Error in ReqSource (" << address_ << "): " << e.what() << std::endl;
    }
}

std::vector<std::complex<float>> ReqSource::get_data()
{
    std::lock_guard<std::mutex> lock(buffer_mutex_);
    return buffer_; // Return a copy of the data
}
