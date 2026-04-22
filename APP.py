import streamlit as st
import pandas as pd
import sqlite3
import os
import io
import time
from datetime import datetime
from pathlib import Path

# --- CONFIGURAÇÃO DE CAMINHOS ---
pasta_documentos = Path.home() / "Documents" / "SISTEMA DE PONTO GMAC"
pasta_fotos = pasta_documentos / "fotos"
db_path = pasta_documentos / "ponto_digital.db"
excel_path = pasta_documentos / "relatorio_ponto_gmac.xlsx"

pasta_documentos.mkdir(parents=True, exist_ok=True)
pasta_fotos.mkdir(parents=True, exist_ok=True)

# --- LISTA OFICIAL ---
FUNCIONARIOS = [
    "SELECIONE O NOME...", "ANTONIO JORGE VIEIRA", "ANTONIO OLINO LIMA", "CLEYDSON DE ALCANTARA COSTA",
    "COSME SANTANA", "ED CARLOS SOUZA CARDOSO", "EDILSON PEREIRA DA SILVA JUNIOR",
    "EDOIL BATISTA MARTINS", "EMERSON ALCANTARA RIBEIRO", "FELIPE BOTELHO SANTOS",
    "FLAVIO DAS VIRGENS DE CARVALHO QUEIROZ", "GEORGE DA SILVA BARBOSA", "GUTEMBERGUE MOTA GONÇALO",
    "HECTOR CAMILLO ASSUNCAO COLUCCI", "JEFFERSON JOSE DA SILVA", "JOEL ARLINDO SALES DE SOUZA",
    "JOEL DOS SANTOS", "JORGE PEREIRA DE JESUS", "JOYCIELLY ALINE TORRES GALINDO AMORIM",
    "LAIS MARIA FERNANDES", "LEONARDO MENDONÇA TEIXEIRA", "LUCIANO SILVEIRA DA SILVA",
    "MARCOS ANTONIO LIMA NASCIMENTO", "MARCOS MOISES FARIAS MENEZES", "MIGUEL DE JESUS ROCHA",
    "OSVALDO TELES JUNIOR", "PAULO JOSE DA SILVA", "RENALDO DOS SANTOS CERQUEIRA",
    "ROBERTO RODRIGUES SANTOS BARRETO", "THIAGO RAFAEL CARVALHO DE SANTANA",
    "WELLINGTON SEBASTIAO CARVALHO QUEIROZ", "WENDERSON PRADO PINTO", "JORGE CORREIA BORGES", "ALEXANDRE DA CONCEIÇÃO", "WANDERLEY DA SILVA NASCIMENTO", "GERCI CLECIO TEIXEIRA", "ALEXANDRO SAMPAIO"
]

def atualizar_excel_automatico():
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT id, nome, data, hora, tipo, foto_path FROM registros ORDER BY id DESC", conn)
        conn.close()
        if not df.empty:
            df.to_excel(excel_path, index=False, engine='xlsxwriter')
    except Exception as e:
        st.error(f"Feche o arquivo Excel na pasta para que eu possa atualizá-lo! Erro: {e}")

