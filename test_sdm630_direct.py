#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script de diagnóstico para testar conexão direta com SDM630 via Modbus TCP."""

import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul')
    sys.stdout.reconfigure(encoding='utf-8')

from app.connectors.modbus import ModbusTCPClient
from app.connectors.eastron_sdm630 import read_sdm630_metrics


def test_connection():
    """Testa conexão TCP com o gateway EW11."""
    host = "10.0.0.109"
    port = 8899
    slave_id = 1
    timeout = 3.0

    print(f"=== Teste de Conexão Modbus TCP ===")
    print(f"Host: {host}:{port}")
    print(f"Slave ID: {slave_id}")
    print(f"Timeout: {timeout}s")
    print("-" * 50)

    try:
        print("\n[1/3] Conectando ao gateway EW11...")
        with ModbusTCPClient(host=host, port=port, slave_id=slave_id, timeout=timeout) as client:
            print("[OK] Conexao estabelecida!")

            print("\n[2/3] Testando leitura de registradores básicos (0x0000-0x0005)...")
            test_regs = client.read_input_registers(address=0x0000, count=6)
            print(f"[OK] Registradores lidos: {test_regs}")

            print("\n[3/3] Lendo métricas completas do SDM630...")
            metrics = read_sdm630_metrics(client, base_address=0)

            print("\n" + "=" * 50)
            print("METRICAS DO SDM630")
            print("=" * 50)

            print("\nTENSOES:")
            print(f"  L1: {metrics['voltage_l1']:.2f} V")
            print(f"  L2: {metrics['voltage_l2']:.2f} V")
            print(f"  L3: {metrics['voltage_l3']:.2f} V")
            print(f"  Media: {metrics['voltage_avg']:.2f} V")

            print("\nCORRENTES:")
            print(f"  L1: {metrics['current_l1']:.3f} A")
            print(f"  L2: {metrics['current_l2']:.3f} A")
            print(f"  L3: {metrics['current_l3']:.3f} A")
            print(f"  Total: {metrics['current_total']:.3f} A")

            print("\nPOTENCIAS:")
            print(f"  L1: {metrics['power_l1']:.2f} W")
            print(f"  L2: {metrics['power_l2']:.2f} W")
            print(f"  L3: {metrics['power_l3']:.2f} W")
            print(f"  Total: {metrics['power_total']:.2f} W")

            print("\nOUTROS:")
            print(f"  Frequencia: {metrics['frequency']:.2f} Hz")
            print(f"  Energia: {metrics['energy_kwh']:.3f} kWh")
            print(f"  Fator Potencia: {metrics['power_factor']:.3f}")

            print("\n[OK] TESTE CONCLUIDO COM SUCESSO!")
            return True

    except Exception as e:
        print(f"\n[ERRO] {type(e).__name__}: {e}")
        print("\nPossiveis causas:")
        print("  1. Gateway EW11 nao esta acessivel em 10.0.0.109:8899")
        print("  2. SDM630 nao esta respondendo (verificar cabeamento RS485)")
        print("  3. Slave ID incorreto (atual: 1)")
        print("  4. Firewall bloqueando porta 8899")
        print("\nSugestoes:")
        print("  - Ping no gateway: ping 10.0.0.109")
        print("  - Testar porta: telnet 10.0.0.109 8899")
        print("  - Verificar LED do EW11 (deve piscar durante comunicacao)")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
