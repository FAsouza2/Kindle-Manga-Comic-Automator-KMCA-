#!/usr/bin/env python3
"""
Wrapper para integração do manga_chapter_to_volume_converter com GUI Launcher
"""

import subprocess
import sys
from pathlib import Path


class MangaChapterVolumeConverter:
    """Wrapper para executar o conversor de capítulos para volumes via GUI"""

    def __init__(self, working_dir: str):
        """
        Inicializa o conversor

        Args:
            working_dir: Diretório de trabalho contendo os capítulos de mangá
        """
        self.working_dir = Path(working_dir)
        self.script_path = Path(__file__).parent / "manga_chapter_to_volume_converter.py"

    def run(self):
        """Executa o script de conversão"""
        print(f"Diretório de trabalho: {self.working_dir}")
        print(f"Script: {self.script_path}")
        print()
        print("=" * 70)
        print("⚠️  AVISO: Este script é DESTRUTIVO!")
        print("=" * 70)
        print()
        print("O script irá:")
        print("  1. Renomear todas as imagens dentro das pastas de capítulos")
        print("  2. Mover imagens para novas pastas de volume")
        print("  3. DELETAR as pastas de capítulos originais")
        print("  4. Criar arquivos CBZ")
        print()
        print("🔴 IMPORTANTE: Certifique-se de ter feito BACKUP antes!")
        print()
        print("Executando conversão automaticamente...")
        print("=" * 70)
        print()

        # Executa o script com --confirm
        try:
            # Usa Python do sistema
            cmd = [
                sys.executable,
                str(self.script_path),
                str(self.working_dir),
                "--confirm",
                "--verbose"
            ]

            # Executa e captura output em tempo real
            # Usa stdin=subprocess.PIPE para enviar respostas automáticas
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )

            # Envia respostas automáticas para qualquer prompt:
            # - "y" para continuar processamento de pastas válidas
            # - "y" para sobrescrever CBZ existentes
            # Fecha stdin para não ficar esperando mais input
            try:
                process.stdin.write("y\n" * 10)  # Envia múltiplos "y" para cobrir todos os prompts
                process.stdin.close()
            except:
                pass

            # Imprime output em tempo real
            for line in process.stdout:
                print(line, end='')

            # Aguarda conclusão
            return_code = process.wait()

            if return_code == 0:
                print("\n✓ Conversão concluída com sucesso!")
            else:
                print(f"\n✗ Conversão falhou com código de erro: {return_code}")
                sys.exit(return_code)

        except FileNotFoundError:
            print(f"\n✗ Erro: Script não encontrado em {self.script_path}")
            print("Certifique-se de que 'manga_chapter_to_volume_converter.py' está no mesmo diretório.")
            sys.exit(1)

        except Exception as e:
            print(f"\n✗ Erro durante execução: {e}")
            sys.exit(1)