def inicializar_banco():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS registros 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, data TEXT, hora TEXT, tipo TEXT, foto_path TEXT)''')
    conn.commit()
    conn.close()
    atualizar_excel_automatico()

def salvar_registro(nome, tipo, foto_bytes, data_manual=None, hora_manual=None):
    data_f = data_manual if data_manual else datetime.now().strftime("%d/%m/%Y")
    hora_f = hora_manual if hora_manual else datetime.now().strftime("%H:%M:%S")
    if foto_bytes:
        nome_foto = f"{nome.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        caminho_f_obj = pasta_fotos / nome_foto
        with open(caminho_f_obj, "wb") as f:
            f.write(foto_bytes.getbuffer())
        caminho_foto = str(caminho_f_obj)
    else:
        caminho_foto = "Ajuste/Edição Manual"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO registros (nome, data, hora, tipo, foto_path) VALUES (?, ?, ?, ?, ?)",
              (nome, data_f, hora_f, tipo, caminho_foto))
    conn.commit()
    conn.close()
    atualizar_excel_automatico()

# --- INTERFACE ---
st.set_page_config(page_title="GMAC - Ponto Digital", layout="wide")
inicializar_banco()

st.title("🕒 Sistema de Ponto GMAC")

aba_ponto, aba_admin = st.tabs(["📍 Registrar Ponto", "🔒 Área do Gestor (Fábio)"])

with aba_ponto:
    col_c, _ = st.columns([1, 1])
    with col_c:
        st.subheader("Bater Ponto")
        nome_sel = st.selectbox("Selecione seu Nome", FUNCIONARIOS)
        tipo = st.radio("Registro de:", ["Entrada", "Saída"], horizontal=True)
        foto = st.camera_input("Tire sua foto")
        if st.button("CONFIRMAR REGISTRO", use_container_width=True, type="primary"):
            if nome_sel != "SELECIONE O NOME..." and foto:
                salvar_registro(nome_sel, tipo, foto)
                st.success(f"✅ Ponto registrado!")
                time.sleep(2)
                st.rerun()
            else:
                st.error("⚠️ Escolha o nome e tire a foto!")

with aba_admin:
    senha = st.text_input("Senha Administrativa", type="password")
    if senha == "fabioadmponto":
        st.success("Painel de Controle Liberado")
        
        # Filtros
        col_f1, col_f2 = st.columns(2)
        filtro_nome = col_f1.multiselect("Filtrar por Funcionário", FUNCIONARIOS[1:])
        filtro_data = col_f2.text_input("Filtrar por Data (dd/mm/aaaa)", "")

        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM registros ORDER BY id DESC", conn)
        conn.close()

        if not df.empty:
            if filtro_nome: df = df[df['nome'].isin(filtro_nome)]
            if filtro_data: df = df[df['data'] == filtro_data]

            for index, row in df.iterrows():
                with st.container(border=True):
                    # Estado de edição usando session_state
                    edit_key = f"edit_mode_{row['id']}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False

                    c1, c2, c3, c4, c5, c6 = st.columns([1, 2.5, 2, 2, 1.5, 1.5])
                    
                    # Foto
                    if os.path.exists(row['foto_path']):
                        c1.image(row['foto_path'], width=80)
                    else: c1.write("🚫📷")

                    if st.session_state[edit_key]:
                        # MODO EDIÇÃO
                        novo_nome = c2.selectbox("Nome", FUNCIONARIOS[1:], index=FUNCIONARIOS[1:].index(row['nome']), key=f"n_{row['id']}")
                        nova_data = c3.text_input("Data", value=row['data'], key=f"d_{row['id']}")
                        nova_hora = c4.text_input("Hora", value=row['hora'], key=f"h_{row['id']}")
                        novo_tipo = c5.selectbox("Tipo", ["Entrada", "Saída"], index=0 if row['tipo']=="Entrada" else 1, key=f"t_{row['id']}")
                        
                        if c6.button("💾 Salvar", key=f"save_{row['id']}"):
                            conn = sqlite3.connect(db_path)
                            c = conn.cursor()
                            c.execute("UPDATE registros SET nome=?, data=?, hora=?, tipo=? WHERE id=?", 
                                     (novo_nome, nova_data, nova_hora, novo_tipo, row['id']))
                            conn.commit()
                            conn.close()
                            st.session_state[edit_key] = False
                            atualizar_excel_automatico()
                            st.rerun()
                        if c6.button("✖️ Sair", key=f"cancel_{row['id']}"):
                            st.session_state[edit_key] = False
                            st.rerun()
                    else:
                        # MODO VISUALIZAÇÃO
                        c2.markdown(f"**Funcionário:**\n{row['nome']}")
                        c3.markdown(f"**Data:**\n{row['data']}")
                        c4.markdown(f"**Hora:**\n{row['hora']}")
                        status_cor = "🟢" if row['tipo'] == "Entrada" else "🔴"
                        c5.markdown(f"**Tipo:**\n{status_cor} {row['tipo']}")
                        
                        if c6.button("✏️ Editar", key=f"btn_ed_{row['id']}"):
                            st.session_state[edit_key] = True
                            st.rerun()
                        if c6.button("🗑️ Excluir", key=f"btn_del_{row['id']}"):
                            conn = sqlite3.connect(db_path)
                            c = conn.cursor()
                            c.execute("DELETE FROM registros WHERE id = ?", (row['id'],))
                            conn.commit()
                            conn.close()
                            atualizar_excel_automatico()
                            st.rerun()

            st.divider()
            with st.expander("🛠️ Inserir Novo Registro Manual"):
                ca1, ca2, ca3, ca4 = st.columns(4)
                n_aj = ca1.selectbox("Funcionário", FUNCIONARIOS, key="n_aj")
                d_aj = ca2.date_input("Data")
                h_aj = ca3.time_input("Hora")
                t_aj = ca4.selectbox("Tipo", ["Entrada", "Saída"], key="t_aj")
                if st.button("SALVAR NOVO AJUSTE"):
                    if n_aj != "SELECIONE O NOME...":
                        salvar_registro(n_aj, t_aj, None, d_aj.strftime("%d/%m/%Y"), h_aj.strftime("%H:%M:%S"))
                        st.rerun()

            st.info(f"📁 Excel sempre atualizado em: {excel_path}")
            if st.button("📂 Abrir Pasta"):
                os.startfile(pasta_documentos)
    elif senha != "":
        st.error("Senha incorreta!")