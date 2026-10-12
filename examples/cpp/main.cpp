// Public local API consumer. No broker client code, injection or automatic retry.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winhttp.h>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <regex>
#include <stdexcept>
#include <string>
#include <vector>
using Json = nlohmann::json;

static std::string env(const std::string& key, const std::string& fallback="") {
    const char* value=std::getenv(key.c_str()); return value ? value : fallback;
}
static std::string trim(std::string value) {
    const auto start=value.find_first_not_of(" \t\r\n"), end=value.find_last_not_of(" \t\r\n");
    return start==std::string::npos ? "" : value.substr(start,end-start+1);
}
static std::wstring wide(const std::string& value) {
    int size=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,value.data(),(int)value.size(),nullptr,0);
    if(size<=0 && !value.empty()) throw std::runtime_error("Invalid UTF-8");
    std::wstring result(size,L'\0');
    if(size) MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,value.data(),(int)value.size(),result.data(),size);
    return result;
}
static Json read_object(const std::string& file) {
    auto path=std::filesystem::u8path(file);
    if(std::filesystem::file_size(path)>65536) throw std::runtime_error("JSON file exceeds 64 KiB");
    std::ifstream stream(path,std::ios::binary);
    if(!stream) throw std::runtime_error("Could not read JSON file");
    auto result=Json::parse(stream);
    if(!result.is_object()) throw std::runtime_error("Expected JSON object");
    return result;
}
struct HttpHandle {
    HINTERNET value;
    explicit HttpHandle(HINTERNET handle): value(handle) { if(!value) throw std::runtime_error("WinHTTP open failed"); }
    ~HttpHandle() { WinHttpCloseHandle(value); }
    HttpHandle(const HttpHandle&)=delete;
};
static void checked(BOOL value) { if(!value) throw std::runtime_error("WinHTTP error="+std::to_string(GetLastError())+"; do not resubmit"); }

static std::pair<unsigned,std::string> http_call(unsigned port,const std::string& token,
        const std::string& method,const std::string& path,const Json& body) {
    HttpHandle session(WinHttpOpen(L"TradeApi public example/1.0",WINHTTP_ACCESS_TYPE_NO_PROXY,WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,0));
    checked(WinHttpSetTimeouts(session.value,90000,90000,90000,90000));
    HttpHandle connection(WinHttpConnect(session.value,L"127.0.0.1",(INTERNET_PORT)port,0));
    HttpHandle request(WinHttpOpenRequest(connection.value,wide(method).c_str(),wide(path).c_str(),nullptr,WINHTTP_NO_REFERER,WINHTTP_DEFAULT_ACCEPT_TYPES,0));
    DWORD disabled=WINHTTP_DISABLE_REDIRECTS|WINHTTP_DISABLE_COOKIES|WINHTTP_DISABLE_AUTHENTICATION;
    checked(WinHttpSetOption(request.value,WINHTTP_OPTION_DISABLE_FEATURE,&disabled,sizeof(disabled)));
    std::wstring headers=L"Content-Type: application/json\r\n";
    if(!token.empty()) headers+=L"Authorization: Bearer "+wide(token)+L"\r\n";
    std::string data=body.is_null() ? "" : body.dump();
    checked(WinHttpSendRequest(request.value,headers.c_str(),(DWORD)headers.size(),data.empty()?WINHTTP_NO_REQUEST_DATA:(void*)data.data(),(DWORD)data.size(),(DWORD)data.size(),0));
    checked(WinHttpReceiveResponse(request.value,nullptr));
    DWORD status=0,size=sizeof(status);
    checked(WinHttpQueryHeaders(request.value,WINHTTP_QUERY_STATUS_CODE|WINHTTP_QUERY_FLAG_NUMBER,WINHTTP_HEADER_NAME_BY_INDEX,&status,&size,WINHTTP_NO_HEADER_INDEX));
    std::string raw;
    for(;;) {
        DWORD available=0; checked(WinHttpQueryDataAvailable(request.value,&available));
        if(!available) break;
        if(raw.size()+available>16*1024*1024) throw std::runtime_error("Response exceeds 16 MiB");
        std::vector<char> chunk(available); DWORD received=0;
        checked(WinHttpReadData(request.value,chunk.data(),available,&received));
        if(!received) throw std::runtime_error("Interrupted response; do not resubmit");
        raw.append(chunk.data(),received);
    }
    return {status,raw};
}

