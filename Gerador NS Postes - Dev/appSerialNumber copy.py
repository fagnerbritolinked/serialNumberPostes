import csv
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from PIL import Image, ImageTk
import time
import sv_ttk  # Biblioteca para tema Sv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Obtém os valores da URL e da chave do Supabase a partir do .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Cria o cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Mapeamento de regionais
regionais_map = {
    "Petrolina": "PT", "PT": "PT",
    "Garanhuns": "GR", "GR": "GR",
    "Arcoverde": "AV", "AV": "AV",
    "Caruaru": "CR", "CR": "CR",
    "Recife": "RF", "RF": "RF",
    "Serra Talhada": "ST", "ST": "ST",
    "Ouricuri": "OC", "OC": "OC"
}

# Variáveis globais para armazenar dados do usuário logado e controlar o loading
logged_user = None
logged_regional = None
logged_role = None
loading = None

# Função para mostrar o indicador de carregamento
def show_loading():
    global loading
    loading = ttk.Label(login_frame, text="Carregando...", style="Loading.TLabel")
    loading.grid(row=3, column=0, columnspan=2, pady=10)
    root.update()

# Função para esconder o indicador de carregamento
def hide_loading():
    global loading
    if loading:
        loading.grid_forget()
        loading = None

# Função para autenticar o usuário no Supabase
def login():
    global logged_user, logged_regional, logged_role, user_regionals
    email = email_entry.get().strip()
    password = password_entry.get()

    show_loading()

    try:
        response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password
        })

        if response.user:
            logged_user = email
            user_data = supabase.table('profiles').select('*').eq('email', email).single().execute()

            if user_data.data:
                logged_role = user_data.data['role']
                
                # Buscar as regionais do usuário
                if logged_role == 'master':
                    user_regionals = list(regionais_map.keys())
                else:
                    user_regionals = user_data.data.get('regionals', [])

                messagebox.showinfo("Sucesso", "Login realizado com sucesso!")

                login_frame.pack_forget()
                main_content_frame.pack(pady=20)

                # Atualizar o menu de seleção de regional
                update_regional_menu()

            else:
                messagebox.showerror("Erro", "Usuário não encontrado.")
        else:
            messagebox.showerror("Erro", "Falha no login. Verifique suas credenciais.")

    except Exception as e:
        messagebox.showerror("Erro de autenticação", f"Ocorreu um erro: {str(e)}")
    finally:
        hide_loading()

# Adicione uma nova função para atualizar o menu de seleção de regional
def update_regional_menu():
    regional_menu['values'] = user_regionals
    if user_regionals:
        regional_var.set(user_regionals[0])
    regional_menu.config(state="readonly" if len(user_regionals) > 1 else "disabled")

# Função para obter o último número de série gerado para uma região
def get_last_serial_number(regional):
    try:
        response = supabase.table('serial_numbers').select('serial_number').like('serial_number', f"%{regional}%").order('serial_number', desc=True).limit(1).execute()
        if response.data:
            last_serial = response.data[0]['serial_number']
            last_number = int(last_serial[-5:])  # Extrai a parte numérica do número de série
            return last_number
        else:
            return 0  # Se não houver números de série, começa do zero
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao obter o último número de série: {str(e)}")
        return 0

# Função para gerar números de série
def generate_serials(regional, quantity):
    current_year = datetime.now().year
    serials = []
    
    # Obtém o último número de série gerado para a região
    last_number = get_last_serial_number(regional)
    
    print(f"Gerando séries para regional: {regional}, último número: {last_number}")  # Debug
    
    for i in range(1, quantity + 1):
        serial_number = f"{current_year}{regional}{str(last_number + i).zfill(5)}"
        serials.append(serial_number)
        print(f"Série gerada: {serial_number}")  # Debug
    
    return serials

