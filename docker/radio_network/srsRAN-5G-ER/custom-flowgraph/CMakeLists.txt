# cmake_minimum_required(VERSION 3.0)
# project(ZeroMQProcessor)

# set(CMAKE_CXX_STANDARD 11)

# # Find pkg-config
# find_package(PkgConfig REQUIRED)

# # Use pkg-config to find ZeroMQ
# pkg_check_modules(ZeroMQ REQUIRED libzmq)

# include_directories(${ZeroMQ_INCLUDE_DIRS})
# link_directories(${ZeroMQ_LIBRARY_DIRS})

# add_executable(zero_mq_processor zero_mq_processor.cpp)

# # Link with ZeroMQ and pthread
# target_link_libraries(zero_mq_processor PRIVATE ${ZeroMQ_LIBRARIES} pthread)

cmake_minimum_required(VERSION 3.5)
project(zero_mq_processor)

set(CMAKE_CXX_STANDARD 11)
# Find pkg-config
find_package(PkgConfig REQUIRED)

# Use pkg-config to find ZeroMQ
pkg_check_modules(ZeroMQ REQUIRED libzmq)

find_package(Threads REQUIRED)
#find_package(ZeroMQ REQUIRED)

include_directories(${ZeroMQ_INCLUDE_DIRS})

add_executable(zero_mq_processor
    zero_mq_processor.cpp
    req_source.cpp
    rep_sink.cpp
)

target_link_libraries(zero_mq_processor
    ${ZeroMQ_LIBRARIES}
    Threads::Threads
)