static std::pair<unsigned,std::string> dll_call(const std::string& product,const std::string& url,
        const std::string& token,const std::string& method,const std::string& path,const Json& body) {
    auto name=product=="tdx" ? "TRADEAPI_TDX_HOME" : "TRADEAPI_THS_HOME";
    auto home=env(name); if(home.empty()) throw std::runtime_error(std::string("Set ")+name);
    auto dll_path=std::filesystem::absolute(std::filesystem::u8path(home)/"build"/(sizeof(void*)==8?"x64":"x86")/("tradeapi_"+product+".dll"));
    HMODULE library=LoadLibraryExW(dll_path.c_str(),nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if(!library) throw std::runtime_error("DLL load failed; check package path and calling process bitness");
    struct LibraryScope { HMODULE value; ~LibraryScope(){FreeLibrary(value);} } scope{library};
    using Init=int(__cdecl*)(const char*,const char*);
    using Call=int(__cdecl*)(const char*,const char*,const char*,char*,uint32_t,uint32_t*);
    using Cached=int(__cdecl*)(char*,uint32_t,uint32_t*);
    using Status=uint32_t(__cdecl*)();
    auto init=(Init)GetProcAddress(library,"TradeApi_Initialize");
    auto call=(Call)GetProcAddress(library,"TradeApi_Call");
    auto cached=(Cached)GetProcAddress(library,"TradeApi_GetLastResponse");
    auto status=(Status)GetProcAddress(library,"TradeApi_GetLastHttpStatus");
    if(!init||!call||!cached||!status||init(url.c_str(),token.c_str())) throw std::runtime_error("DLL initialization failed");
    std::vector<char> output(65536); uint32_t required=0;
    std::string data=body.is_null()?"":body.dump();
    int code=call(method.c_str(),path.c_str(),body.is_null()?nullptr:data.c_str(),output.data(),(uint32_t)output.size(),&required);
    if(code==3) {
        if(!required||required>16*1024*1024+1) throw std::runtime_error("Invalid DLL output size");
        output.resize(required);
        code=cached(output.data(),(uint32_t)output.size(),&required); // Same thread; copy only, nothing resent.
    }
    if(code!=0&&code!=4) throw std::runtime_error("DLL error="+std::to_string(code)+"; do not resubmit");
    auto nul=std::find(output.begin(),output.end(),'\0');
    if(nul==output.end()) throw std::runtime_error("DLL response has no terminator");
    return {status(),std::string(output.begin(),nul)};
}

int main(int argc,char** argv) {
    SetConsoleOutputCP(CP_UTF8);
    try {
        std::vector<std::string> args; bool execute=false,dll=false;
        for(int i=1;i<argc;i++) { std::string a=argv[i]; if(a=="--execute") execute=true; else if(a=="--dll") dll=true; else args.push_back(a); }
        if(args.empty()||args.size()>3) throw std::runtime_error("Usage: demo PRODUCT [COMMAND [VALUE]] [--execute] [--dll]");
        std::string product=args[0], command=args.size()>1?args[1]:"query", value=args.size()>2?args[2]:"";
        if(product!="tdx"&&product!="ths") throw std::runtime_error("PRODUCT must be tdx or ths");
        Json profile=read_object("config/api-contract.json").at(product), spec, body;
        if(command=="query") spec={{"method","GET"},{"path",profile.at("queries").at(value.empty()?"funds":value)},{"input","none"},{"live",false}};
        else spec=profile.at("commands").at(command);
        std::string input=spec.at("input"),endpoint=spec.at("path"),method=spec.at("method");
        if(input=="file") body=read_object(value);
        else if(input.rfind("id-",0)==0) {
            if(!std::regex_match(value,std::regex("[A-Za-z0-9_-]{1,128}"))) throw std::runtime_error("Pass an existing action/preview ID");
            if(input=="id-path") endpoint+=value; else body={{"preview_id",value}};
        } else if(!value.empty()&&command!="query") throw std::runtime_error("This command takes no VALUE");
        if(spec.at("live").get<bool>()&&!execute) {
            std::cout<<Json({{"dry_run",true},{"method",method},{"path",endpoint},{"body",body},{"note","Nothing sent. --execute submits ONE REAL action."}}).dump(2)<<"\n"; return 0;
        }
        std::string url=env(profile.at("url_env"),profile.at("base_url"));
        while(!url.empty()&&url.back()=='/') url.pop_back();
        std::smatch match;
        if(!std::regex_match(url,match,std::regex("http://127\\.0\\.0\\.1:([0-9]{1,5})"))) throw std::runtime_error("URL must be http://127.0.0.1:<port>");
        unsigned port=std::stoul(match[1]); if(!port||port>65535) throw std::runtime_error("Invalid port");
        std::string token=trim(env(profile.at("token_env")));
        if(endpoint!="/health"&&!std::regex_match(token,std::regex("[A-Za-z0-9_-]{32,256}"))) throw std::runtime_error("Set "+profile.at("token_env").get<std::string>());
        auto [status,raw]=dll?dll_call(product,url,token,method,endpoint,body):http_call(port,token,method,endpoint,body);
        auto result=Json::parse(raw); if(!result.is_object()) throw std::runtime_error("Response is not an object");
        std::cout<<"HTTP "<<status<<"\n"<<result.dump(2)<<"\n";
        return status==200&&(!result.contains("ok")||result["ok"]!=false)?0:1;
    } catch(const std::exception& error) {
        std::cerr<<error.what()<<"\nNo automatic retry. Reconcile any submitted action in the official client.\n"; return 1;
    }
}
