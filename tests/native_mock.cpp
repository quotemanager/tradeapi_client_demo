// Mock-only cdecl DLL. No sockets, files, accounts or real client interactions.
#include <cstdint>
#include <cstring>
#include <string>
static thread_local unsigned request_count=0;
static thread_local std::string cached;
extern "C" {
__declspec(dllexport) int __cdecl TradeApi_Initialize(const char*,const char*) {
    request_count=0; cached.clear(); return 0;
}
__declspec(dllexport) int __cdecl TradeApi_GetLastResponse(char* output,uint32_t capacity,uint32_t* required) {
    *required=(uint32_t)cached.size()+1;
    if(capacity<*required) return 3;
    std::memcpy(output,cached.c_str(),*required); return 0;
}
__declspec(dllexport) int __cdecl TradeApi_Call(const char*,const char*,const char*,char* output,uint32_t capacity,uint32_t* required) {
    ++request_count;
    // Deliberately too large for the initial 64 KiB buffer, with non-200 HTTP.
    cached="{\"ok\":false,\"request_count\":"+std::to_string(request_count)+",\"padding\":\""+std::string(70000,'x')+"\"}";
    int result=TradeApi_GetLastResponse(output,capacity,required);
    return result==3 ? 3 : 4;
}
__declspec(dllexport) uint32_t __cdecl TradeApi_GetLastHttpStatus(void) { return 409; }
}
