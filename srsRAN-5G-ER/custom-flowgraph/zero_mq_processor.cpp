// zero_mq_processor.cpp

#include <zmq.hpp>
#include <thread>
#include <vector>
#include <complex>
#include <mutex>
#include <iostream>
#include <fstream>
#include <chrono>
#include <atomic>
#include <map>
#include <string>

// Include the headers for ReqSource and RepSink
#include "req_source.h"
#include "rep_sink.h"

class ZeroMQProcessor {
public:
    ZeroMQProcessor(double samp_rate = 23.04e6)
        : samp_rate(samp_rate), stop_flag(false)
    {
        // Addresses
        source_addresses = {
            {"source1", "tcp://localhost:2001"}, // zeromq_req_source_1
            {"source2", "tcp://localhost:2011"}, // zeromq_req_source_0
            {"source3", "tcp://localhost:2101"}, // zeromq_req_source_3
        };
        sink_addresses = {
            {"sink1", "tcp://*:2000"}, // zeromq_rep_sink_0
            {"sink2", "tcp://*:2010"}, // zeromq_rep_sink_1
            {"sink3", "tcp://*:2100"}, // zeromq_rep_sink_2
        };
    }

    void start() {
        // Initialize ReqSources
        source1 = std::make_shared<ReqSource>(source_addresses["source1"]);
        source2 = std::make_shared<ReqSource>(source_addresses["source2"]);
        source3 = std::make_shared<ReqSource>(source_addresses["source3"]);

        source1->start();
        source2->start();
        source3->start();

        // Initialize RepSinks
        sink1 = std::make_shared<RepSink>(sink_addresses["sink1"]);
        sink2 = std::make_shared<RepSink>(sink_addresses["sink2"]);
        sink3 = std::make_shared<RepSink>(sink_addresses["sink3"]);

        sink1->start();
        sink2->start();
        sink3->start();

        // Start processing thread
        processing_thread = std::thread(&ZeroMQProcessor::process_data, this);
    }

    void stop() {
        stop_flag = true;

        if (processing_thread.joinable())
            processing_thread.join();

        // Stop sources and sinks
        source1->stop();
        source2->stop();
        source3->stop();

        sink1->stop();
        sink2->stop();
        sink3->stop();
    }

private:
    double samp_rate;

    // Addresses
    std::map<std::string, std::string> source_addresses;
    std::map<std::string, std::string> sink_addresses;

    // ReqSources
    std::shared_ptr<ReqSource> source1;
    std::shared_ptr<ReqSource> source2;
    std::shared_ptr<ReqSource> source3;

    // RepSinks
    std::shared_ptr<RepSink> sink1;
    std::shared_ptr<RepSink> sink2;
    std::shared_ptr<RepSink> sink3;

    // Thread
    std::thread processing_thread;

    // Stop flag
    std::atomic<bool> stop_flag;

    void process_data() {
        while (!stop_flag) {
            // Get data from sources
            auto data1 = source1->get_data(); // Source 1
            auto data2 = source2->get_data(); // Source 2
            auto data3 = source3->get_data(); // Source 3

            // Process data (Add data1 and data2)
            std::vector<std::complex<float>> sum_data;
            if (!data1.empty() && !data2.empty() && data1.size() == data2.size()) {
                sum_data.resize(data1.size());
                for (size_t i = 0; i < data1.size(); ++i) {
                    sum_data[i] = data1[i] + data2[i];
                }
            }

            // Set data to sinks
            if (!sum_data.empty()) {
                sink1->set_data(sum_data); // Send sum to Sink 1
            }

            if (!data3.empty()) {
                sink2->set_data(data3); // Send data3 to Sink 2
                sink3->set_data(data3); // Send data3 to Sink 3
            }

            // Throttling (simulate sample rate)
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }
};

int main() {
    ZeroMQProcessor processor;
    processor.start();

    // Keep the main thread alive
    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    processor.stop();
    return 0;
}
