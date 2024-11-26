# # Create a library from the edgeric source files
# add_library(edgeric STATIC edgeric.cpp)

# # Include the current directory for header files
# target_include_directories(edgeric PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

set(SRCS
    edgeric.cpp
    control_mcs.pb.cc # Add the generated Protobuf source file
    control_weights.pb.cc
    metrics.pb.cc
)

# Create a static library from the edgeric source files
# add_library(edgeric STATIC edgeric.cpp)
add_library(edgeric STATIC ${SRCS})

# Include the current directory for header files
# target_include_directories(edgeric PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_include_directories(edgeric PUBLIC ${CMAKE_CURRENT_SOURCE_DIR} ${PROTOBUF_INCLUDE_DIRS})

# Link the ZeroMQ and Protocol Buffers libraries to the edgeric library
target_link_libraries(edgeric PUBLIC ${ZMQ_LIBRARIES} ${Protobuf_LIBRARIES} zmq)

# Add to exported libraries if ENABLE_EXPORT is on
ADD_TO_EXPORTED_LIBS(edgeric)

########################################################################
# Disable specific warnings for Protobuf files
########################################################################
set_source_files_properties(control_mcs.pb.cc control_weights.pb.cc metrics.pb.cc PROPERTIES COMPILE_FLAGS -Wno-array-bounds)