# Função para exportar os números de série para CSV
def export_to_csv(serials):
    filepath = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[("CSV files", "*.csv")])
    
    if filepath:
        try:
            with open(filepath, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Número de Série"])
                for serial in serials:
                    writer.writerow([serial])
            return filepath  # Retorna o caminho do arquivo se a exportação for bem-sucedida
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar o arquivo: {str(e)}")
            return None
    else:
        messagebox.showerror("Erro", "Exportação cancelada.")
        return None

# Função para gerar e exportar os números de série com barra de progresso
def generate_and_export():
    try:
        num_serials = int(quantity_entry.get().strip())

        if num_serials > 20:
            messagebox.showerror("Erro", "O número máximo de gerações por vez é 20.")
            return

        if num_serials <= 0:
            messagebox.showerror("Erro", "Por favor, insira um número positivo.")
            return

        selected_regional_name = regional_var.get()
        selected_regional = regionais_map.get(selected_regional_name)

        if selected_regional is None:
            messagebox.showerror("Erro", f"Sigla não encontrada para a regional: {selected_regional_name}")
            return

        print(f"Regional selecionada: {selected_regional_name}, Sigla: {selected_regional}")  # Debug

        # Verificar se o usuário tem acesso à regional selecionada
        if selected_regional_name not in user_regionals:
            messagebox.showerror("Erro", "Você não tem acesso a esta regional.")
            return

        # Adiciona a mensagem de confirmação
        confirmation = messagebox.askyesno("Confirmação", "Tem certeza que deseja gerar esses NS? Ao confirmar SIM o sistema irá gerar no banco de dados e não poderá ser removido.")
        
        if not confirmation:
            messagebox.showinfo("Informação", "Operação cancelada pelo usuário.")
            return

        progress['value'] = 0
        root.update_idletasks()

        serials = generate_serials(selected_regional, num_serials)

        export_path = export_to_csv(serials)
        if export_path:
            user_response = supabase.auth.get_user()
            user = user_response.user

            for i, serial in enumerate(serials):
                print(f"Inserindo no Supabase: {serial}")  # Debug
                response = supabase.table('serial_numbers').insert({
                    'serial_number': serial,
                    'user_id': user.id
                }).execute()
                print(f"Resposta do Supabase: {response}")  # Debug
                
                progress['value'] = ((i + 1) / num_serials) * 100
                root.update_idletasks()
                time.sleep(0.1)

            messagebox.showinfo("Sucesso", f"Números de série gerados e exportados com sucesso para {export_path}!")
        else:
            messagebox.showwarning("Atenção", "A exportação foi cancelada. Nenhum número de série foi salvo no banco de dados.")

    except ValueError:
        messagebox.showerror("Erro", "Por favor, insira um número válido.")
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro: {str(e)}")
        print(f"Erro detalhado: {str(e)}")  # Debug

# Configuraão da interface gráfica
root = tk.Tk()
root.title("Gerador de Números de Série")
root.geometry("600x700")
sv_ttk.set_theme("dark")  # Aplica o tema escuro do Sv

# Estilo personalizado
style = ttk.Style()
style.configure("TButton", padding=10, font=("Roboto", 10))
style.configure("TLabel", font=("Roboto", 10))
style.configure("TEntry", font=("Roboto", 10))
style.configure("Loading.TLabel", foreground="blue", font=("Roboto", 12, "bold"))

# Cabeçalho com logo
header_frame = ttk.Frame(root)
header_frame.pack(fill="x", pady=20)

try:
    logo_image = Image.open("logoHome.png")  # Alterado de "logo.png" para "logoHome.png"
    logo_image = logo_image.resize((80, 80), Image.LANCZOS)  # Reduzido de 100x100 para 80x80
    logo_photo = ImageTk.PhotoImage(logo_image)
    logo_label = ttk.Label(header_frame, image=logo_photo)
    logo_label.image = logo_photo  # Mantenha uma referência à imagem
    logo_label.pack(pady=10)  # Centraliza verticalmente com um pequeno espaçamento
except Exception as e:
    print(f"Erro ao carregar a imagem: {str(e)}")
    # Adicione um label alternativo caso a imagem não seja carregada
    fallback_label = ttk.Label(header_frame, text="Logo não disponível")
    fallback_label.pack(pady=10)

title_label = ttk.Label(header_frame, text="Gerador de NS - Postes", font=("Roboto", 20, "bold"))
title_label.pack(pady=10)  # Adiciona espaçamento vertical

# Frame principal
main_frame = ttk.Frame(root, padding=20)
main_frame.pack(fill="both", expand=True)

# Tela de login
login_frame = ttk.Frame(main_frame)

email_label = ttk.Label(login_frame, text="Email:")
email_label.grid(row=0, column=0, pady=5, sticky="w")
email_entry = ttk.Entry(login_frame, width=30)
email_entry.grid(row=0, column=1, pady=5)

password_label = ttk.Label(login_frame, text="Senha:")
password_label.grid(row=1, column=0, pady=5, sticky="w")
password_entry = ttk.Entry(login_frame, show="*", width=30)
password_entry.grid(row=1, column=1, pady=5)

login_button = ttk.Button(login_frame, text="Login", command=login)
login_button.grid(row=2, column=0, columnspan=2, pady=20)

login_frame.pack(pady=20)

# Tela principal (após login)
main_content_frame = ttk.Frame(main_frame)

regional_label = ttk.Label(main_content_frame, text="Regional Cadastrada:")
regional_label.grid(row=0, column=0, pady=10, sticky="w")

regional_var = tk.StringVar(main_content_frame)
regional_menu = ttk.Combobox(main_content_frame, textvariable=regional_var, state="readonly")
regional_menu.grid(row=0, column=1, pady=10)

quantity_label = ttk.Label(main_content_frame, text="Quantidade de Números de Série:")
quantity_label.grid(row=1, column=0, pady=10, sticky="w")

quantity_entry = ttk.Entry(main_content_frame, width=10)
quantity_entry.grid(row=1, column=1, pady=10)

progress = ttk.Progressbar(main_content_frame, orient="horizontal", length=300, mode="determinate")
progress.grid(row=2, column=0, columnspan=2, pady=20)

generate_button = ttk.Button(main_content_frame, text="Gerar e Exportar", command=generate_and_export)
generate_button.grid(row=3, column=0, columnspan=2, pady=20)

# Rodapé com texto
footer_frame = ttk.Frame(root)
footer_frame.pack(side=tk.BOTTOM, pady=10)

footer_text = ttk.Label(footer_frame, text="Desenvolvido por: Setor de Tecnologia - CENEGED-PE", font=("Roboto", 9))
footer_text.pack()

root.mainloop()
