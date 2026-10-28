#!/usr/bin/env python3
"""Apply a BPS1 patch to a user-owned ROM and optionally rebuild snesrev assets.

No game data or patch is committed into the repository.
"""
import argparse
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

MAX_FILE_SIZE = 64 * 1024 * 1024


class PatchError(ValueError):
    pass


def crc32(data):
    return zlib.crc32(data) & 0xffffffff


def read_number(patch, pos, end):
    value, shift = 0, 1
    while True:
        if pos >= end:
            raise PatchError('BPS truncado ao ler numero variavel')
        b = patch[pos]
        pos += 1
        value += (b & 0x7f) * shift
        if b & 0x80:
            return value, pos
        shift <<= 7
        value += shift
        if value > MAX_FILE_SIZE * 8:
            raise PatchError('Numero BPS excede limite seguro')


def apply_bps(source, patch):
    if patch[:4] != b'BPS1' or len(patch) < 19:
        raise PatchError('Arquivo nao e um patch BPS1 valido')
    expected_source_crc, expected_target_crc, expected_patch_crc = struct.unpack_from('<III', patch, len(patch) - 12)
    if crc32(patch[:-4]) != expected_patch_crc:
        raise PatchError('CRC do patch BPS invalido')
    end = len(patch) - 12
    pos = 4
    src_len, pos = read_number(patch, pos, end)
    dst_len, pos = read_number(patch, pos, end)
    meta_len, pos = read_number(patch, pos, end)
    if src_len != len(source):
        raise PatchError(f'Tamanho da ROM incorreto: patch espera {src_len}, recebeu {len(source)} (cabecalho de 512 bytes?)')
    if crc32(source) != expected_source_crc:
        raise PatchError('CRC da ROM nao corresponde ao exigido pelo patch BPS; verifique a versao original')
    if dst_len > MAX_FILE_SIZE:
        raise PatchError('ROM resultante excede limite seguro de 64 MiB')
    if meta_len > end - pos:
        raise PatchError('Metadados BPS truncados')
    pos += meta_len
    target = bytearray()
    source_relative = 0
    target_relative = 0
    while len(target) < dst_len:
        instruction, pos = read_number(patch, pos, end)
        action = instruction & 3
        length = (instruction >> 2) + 1
        if length > dst_len - len(target):
            raise PatchError('Instrucao BPS ultrapassa tamanho do destino')
        if action == 0:  # SourceRead: source at same output offset
            offset = len(target)
            if offset + length > len(source):
                raise PatchError('SourceRead fora da ROM')
            target.extend(source[offset:offset+length])
        elif action == 1:  # TargetRead: literal bytes in patch
            if pos + length > end:
                raise PatchError('TargetRead truncado')
            target.extend(patch[pos:pos+length])
            pos += length
        elif action == 2:  # SourceCopy: relative offset within source
            delta, pos = read_number(patch, pos, end)
            source_relative += -(delta >> 1) if delta & 1 else delta >> 1
            if source_relative < 0 or source_relative + length > len(source):
                raise PatchError('SourceCopy fora da ROM')
            target.extend(source[source_relative:source_relative+length])
            source_relative += length
        else:  # TargetCopy: allows overlapping copies
            delta, pos = read_number(patch, pos, end)
            target_relative += -(delta >> 1) if delta & 1 else delta >> 1
            if target_relative < 0 or target_relative >= len(target):
                raise PatchError('TargetCopy fora do destino ja escrito')
            for _ in range(length):
                if target_relative >= len(target):
                    raise PatchError('TargetCopy le alem do destino ja escrito')
                target.append(target[target_relative])
                target_relative += 1
    if pos != end:
        raise PatchError('Dados inesperados no final das instrucoes BPS')
    if crc32(target) != expected_target_crc:
        raise PatchError('CRC final da ROM modificada nao corresponde ao patch')
    return bytes(target)


def main():
    parser = argparse.ArgumentParser(description='Aplica BPS e gera assets para o SMW-R36S')
    parser.add_argument('rom', type=Path, help='ROM original, sem patches')
    parser.add_argument('patch', type=Path, help='Patch de traducao ou sprites .bps')
    parser.add_argument('--rom-out', type=Path, default=Path('smw-patched.sfc'))
    parser.add_argument('--assets-out', type=Path, default=Path('smw_assets_patched.dat'))
    parser.add_argument('--no-assets', action='store_true', help='Somente aplicar BPS, sem extrair assets')
    parser.add_argument('--without-rom-compare', action='store_true', help='Nao inserir ROM no .dat para comparar com o port')
    args = parser.parse_args()
    source = args.rom.read_bytes()
    patch = args.patch.read_bytes()
    if len(source) > MAX_FILE_SIZE or len(patch) > MAX_FILE_SIZE:
        raise PatchError('Arquivo de entrada excede 64 MiB')
    target = apply_bps(source, patch)
    args.rom_out.parent.mkdir(parents=True, exist_ok=True)
    args.rom_out.write_bytes(target)
    print(f'BPS verificado: ROM de {len(source)} -> {len(target)} bytes: {args.rom_out}')
    if not args.no_assets:
        restool = Path(__file__).resolve().parents[1] / 'assets' / 'restool.py'
        if not restool.is_file():
            raise PatchError('Nao encontrei assets/restool.py; execute no checkout do fork smw')
        with tempfile.TemporaryDirectory(prefix='smw-r36s-bps-') as directory:
            cmd = [sys.executable, str(restool), '--rom', str(args.rom_out.resolve()), '--no-hash-check']
            if args.without_rom_compare:
                cmd.append('--no-include-rom')
            subprocess.run(cmd, check=True, cwd=directory)
            assets_src = Path(directory) / 'smw_assets.dat'
            if not assets_src.is_file():
                raise PatchError('Extrator nao gerou smw_assets.dat')
            args.assets_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(assets_src, args.assets_out)
        print(f'Assets gerados: {args.assets_out} (renomeie para smw_assets.dat no R36S)')
    print('AVISO: patches ASM para SNES nao sao automaticamente convertidos para codigo C.')


if __name__ == '__main__':
    try:
        main()
    except (PatchError, OSError, subprocess.CalledProcessError) as exc:
        sys.exit(f'ERRO: {exc}')
