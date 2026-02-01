# Kindle Manga Comic Automator (KMCA)

Script Python para automatizar a conversão de mangás e quadrinhos para o formato CBZ otimizado para Kindle.

## 📋 Funcionalidades

- ✅ Suporta múltiplos formatos: PDF, MOBI, EPUB, CBZ, CBR, AZW3
- ✅ Extrai imagens originais dos arquivos (sem renderização quando possível)
- ✅ Nomeia imagens sequencialmente (001.jpg, 002.jpg, etc.)
- ✅ Organiza arquivos originais em pasta "Fonte"
- ✅ Gera arquivos CBZ prontos para conversão no Kindle Comic Converter

## 🚀 Instalação

### 1. Instalar Python

Certifique-se de ter Python 3.7 ou superior instalado.

### 2. Instalar dependências

```bash
# Use python3 -m pip no macOS
python3 -m pip install -r requirements.txt

# Ou se pip3 estiver disponível
pip3 install -r requirements.txt
```

### 3. Instalar UnRAR (para arquivos CBR)

**macOS:**
```bash
brew install unrar
```

**Linux:**
```bash
sudo apt-get install unrar
```

**Windows:**
Baixe e instale o UnRAR de https://www.rarlab.com/download.htm

## 💻 Como usar

1. Coloque o script `manga_converter.py` na pasta onde estão seus arquivos de manga/quadrinhos

2. Execute o script:
```bash
# No macOS, use python3
python3 manga_converter.py
```

3. O script irá:
   - Identificar todos os arquivos suportados na pasta
   - Criar uma pasta "Fonte"
   - Para cada arquivo:
     - Criar uma subpasta com o nome do arquivo
     - Mover o arquivo original para essa subpasta
     - Extrair todas as imagens
     - Criar um arquivo CBZ na pasta raiz

## 📁 Estrutura final

```
pasta-manga/
├── manga_converter.py
├── Fonte/
│   ├── Naruto Volume 01/
│   │   ├── Naruto Volume 01.pdf    # arquivo original
│   │   ├── 001.jpg
│   │   ├── 002.jpg
│   │   └── ...
│   └── Naruto Volume 02/
│       └── ...
├── Naruto Volume 01.cbz  # pronto para converter
└── Naruto Volume 02.cbz
```

## 🔄 Próximos passos

Após gerar os arquivos CBZ:

1. Abra o **Kindle Comic Converter** (KCC)
2. Adicione os arquivos CBZ gerados
3. Configure para seu modelo de Kindle
4. Converta e transfira para o Kindle

## 🐛 Solução de problemas

### Erro: "No module named 'fitz'"
```bash
pip install PyMuPDF
```

### Erro ao processar CBR
Certifique-se de que o UnRAR está instalado corretamente.

### Imagens em ordem errada
O script nomeia as imagens na ordem em que aparecem no arquivo. Se estiverem fora de ordem, pode ser um problema do arquivo original.

## 📝 Formatos suportados

- **PDF** - Extrai imagens embutidas
- **MOBI/AZW3** - Renderiza páginas como imagens
- **EPUB** - Extrai imagens embutidas
- **CBZ** - Re-organiza e renomeia
- **CBR** - Converte para CBZ

## 🤝 Contribuições

Sinta-se livre para abrir issues ou pull requests com melhorias!

## 📄 Licença

Este projeto é de código aberto e está disponível para uso pessoal.
