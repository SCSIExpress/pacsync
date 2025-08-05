cmake_minimum_required(VERSION 3.16)
project(PacmanSyncUtility VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Qt6 components
find_package(Qt6 REQUIRED COMPONENTS Core Widgets DBus)

# Enable Qt MOC, UIC, and RCC
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

# Include directories
include_directories(${CMAKE_CURRENT_SOURCE_DIR})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/client)

# Client Qt application sources (placeholder for future C++ components)
set(CLIENT_SOURCES
    # Future C++ Qt components can be added here
    # client/qt/main.cpp
    # client/qt/mainwindow.cpp
    # client/qt/systemtray.cpp
)

# Client Qt application headers (placeholder for future C++ components)
set(CLIENT_HEADERS
    # Future C++ Qt headers can be added here
    # client/qt/mainwindow.h
    # client/qt/systemtray.h
)

# Create client executable (commented out until C++ sources are added)
# add_executable(pacman-sync-client ${CLIENT_SOURCES} ${CLIENT_HEADERS})

# Link Qt libraries (commented out until executable is created)
# target_link_libraries(pacman-sync-client
#     Qt6::Core
#     Qt6::Widgets
#     Qt6::DBus
# )

# Install targets (commented out until executable is created)
# install(TARGETS pacman-sync-client
#     RUNTIME DESTINATION bin
# )

# For now, this CMakeLists.txt serves as a template for future C++ integration
# The current implementation uses Python with PyQt6 bindings

# Custom target to run Python client for development
add_custom_target(run-python-client
    COMMAND python3 -m client.main
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Running Python Qt client"
)

# Custom target to run server for development
add_custom_target(run-server
    COMMAND python3 -m server.main
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Running Python server"
)

# Custom target to install Python dependencies
add_custom_target(install-deps
    COMMAND pip3 install -r requirements.txt
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Installing Python dependencies"
)