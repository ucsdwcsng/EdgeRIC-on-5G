#
# Copyright 2021-2024 Software Radio Systems Limited
#
# This file is part of srsRAN
#
# srsRAN is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# srsRAN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# A copy of the GNU Affero General Public License can be found in
# the LICENSE file in the top-level directory of this distribution
# and at http://www.gnu.org/licenses/.
#

# Build args
################
# OS_VERSION            Ubuntu OS version
# LIB                   uhd or dpdk (lowercase)
# LIB_VERSION           UHD or DPDK version number
# ARCH                  gcc/clang compatible arch
# NUM_CORES             Number or empty for all
# EXTRA_CMAKE_ARGS      Extra flags for srsRAN Project

# ARG OS_VERSION=22.04
# ARG LIB=uhd
# ARG LIB_VERSION=4.6.0.0
# ARG ARCH=native
# ARG NUM_CORES=""

# ##################
# # Stage 1: Build #
# ##################
# FROM ubuntu:$OS_VERSION AS builder

# # Adding the complete repo to the context, in /src folder
# ADD . /src
# # An alternative could be to download the repo
# # RUN apt update && apt-get install -y --no-install-recommends git git-lfs
# # RUN git clone https://github.com/srsran/srsRAN_Project.git /src

# # Install srsRAN build dependencies
# ARG LIB
# RUN /src/docker/scripts/install_dependencies.sh build && \
#     /src/docker/scripts/install_${LIB}_dependencies.sh build

# ARG LIB_VERSION
# ARG ARCH
# ARG NUM_CORES

# # Compile UHD/DPDK
# RUN /src/docker/scripts/build_${LIB}.sh ${LIB_VERSION} ${ARCH} ${NUM_CORES}

# # Compile srsRAN Project and install it in the OS
# ARG EXTRA_CMAKE_ARGS=""
# RUN if [ -z "$NUM_CORES" ]; then NUM_CORES=$(nproc); fi && \
#     LIB_UPPER=$(echo $LIB | tr '[:lower:]' '[:upper:]') && \
#     export ${LIB_UPPER}_DIR="/opt/${LIB}/${LIB_VERSION}" && \
#     /src/docker/scripts/builder.sh \
#     -m "-j${NUM_CORES} install" \
#     -DBUILD_TESTS=True \
#     -DENABLE_${LIB_UPPER}=On \
#     -DCMAKE_CXX_FLAGS="-march=${ARCH}" \
#     -DCMAKE_INSTALL_PREFIX=/opt/srs \
#     ${EXTRA_CMAKE_ARGS} /src

# # Copy extra binaries
# RUN cp /src/build/tests/integrationtests/ofh/ru_emulator /usr/local/bin/ru_emulator

# ################
# # Stage 2: Run #
# ################

# FROM ubuntu:$OS_VERSION

# ARG LIB
# ARG LIB_VERSION

# # Copy srsRAN binaries and libraries installed in previous stage
# COPY --from=builder /opt/${LIB}/${LIB_VERSION} /opt/${LIB}/${LIB_VERSION}
# COPY --from=builder /opt/srs /usr/local

# # Copy the install dependencies scripts
# ADD docker/scripts/install_${LIB}_dependencies.sh /usr/local/etc/install_lib_dependencies.sh
# ADD docker/scripts/install_dependencies.sh /usr/local/etc/install_srsran_dependencies.sh
# ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/${LIB}/${LIB_VERSION}/lib/:/opt/${LIB}/${LIB_VERSION}/lib/x86_64-linux-gnu/:/opt/${LIB}/${LIB_VERSION}/lib/aarch64-linux-gnu/
# ENV PATH=$PATH:/opt/${LIB}/${LIB_VERSION}/bin/

# # Install srsran and lib runtime dependencies
# RUN /usr/local/etc/install_srsran_dependencies.sh run && \
#     /usr/local/etc/install_lib_dependencies.sh run && \
#     apt-get autoremove && apt-get clean && rm -rf /var/lib/apt/lists/*

######################################################################################

FROM ubuntu:20.04
#FROM uhd:latest


ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get install -y libfftw3-dev \
	libmbedtls-dev \
	libsctp-dev \
	qt5-default \
	libconfig++-dev \
	net-tools \
	nano \
	libtool pkg-config build-essential autoconf \
	automake \
	git  \
	python3 python3-distutils python3-pip python3-apt \
	libzmq3-dev python3-zmq \
	software-properties-common

RUN apt-get update 
RUN add-apt-repository ppa:gnuradio/gnuradio-releases
RUN apt-get update
RUN apt-get install -y gnuradio xterm python3-gi \
	gobject-introspection gir1.2-gtk-3.0 \
	iputils-ping \
	iproute2 libx11-dev iperf \
	cmake \
	redis-server

RUN pip3 install --upgrade pip
RUN pip3 install gym pandas torchvision tensorboard redis debugpy ray gymnasium dm_tree pyarrow typer scikit-image plotly
RUN pip3 install hydra-core==1.1.0
RUN pip3 uninstall -y protobuf
# Install protobuf version 3.20.*
RUN pip3 install protobuf==3.20.*

	 
RUN apt-get update 
RUN apt-get install -y cmake 
RUN cmake --version
	


## copy srsran and Pytorch
RUN mkdir -p /home/EdgeRIC-A-real-time-RIC
WORKDIR "/home/EdgeRIC-A-real-time-RIC"
COPY . .

## copying zmq header files 
#RUN cp zmq.h /usr/local/include
#RUN cp zmq.hpp /usr/local/include


## Compile srsran for enb/epc
RUN apt-get install -y libprotobuf-dev protobuf-compiler

WORKDIR "/home/EdgeRIC-A-real-time-RIC"
