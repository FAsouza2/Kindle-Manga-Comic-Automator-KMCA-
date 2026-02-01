#!/usr/bin/env python3
"""
Kindle Manga Comic Automator (KMCA)
Converte arquivos de manga/comic (PDF, MOBI, EPUB, CBZ, CBR) para CBZ otimizado para Kindle
"""

import os
import sys
import shutil
import zipfile
import rarfile
from pathlib import Path
from typing import List, Tuple
import fitz  # PyMuPDF
from ebooklib import epub
import io
from PIL import Image


class MangaConverter:
    """Conversor de manga/comic para formato CBZ"""

    SUPPORTED_FORMATS = {'.pdf', '.mobi', '.epub', '.cbz', '.cbr', '.azw3'}
    SOURCE_FOLDER = "Fonte"

    def __init__(self, working_dir: str = None):
        """Inicializa o conversor

        Args:
            working_dir: Diretório de trabalho (padrão: diretório atual)
        """
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.source_path = self.working_dir / self.SOURCE_FOLDER

    def run(self):
        """Executa o processo completo de conversão"""
        print("=" * 60)
        print("Kindle Manga Comic Automator (KMCA)")
        print("=" * 60)

        # Identifica arquivos para converter
        files_to_convert = self.identify_files()

        if not files_to_convert:
            print("\nNenhum arquivo suportado encontrado na pasta.")
            print(f"Formatos suportados: {', '.join(self.SUPPORTED_FORMATS)}")
            return

        print(f"\nEncontrados {len(files_to_convert)} arquivo(s) para converter:")
        for file in files_to_convert:
            print(f"  - {file.name}")

        # Cria pasta Fonte se não existir
        self.source_path.mkdir(exist_ok=True)

        # Processa cada arquivo
        for idx, file_path in enumerate(files_to_convert, 1):
            print(f"\n[{idx}/{len(files_to_convert)}] Processando: {file_path.name}")
            try:
                self.process_file(file_path)
                print(f"✓ Concluído: {file_path.stem}.cbz")
            except Exception as e:
                print(f"✗ Erro ao processar {file_path.name}: {str(e)}")
                continue

        print("\n" + "=" * 60)
        print("Conversão finalizada!")
        print("=" * 60)

    def identify_files(self) -> List[Path]:
        """Identifica todos os arquivos suportados na pasta

        Returns:
            Lista de caminhos de arquivos para converter
        """
        files = []
        for item in self.working_dir.iterdir():
            if item.is_file() and item.suffix.lower() in self.SUPPORTED_FORMATS:
                files.append(item)
        return sorted(files)

    def process_file(self, file_path: Path):
        """Processa um arquivo individual

        Args:
            file_path: Caminho do arquivo a processar
        """
        # Cria pasta específica para este manga
        manga_name = file_path.stem
        manga_folder = self.source_path / manga_name
        manga_folder.mkdir(exist_ok=True)

        # Move arquivo original para a pasta
        dest_file = manga_folder / file_path.name
        shutil.move(str(file_path), str(dest_file))
        print(f"  Arquivo movido para: {manga_folder.relative_to(self.working_dir)}")

        # Extrai imagens baseado no tipo de arquivo
        print("  Extraindo imagens...")
        extension = dest_file.suffix.lower()

        if extension == '.pdf':
            images = self.extract_from_pdf(dest_file, manga_folder)
        elif extension in {'.mobi', '.azw3'}:
            images = self.extract_from_mobi(dest_file, manga_folder)
        elif extension == '.epub':
            images = self.extract_from_epub(dest_file, manga_folder)
        elif extension == '.cbz':
            images = self.extract_from_cbz(dest_file, manga_folder)
        elif extension == '.cbr':
            images = self.extract_from_cbr(dest_file, manga_folder)
        else:
            raise ValueError(f"Formato não suportado: {extension}")

        print(f"  {len(images)} imagens extraídas")

        # Cria arquivo CBZ
        print("  Criando arquivo CBZ...")
        cbz_path = self.working_dir / f"{manga_name}.cbz"
        self.create_cbz(images, cbz_path)
        print(f"  CBZ criado: {cbz_path.name}")

    def extract_from_pdf(self, pdf_path: Path, output_folder: Path) -> List[Path]:
        """Extrai imagens de um arquivo PDF

        Args:
            pdf_path: Caminho do arquivo PDF
            output_folder: Pasta onde salvar as imagens

        Returns:
            Lista de caminhos das imagens extraídas
        """
        images = []
        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()

            # Se a página contém imagens, extrai a primeira (geralmente a imagem da página)
            if image_list:
                xref = image_list[0][0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Salva imagem
                image_name = f"{page_num + 1:03d}.{image_ext}"
                image_path = output_folder / image_name

                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)

                images.append(image_path)
            else:
                # Se não há imagem embutida, renderiza a página como imagem
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolution
                image_name = f"{page_num + 1:03d}.png"
                image_path = output_folder / image_name
                pix.save(str(image_path))
                images.append(image_path)

        doc.close()
        return images

    def extract_from_mobi(self, mobi_path: Path, output_folder: Path) -> List[Path]:
        """Extrai imagens de um arquivo MOBI/AZW3

        Args:
            mobi_path: Caminho do arquivo MOBI
            output_folder: Pasta onde salvar as imagens

        Returns:
            Lista de caminhos das imagens extraídas
        """
        # MOBI é mais complicado, usa PyMuPDF que também suporta
        images = []
        doc = fitz.open(mobi_path)

        # Extrai todas as imagens do documento
        img_count = 0
        for page_num in range(len(doc)):
            page = doc[page_num]

            # Renderiza a página como imagem (MOBI geralmente já é imagem)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_name = f"{page_num + 1:03d}.png"
            image_path = output_folder / image_name
            pix.save(str(image_path))
            images.append(image_path)
            img_count += 1

        doc.close()
        return images

    def extract_from_epub(self, epub_path: Path, output_folder: Path) -> List[Path]:
        """Extrai imagens de um arquivo EPUB

        Args:
            epub_path: Caminho do arquivo EPUB
            output_folder: Pasta onde salvar as imagens

        Returns:
            Lista de caminhos das imagens extraídas
        """
        images = []
        book = epub.read_epub(str(epub_path))

        # Extrai todas as imagens
        img_items = [item for item in book.get_items() if item.get_type() == 9]  # ITEM_IMAGE

        for idx, img_item in enumerate(img_items, 1):
            # Determina extensão da imagem
            img_name = img_item.get_name()
            img_ext = Path(img_name).suffix or '.jpg'

            # Salva imagem
            image_name = f"{idx:03d}{img_ext}"
            image_path = output_folder / image_name

            with open(image_path, "wb") as img_file:
                img_file.write(img_item.get_content())

            images.append(image_path)

        return images

    def extract_from_cbz(self, cbz_path: Path, output_folder: Path) -> List[Path]:
        """Extrai imagens de um arquivo CBZ (ZIP)

        Args:
            cbz_path: Caminho do arquivo CBZ
            output_folder: Pasta onde salvar as imagens

        Returns:
            Lista de caminhos das imagens extraídas
        """
        images = []

        with zipfile.ZipFile(cbz_path, 'r') as zip_ref:
            # Lista todos os arquivos de imagem
            img_files = [f for f in zip_ref.namelist()
                        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))]
            img_files.sort()

            # Extrai cada imagem
            for idx, img_file in enumerate(img_files, 1):
                img_data = zip_ref.read(img_file)
                img_ext = Path(img_file).suffix

                image_name = f"{idx:03d}{img_ext}"
                image_path = output_folder / image_name

                with open(image_path, "wb") as img:
                    img.write(img_data)

                images.append(image_path)

        return images

    def extract_from_cbr(self, cbr_path: Path, output_folder: Path) -> List[Path]:
        """Extrai imagens de um arquivo CBR (RAR)

        Args:
            cbr_path: Caminho do arquivo CBR
            output_folder: Pasta onde salvar as imagens

        Returns:
            Lista de caminhos das imagens extraídas
        """
        images = []

        with rarfile.RarFile(cbr_path, 'r') as rar_ref:
            # Lista todos os arquivos de imagem
            img_files = [f for f in rar_ref.namelist()
                        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))]
            img_files.sort()

            # Extrai cada imagem
            for idx, img_file in enumerate(img_files, 1):
                img_data = rar_ref.read(img_file)
                img_ext = Path(img_file).suffix

                image_name = f"{idx:03d}{img_ext}"
                image_path = output_folder / image_name

                with open(image_path, "wb") as img:
                    img.write(img_data)

                images.append(image_path)

        return images

    def create_cbz(self, image_paths: List[Path], output_path: Path):
        """Cria um arquivo CBZ a partir de uma lista de imagens

        Args:
            image_paths: Lista de caminhos das imagens
            output_path: Caminho do arquivo CBZ de saída
        """
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as cbz:
            for img_path in sorted(image_paths):
                cbz.write(img_path, img_path.name)


def main():
    """Função principal"""
    try:
        converter = MangaConverter()
        converter.run()
    except KeyboardInterrupt:
        print("\n\nProcesso interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\nErro fatal: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
