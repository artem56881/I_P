import subprocess
import re
from ipwhois import IPWhois
import socket


def check_internet_connection():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False


def run_traceroute(target):
    try:
        command = ["traceroute", "-n", target]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        return re.findall(r"\d+\.\d+\.\d+\.\d+", result.stdout)
    except subprocess.TimeoutExpired:
        print("Ошибка: Превышено время ожидания.")
    except Exception as e:
        print(f"Ошибка: {e}")
    return []


def _get_ip_info(ip: str) -> dict:
    ip_info = {'ip': ip}
    try:
        res = IPWhois(ip).lookup_rdap()
    except:
        res = {}
    ip_info['asn'] = res.get('asn') or "---"
    ip_info['country'] = res.get('asn_country_code') or "---"
    ip_info['provider'] = res.get('network', {}).get('name') or "---"
    return ip_info


def main():
    if not check_internet_connection():
        print("Нет доступа в интернет.")
        return

    target = input("Введите доменное имя или IP-адрес: ")
    try:
        socket.gethostbyname(target)
    except socket.gaierror:
        print("Не удалось преобразовать доменное имя в IP-адрес.")
        return
    except Exception as e:
        print(f"Ошибка сети: {e}")
        return

    ips = run_traceroute(target)

    print("№   | IP адрес        | AS     | Страна  | Провайдер ")
    print("-" * 60)

    for i, ip in enumerate(ips, start=1):
        ip_info = _get_ip_info(ip)
        print(f"{i:<3} | {ip:<15} | {ip_info['asn']:<6} | {ip_info['country']:<7} | {ip_info['provider']}")


if __name__ == "__main__":
    main()