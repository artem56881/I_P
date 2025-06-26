import socket
import struct
import threading
import time
import pickle
import os

CACHE_FILE = "dns_cache.pkl"
CACHE_CLEAN_INTERVAL = 60
DNS_PORT = 53
UPSTREAM_DNS = ("8.8.8.8", 53)

running = True

cache = {}  # (name, type) -> (response_bytes, expire_time)


def load_cache():
    global cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            raw = pickle.load(f)
            now = time.time()
            cache = {
                k: v for k, v in raw.items()
                if v[1] > now
            }


def save_cache():
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(cache, f)


def clean_cache():
    while True:
        time.sleep(CACHE_CLEAN_INTERVAL)
        now = time.time()
        expired = [k for k, v in cache.items() if v[1] <= now]
        for k in expired:
            del cache[k]


def parse_dns_name(data, offset):
    labels = []
    while True:
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if (length & 0xC0) == 0xC0:
            pointer = struct.unpack("!H", data[offset:offset+2])[0] & 0x3FFF
            sub_labels, _ = parse_dns_name(data, pointer)
            labels.extend(sub_labels)
            offset += 2
            break
        else:
            labels.append(data[offset+1:offset+1+length].decode())
            offset += 1 + length
    return labels, offset


def get_ttl_and_cache_rrs(data):
    rrs = []
    _, _, qdcount, ancount, nscount, arcount = struct.unpack("!6H", data[:12])
    offset = 12

    for _ in range(qdcount):
        _, offset = parse_dns_name(data, offset)
        offset += 4

    total_rrs = ancount + nscount + arcount
    for _ in range(total_rrs):
        name, offset = parse_dns_name(data, offset)
        rtype, rclass, ttl, rdlength = struct.unpack("!HHIH", data[offset:offset+10])
        offset += 10
        offset += rdlength
        rrs.append(((tuple(name), rtype), ttl))
    return rrs


def forward_to_upstream(query):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3)
        try:
            sock.sendto(query, UPSTREAM_DNS)
            response, _ = sock.recvfrom(4096)
            return response
        except socket.timeout:
            return None


def handle_request(data, addr, server_sock):
    try:
        transaction_id = data[:2]
        qname, offset = parse_dns_name(data, 12)
        qtype, qclass = struct.unpack("!HH", data[offset:offset+4])
        key = (tuple(qname), qtype)

        # поиск в кэше
        if key in cache and cache[key][1] > time.time():
            response = transaction_id + cache[key][0][2:]
            server_sock.sendto(response, addr)
            return

        upstream_response = forward_to_upstream(data)
        if not upstream_response:
            return

        rrs = get_ttl_and_cache_rrs(upstream_response)
        now = time.time()
        for (name, typ), ttl in rrs:
            cache[(name, typ)] = (upstream_response, now + ttl)
        server_sock.sendto(upstream_response, addr)

    except Exception as e:
        print(e)

def console_listener():
    global running
    while True:
        cmd = input()
        if cmd.strip().lower() == "exit":
            print("Завершение работы")
            running = False
            break


def run_dns_server():
    load_cache()
    threading.Thread(target=clean_cache, daemon=True).start() # поток для периодической очистки кэша
    threading.Thread(target=console_listener, daemon=True).start() # поток для чтения команд из консоли (exit)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("0.0.0.0", DNS_PORT))
        print("DNS сервер запущен на порту", DNS_PORT)
        try:
            while running:
                sock.settimeout(1.0)
                try:
                    data, addr = sock.recvfrom(512)
                    threading.Thread(target=handle_request, args=(data, addr, sock)).start() # основной поток функционала dns сервера
                except socket.timeout:
                    continue
        finally:
            print("Сохранение кэша")
            save_cache()

if __name__ == "__main__":
    run_dns_server()
