"""Driver para medidor Eastron SDM630-Modbus-MID (trifásico)."""
from __future__ import annotations
from typing import Dict, Any, Union


def read_sdm630_metrics(client: Union[Any, Any], base_address: int = 0) -> Dict[str, Any]:
    """
    Lê métricas do medidor trifásico Eastron SDM630-Modbus-MID.

    Registradores principais (Input Registers, função 0x04):
    - 0x0000-0x0001: Tensão Fase 1 (V) - Float32
    - 0x0002-0x0003: Tensão Fase 2 (V) - Float32
    - 0x0004-0x0005: Tensão Fase 3 (V) - Float32
    - 0x0006-0x0007: Corrente Fase 1 (A) - Float32
    - 0x0008-0x0009: Corrente Fase 2 (A) - Float32
    - 0x000A-0x000B: Corrente Fase 3 (A) - Float32
    - 0x000C-0x000D: Potência Ativa Fase 1 (W) - Float32
    - 0x000E-0x000F: Potência Ativa Fase 2 (W) - Float32
    - 0x0010-0x0011: Potência Ativa Fase 3 (W) - Float32
    - 0x0034-0x0035: Potência Ativa Total (W) - Float32
    - 0x0046-0x0047: Frequência (Hz) - Float32
    - 0x0048-0x0049: Energia Ativa Total (kWh) - Float32
    - 0x001E-0x001F: Fator de Potência Total - Float32

    Nota: SDM630 usa Float32 IEEE754 (2 registradores por valor)
    """

    # Ler bloco principal (tensões, correntes, potências)
    regs_main = client.read_input_registers(address=0x0000, count=36)

    # Ler potência total
    regs_power_total = client.read_input_registers(address=0x0034, count=2)

    # Ler frequência e energia
    regs_freq_energy = client.read_input_registers(address=0x0046, count=4)

    # Ler fator de potência
    regs_pf = client.read_input_registers(address=0x001E, count=2)

    def regs_to_float32(reg_high: int, reg_low: int) -> float:
        """Converte 2 registradores em Float32 IEEE754 (Big Endian)."""
        import struct
        # Combinar registradores (Big Endian: high word primeiro)
        combined = (reg_high << 16) | reg_low
        # Converter para float
        return struct.unpack('>f', struct.pack('>I', combined))[0]

    # Extrair valores
    v1 = regs_to_float32(regs_main[0], regs_main[1])
    v2 = regs_to_float32(regs_main[2], regs_main[3])
    v3 = regs_to_float32(regs_main[4], regs_main[5])

    i1 = regs_to_float32(regs_main[6], regs_main[7])
    i2 = regs_to_float32(regs_main[8], regs_main[9])
    i3 = regs_to_float32(regs_main[10], regs_main[11])

    p1 = regs_to_float32(regs_main[12], regs_main[13])
    p2 = regs_to_float32(regs_main[14], regs_main[15])
    p3 = regs_to_float32(regs_main[16], regs_main[17])

    power_total = regs_to_float32(regs_power_total[0], regs_power_total[1])
    frequency = regs_to_float32(regs_freq_energy[0], regs_freq_energy[1])
    energy_kwh = regs_to_float32(regs_freq_energy[2], regs_freq_energy[3])
    power_factor = regs_to_float32(regs_pf[0], regs_pf[1])

    from app.services.flow_split import apply_import_export_split

    metrics = {
        # Tensões por fase
        "voltage_l1": v1,
        "voltage_l2": v2,
        "voltage_l3": v3,
        "voltage_avg": (v1 + v2 + v3) / 3,

        # Correntes por fase (sinal negativo = injeção solar — premissa do projeto)
        "current_l1": i1,
        "current_l2": i2,
        "current_l3": i3,
        "current_total": i1 + i2 + i3,

        # Potências por fase (negativo = injeção)
        "power_l1": p1,
        "power_l2": p2,
        "power_l3": p3,
        "power_total": power_total,

        # Outros
        "frequency": frequency,
        "energy_kwh": energy_kwh,
        "energy_wh": energy_kwh * 1000,  # Para compatibilidade
        "power_factor": power_factor,

        "_raw_main": regs_main,
        "_device": "SDM630-Modbus-MID"
    }
    return apply_import_export_split(metrics)
