cmake_minimum_required(VERSION 3.20)
project(tradeapi_client_demo LANGUAGES CXX)
if(NOT WIN32)
  message(FATAL_ERROR "This example uses Windows WinHTTP / DLL loading")
endif()
include(FetchContent)
FetchContent_Declare(json
  URL https://github.com/nlohmann/json/releases/download/v3.12.0/json.tar.xz
  URL_HASH SHA256=42f6e95cad6ec532fd372391373363b62a14af6d771056dbfc86160e6dfff7aa
  DOWNLOAD_EXTRACT_TIMESTAMP TRUE)
FetchContent_MakeAvailable(json)
add_executable(tradeapi_client_demo main.cpp)
target_compile_features(tradeapi_client_demo PRIVATE cxx_std_17)
target_link_libraries(tradeapi_client_demo PRIVATE nlohmann_json::nlohmann_json winhttp)
if(MSVC)
  target_compile_options(tradeapi_client_demo PRIVATE /W4 /utf-8)
endif()
# Optional PUBLIC test fixture, not a broker component or runtime-package DLL.
option(DEMO_BUILD_TEST_FIXTURES "Build mock-only DLL for buffer handling checks" OFF)
if(DEMO_BUILD_TEST_FIXTURES)
  add_library(mock_tradeapi SHARED ../../tests/native_mock.cpp ../../tests/native_mock.def)
  set_target_properties(mock_tradeapi PROPERTIES PREFIX "")
  target_compile_features(mock_tradeapi PRIVATE cxx_std_17)
endif()
