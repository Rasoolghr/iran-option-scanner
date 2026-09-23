import subprocess

urls = [
    "https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/%D8%AE%D9%88%D8%AF%D8%B1%D9%88",
    "https://webgw.tse.ir/InstrumentProvider/api/v1/MarketWatch/MarketWatchOption/fa",
]

print("====================================")
print("TSETMC IPV4 CONNECTION TEST")
print("====================================")

for url in urls:
    print("\n------------------------------------")
    print("URL:", url)

    cmd = [
        "curl",
        "-4",
        "-L",
        "--connect-timeout", "10",
        "--max-time", "20",
        "-A", "Mozilla/5.0",
        "-H", "Accept: application/json",
        "-sS",
        "-w", "\nHTTP_STATUS:%{http_code}\nREMOTE_IP:%{remote_ip}\n",
        url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        print("OUTPUT:")
        print(result.stdout[:5000])

        if result.stderr:
            print("STDERR:")
            print(result.stderr[:2000])

    except Exception as e:
        print("ERROR:", repr(e))

print("\n====================================")
print("TEST FINISHED")
print("====================================")