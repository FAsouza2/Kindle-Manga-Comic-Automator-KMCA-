#!/usr/bin/env python3
"""
GUI Launcher para Scripts Python
Interface gráfica para executar scripts Python em diretórios selecionados
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import queue
import json
import importlib
import sys
from pathlib import Path
from io import StringIO


class ScriptRegistry:
    """Gerencia o registro e carregamento de scripts disponíveis"""

    def __init__(self, config_file: str = "scripts_config.json"):
        """Inicializa o registro de scripts

        Args:
            config_file: Caminho do arquivo de configuração JSON
        """
        self.config_file = Path(config_file)
        self.scripts = []
        self.load_config()

    def load_config(self):
        """Carrega a configuração de scripts do arquivo JSON"""
        if not self.config_file.exists():
            self._create_default_config()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.scripts = config.get('scripts', [])
        except json.JSONDecodeError as e:
            messagebox.showerror(
                "Erro de Configuração",
                f"Arquivo de configuração inválido: {e}\nUsando configuração padrão."
            )
            self._create_default_config()
            self.load_config()

    def _create_default_config(self):
        """Cria arquivo de configuração padrão com manga_converter"""
        default_config = {
            "scripts": [
                {
                    "name": "Conversor de Mangá",
                    "description": "Converte arquivos de manga/comic (PDF, MOBI, EPUB, CBZ, CBR) para CBZ otimizado para Kindle.\n\nFormatos suportados:\n- PDF\n- MOBI/AZW3\n- EPUB\n- CBZ/CBR\n\nO script processa todos os arquivos suportados no diretório selecionado.",
                    "file": "manga_converter.py",
                    "module": "manga_converter",
                    "class": "MangaConverter"
                }
            ]
        }

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

    def _validate_script_file(self, script: dict) -> bool:
        """Valida se o arquivo do script existe

        Args:
            script: Dicionário com informações do script

        Returns:
            True se o arquivo existe, False caso contrário
        """
        script_path = Path(script.get('file', ''))
        return script_path.exists() and script_path.is_file()

    def get_all_scripts(self) -> list:
        """Retorna lista de todos os scripts registrados

        Returns:
            Lista de dicionários com informações dos scripts
        """
        return self.scripts

    def get_script_by_name(self, name: str) -> dict:
        """Busca um script pelo nome

        Args:
            name: Nome do script

        Returns:
            Dicionário com informações do script ou None se não encontrado
        """
        for script in self.scripts:
            if script.get('name') == name:
                return script
        return None


class ExecutionEngine:
    """Gerencia a execução de scripts em threads separadas"""

    def __init__(self, output_queue: queue.Queue):
        """Inicializa o motor de execução

        Args:
            output_queue: Fila para comunicação thread-safe do output
        """
        self.output_queue = output_queue
        self.state = "idle"  # idle, running, completed, error
        self.worker_thread = None
        self.original_stdout = None
        self.original_stderr = None

    def execute_script(self, script_info: dict, working_dir: str):
        """Executa um script em thread separada

        Args:
            script_info: Dicionário com informações do script
            working_dir: Diretório de trabalho para o script
        """
        self.state = "running"
        self.worker_thread = threading.Thread(
            target=self._run_script,
            args=(script_info, working_dir),
            daemon=True
        )
        self.worker_thread.start()

    def _run_script(self, script_info: dict, working_dir: str):
        """Executa o script (roda em thread separada)

        Args:
            script_info: Dicionário com informações do script
            working_dir: Diretório de trabalho
        """
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        try:
            # Redireciona stdout e stderr
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Importa o módulo dinamicamente
            module_name = script_info.get('module')
            class_name = script_info.get('class')

            self.output_queue.put(f"Importando módulo: {module_name}...\n")

            try:
                module = importlib.import_module(module_name)
                # Recarrega o módulo para pegar mudanças
                importlib.reload(module)
            except ImportError as e:
                raise ImportError(f"Não foi possível importar o módulo '{module_name}': {e}")

            # Obtém a classe
            if not hasattr(module, class_name):
                raise AttributeError(f"Classe '{class_name}' não encontrada no módulo '{module_name}'")

            script_class = getattr(module, class_name)

            self.output_queue.put(f"Instanciando classe: {class_name}...\n")

            # Instancia a classe com o diretório de trabalho
            script_instance = script_class(working_dir=working_dir)

            self.output_queue.put(f"Executando script...\n")
            self.output_queue.put("=" * 60 + "\n")

            # Cria uma thread para enviar output periodicamente
            def send_output():
                while self.state == "running":
                    # Captura output acumulado
                    output = stdout_capture.getvalue()
                    error_output = stderr_capture.getvalue()

                    if output:
                        self.output_queue.put(output)
                        stdout_capture.truncate(0)
                        stdout_capture.seek(0)

                    if error_output:
                        self.output_queue.put(f"[ERRO] {error_output}")
                        stderr_capture.truncate(0)
                        stderr_capture.seek(0)

                    threading.Event().wait(0.1)  # Poll a cada 100ms

            output_thread = threading.Thread(target=send_output, daemon=True)
            output_thread.start()

            # Executa o método run()
            script_instance.run()

            # Captura qualquer output final
            final_output = stdout_capture.getvalue()
            final_error = stderr_capture.getvalue()

            if final_output:
                self.output_queue.put(final_output)
            if final_error:
                self.output_queue.put(f"[ERRO] {final_error}")

            self.state = "completed"
            self.output_queue.put("\n" + "=" * 60 + "\n")
            self.output_queue.put("✓ Script executado com sucesso!\n")

        except Exception as e:
            self.state = "error"
            error_msg = f"\n{'=' * 60}\n✗ Erro durante a execução:\n{str(e)}\n{'=' * 60}\n"
            self.output_queue.put(error_msg)

        finally:
            # Restaura stdout e stderr
            if self.original_stdout:
                sys.stdout = self.original_stdout
            if self.original_stderr:
                sys.stderr = self.original_stderr


class ScriptLauncherGUI(tk.Tk):
    """Interface gráfica para executar scripts Python"""

    def __init__(self):
        """Inicializa a interface gráfica"""
        super().__init__()

        # Configurações da janela
        self.title("Script Launcher")
        self.minsize(800, 600)
        self.geometry("900x700")

        # Variáveis de estado
        self.selected_dir = tk.StringVar()
        self.selected_script = None
        self.is_running = False

        # Inicializa componentes
        self.registry = ScriptRegistry()
        self.output_queue = queue.Queue()
        self.engine = ExecutionEngine(self.output_queue)

        # Cria interface
        self._create_widgets()

        # Configura evento de fechamento
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        """Cria todos os widgets da interface"""
        # Frame principal com padding
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Seção 1: Seleção de diretório
        dir_frame = tk.LabelFrame(main_frame, text="1. Diretório de Trabalho", padx=10, pady=10)
        dir_frame.pack(fill=tk.X, pady=(0, 10))

        dir_label = tk.Label(dir_frame, text="Selecione o diretório onde o script será executado:")
        dir_label.pack(anchor=tk.W)

        dir_input_frame = tk.Frame(dir_frame)
        dir_input_frame.pack(fill=tk.X, pady=(5, 0))

        self.dir_entry = tk.Entry(dir_input_frame, textvariable=self.selected_dir, state='readonly')
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        browse_btn = tk.Button(dir_input_frame, text="Procurar...", command=self._browse_directory)
        browse_btn.pack(side=tk.RIGHT)

        # Seção 2: Seleção de script
        script_frame = tk.LabelFrame(main_frame, text="2. Seleção de Script", padx=10, pady=10)
        script_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # PanedWindow para dividir lista e descrição
        paned = tk.PanedWindow(script_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Frame esquerdo: Lista de scripts (30%)
        left_frame = tk.Frame(paned)
        paned.add(left_frame, width=250)

        list_label = tk.Label(left_frame, text="Scripts disponíveis:")
        list_label.pack(anchor=tk.W)

        list_scroll = tk.Scrollbar(left_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.script_listbox = tk.Listbox(left_frame, yscrollcommand=list_scroll.set)
        self.script_listbox.pack(fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.script_listbox.yview)

        self.script_listbox.bind('<<ListboxSelect>>', self._on_script_select)

        # Frame direito: Descrição (70%)
        right_frame = tk.Frame(paned)
        paned.add(right_frame, width=550)

        desc_label = tk.Label(right_frame, text="Descrição do script:")
        desc_label.pack(anchor=tk.W)

        desc_scroll = tk.Scrollbar(right_frame)
        desc_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.description_text = tk.Text(right_frame, wrap=tk.WORD, yscrollcommand=desc_scroll.set, state='disabled')
        self.description_text.pack(fill=tk.BOTH, expand=True)
        desc_scroll.config(command=self.description_text.yview)

        # Popula lista de scripts
        self._populate_script_list()

        # Seção 3: Log de execução
        log_frame = tk.LabelFrame(main_frame, text="3. Log de Execução", padx=10, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Status label
        status_frame = tk.Frame(log_frame)
        status_frame.pack(fill=tk.X, pady=(0, 5))

        tk.Label(status_frame, text="Status:").pack(side=tk.LEFT)
        self.status_label = tk.Label(status_frame, text="Pronto", fg="green")
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))

        # Text widget com scrollbar para log
        log_text_frame = tk.Frame(log_frame)
        log_text_frame.pack(fill=tk.BOTH, expand=True)

        log_scroll = tk.Scrollbar(log_text_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_text_frame, wrap=tk.WORD, yscrollcommand=log_scroll.set, state='disabled', height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)

        # Botão de execução
        button_frame = tk.Frame(log_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.run_button = tk.Button(button_frame, text="Rodar Script", command=self._execute_script, state='disabled')
        self.run_button.pack(side=tk.RIGHT)

    def _browse_directory(self):
        """Abre diálogo para selecionar diretório"""
        directory = filedialog.askdirectory(title="Selecione o Diretório de Trabalho")
        if directory:
            # Valida diretório
            dir_path = Path(directory)
            if dir_path.exists() and dir_path.is_dir():
                self.selected_dir.set(directory)
                self._update_run_button_state()
            else:
                messagebox.showerror(
                    "Diretório Inválido",
                    "O diretório selecionado não existe ou não é acessível."
                )

    def _populate_script_list(self):
        """Popula a lista de scripts disponíveis"""
        scripts = self.registry.get_all_scripts()

        for script in scripts:
            script_name = script.get('name', 'Sem nome')

            # Verifica se o arquivo existe
            if not self.registry._validate_script_file(script):
                script_name += " ⚠️ (arquivo não encontrado)"

            self.script_listbox.insert(tk.END, script_name)

    def _on_script_select(self, event):
        """Callback quando um script é selecionado"""
        selection = self.script_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        scripts = self.registry.get_all_scripts()

        if index < len(scripts):
            self.selected_script = scripts[index]

            # Atualiza descrição
            description = self.selected_script.get('description', 'Sem descrição disponível')
            self.description_text.config(state='normal')
            self.description_text.delete(1.0, tk.END)
            self.description_text.insert(1.0, description)
            self.description_text.config(state='disabled')

            # Atualiza estado do botão
            self._update_run_button_state()

    def _update_run_button_state(self):
        """Atualiza o estado do botão de execução baseado nas seleções"""
        if self.selected_dir.get() and self.selected_script and not self.is_running:
            # Verifica se o arquivo do script existe
            if self.registry._validate_script_file(self.selected_script):
                self.run_button.config(state='normal')
            else:
                self.run_button.config(state='disabled')
        else:
            self.run_button.config(state='disabled')

    def _execute_script(self):
        """Executa o script selecionado"""
        # Validações
        if not self.selected_dir.get():
            messagebox.showwarning("Atenção", "Selecione um diretório de trabalho.")
            return

        if not self.selected_script:
            messagebox.showwarning("Atenção", "Selecione um script para executar.")
            return

        # Limpa o log
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

        # Atualiza estado
        self.is_running = True
        self.run_button.config(state='disabled')
        self.status_label.config(text="Executando...", fg="orange")

        # Inicia execução
        self.engine.execute_script(self.selected_script, self.selected_dir.get())

        # Inicia polling do output
        self._poll_output()

    def _poll_output(self):
        """Verifica a fila de output periodicamente"""
        try:
            while True:
                # Tenta pegar mensagens da fila (non-blocking)
                message = self.output_queue.get_nowait()

                # Adiciona ao log
                self.log_text.config(state='normal')

                # Limitação: mantém apenas últimas 1000 linhas
                line_count = int(self.log_text.index('end-1c').split('.')[0])
                if line_count > 1000:
                    self.log_text.delete(1.0, f"{line_count - 1000}.0")

                self.log_text.insert(tk.END, message)
                self.log_text.see(tk.END)  # Auto-scroll
                self.log_text.config(state='disabled')

        except queue.Empty:
            pass

        # Verifica se ainda está executando
        if self.engine.state == "running":
            # Continua polling
            self.after(100, self._poll_output)
        else:
            # Execução finalizada
            self._on_execution_complete()

    def _on_execution_complete(self):
        """Callback quando execução completa"""
        self.is_running = False
        self.run_button.config(state='normal')

        if self.engine.state == "completed":
            self.status_label.config(text="Concluído ✓", fg="green")
        elif self.engine.state == "error":
            self.status_label.config(text="Erro ✗", fg="red")
        else:
            self.status_label.config(text="Pronto", fg="green")

        self._update_run_button_state()

    def _on_closing(self):
        """Callback ao fechar a janela"""
        if self.is_running:
            if messagebox.askokcancel(
                "Script em Execução",
                "Um script está sendo executado. Deseja realmente fechar?"
            ):
                self.destroy()
        else:
            self.destroy()


def main():
    """Função principal"""
    app = ScriptLauncherGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
