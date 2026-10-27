#!/usr/bin/env python3
"""Resume mudancas de fase e ultimos sinais fatais nos logs do SMW-R36S."""
from pathlib import Path
import sys

if len(sys.argv) < 2:
    raise SystemExit('Uso: python3 tools/analisar_log.py r36s-diagnostic.log [run-*.log]')
for name in sys.argv[1:]:
    path = Path(name)
    if not path.is_file():
        print('Arquivo inexistente:', name)
        continue
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    changes = [(i, line) for i, line in enumerate(lines) if '[STATE_CHANGE]' in line]
    failures = [(i, line) for i, line in enumerate(lines)
                if '[FATAL_SIGNAL]' in line or 'game_exit_status=' in line]
    mismatches = [(i, line) for i, line in enumerate(lines) if '[DIVERGENCE]' in line]
    print('\n==', path, '==\nLinhas:', len(lines),
          'Mudancas:', len(changes), 'Divergencias:', len(mismatches),
          'Falhas/saidas:', len(failures))
    for i, line in changes[-8:]:
        print(f'Transicao {i+1}: {line}')
    for i, line in failures[-5:]:
        print(f'Falha/saida {i+1}: {line}')
    print('Ultimas linhas:')
    for line in lines[-12:]:
        print(line)
