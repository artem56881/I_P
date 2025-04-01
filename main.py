import subprocess
import re
import sys
from ipwhois import IPWhois
import socket


def check_internet_connection():
    """Проверяет наличие подключения к интернету."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False


def run_traceroute(target):
    """Запускает команду tracert/traceroute и извлекает IP-адреса."""
    try:
        command = ["tracert", target] if sys.platform == "win32" else ["traceroute", "-n", target]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        return re.findall(r"\d+\.\d+\.\d+\.\d+", result.stdout)
    except subprocess.TimeoutExpired:
        print("Ошибка: Сервер не отвечает (превышено время ожидания).")
    except FileNotFoundError:
        print("Ошибка: Команда tracert/traceroute не найдена. Убедитесь, что она установлена.")
    except Exception as e:
        print(f"Ошибка при выполнении трассировки: {e}")
    return []


def _get_ip_info(ip: str) -> dict:
    """Получает номер автономной системы (AS), страну и провайдера для IP."""
    ip_info = {'ip': ip}
    try:
        res = IPWhois(ip).lookup_rdap()
    except:
        res = {}
    ip_info['asn'] = res.get('asn') or "N/A"
    ip_info['country'] = res.get('asn_country_code') or "N/A"
    ip_info['provider'] = res.get('network', {}).get('name') or "N/A"
    return ip_info


def main():
    if not check_internet_connection():
        print("Ошибка: Нет доступа в интернет.")
        return

    target = input("Введите доменное имя или IP-адрес: ")
    try:
        socket.gethostbyname(target)
    except socket.gaierror:
        print("Ошибка: Не удалось разрешить доменное имя в IP-адрес.")
        return
    except Exception as e:
        print(f"Ошибка сети: {e}")
        return

    print("Трассировка до", target)
    ips = run_traceroute(target)

    if not ips:
        print("Ошибка: Не удалось выполнить трассировку.")
        return

    print("No | IP Address      | AS     | Country | Provider")
    print("-" * 60)

    for i, ip in enumerate(ips, start=1):
        ip_info = _get_ip_info(ip)
        print(f"{i:<3} | {ip:<15} | {ip_info['asn']:<6} | {ip_info['country']:<7} | {ip_info['provider']}")


if __name__ == "__main__":
    main()