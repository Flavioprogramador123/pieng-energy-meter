#!/usr/bin/env python3
"""
Script de teste para PZEM-004T
Testa a comunicação Modbus com o dispositivo real
"""

import minimalmodbus
import time
import sys

def test_pzem004t():
    """Testa a comunicação com PZEM-004T"""
    try:
        print("=== Teste PZEM-004T ===")
        print("Configurando instrumento Modbus...")
        
        # Configurar instrumento Modbus
        instrument = minimalmodbus.Instrument('COM3', 1)  # porta COM3, slave ID 1
        instrument.serial.baudrate = 9600
        instrument.serial.timeout = 0.5
        instrument.serial.bytesize = 8
        instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
        instrument.serial.stopbits = 1
        
        print("Tentando conectar ao PZEM-004T...")
        
        # Teste de conexão básica
        try:
            # Ler registros do PZEM-004T conforme documentação
            print("Lendo registros do PZEM-004T...")
            
            # Registro 0: Tensão (V) - escala 0.1V
            voltage_raw = instrument.read_register(0, 1)
            voltage = voltage_raw * 0.1
            
            # Registro 1: Corrente (A) - escala 0.001A  
            current_raw = instrument.read_register(1, 2)
            current = current_raw * 0.001
            
            # Registro 3: Potência (W) - escala 0.1W
            power_raw = instrument.read_register(3, 0)
            power = power_raw * 0.1
            
            # Registro 5: Energia (Wh) - escala 1Wh
            energy_raw = instrument.read_register(5, 0)
            energy = energy_raw * 1
            
            # Registro 7: Frequência (Hz) - escala 0.1Hz
            frequency_raw = instrument.read_register(7, 1)
            frequency = frequency_raw * 0.1
            
            # Registro 8: Fator de potência - escala 0.01
            pf_raw = instrument.read_register(8, 2)
            power_factor = pf_raw * 0.01
            
            print("\n=== DADOS LIDOS DO PZEM-004T ===")
            print(f"Tensão: {voltage:.1f} V")
            print(f"Corrente: {current:.3f} A")
            print(f"Potência: {power:.1f} W")
            print(f"Energia: {energy:.0f} Wh")
            print(f"Frequência: {frequency:.1f} Hz")
            print(f"Fator de Potência: {power_factor:.2f}")
            print("\n✅ Leitura bem-sucedida!")
            
            return True
            
        except Exception as read_error:
            print(f"❌ Erro na leitura: {read_error}")
            return False
            
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        print("\n💡 Possíveis soluções:")
        print("   1. Verifique se o PZEM-004T está conectado na COM3")
        print("   2. Verifique se o cabo USB está funcionando")
        print("   3. Verifique se o driver Prolific está instalado")
        print("   4. Feche outros programas que possam estar usando a porta")
        print("   5. Tente executar como administrador")
        return False

if __name__ == "__main__":
    print("Iniciando teste do PZEM-004T...")
    success = test_pzem004t()
    
    if success:
        print("\n🎉 Teste concluído com sucesso!")
        sys.exit(0)
    else:
        print("\n❌ Teste falhou!")
        sys.exit(1)


