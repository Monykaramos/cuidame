"""
Cuida-me - MVP
App simples feito em Streamlit + SQLite.

Como rodar localmente:
    1. pip install -r requirements.txt
    2. streamlit run app.py

O banco de dados (cuidame.db) é criado automaticamente na primeira
execução, na mesma pasta deste arquivo.

IMPORTANTE: o formato da tabela "cuidadores" mudou de novo (tipo de
cuidado e faixa de idade agora aceitam mais de uma opção, e tem campo
de upload de arquivo). Se você já tinha um cuidame.db de testes
antigos, apague-o antes de rodar de novo. Ele é recriado sozinho,
vazio.
"""

import os
import re
import sqlite3
from datetime import date

import streamlit as st

# ---------------------------------------------------------------
# CONFIGURAÇÃO DO BANCO DE DADOS E DE ARQUIVOS
# ---------------------------------------------------------------
# SQLite guarda tudo em um único arquivo (cuidame.db). Não precisa
# instalar nenhum servidor de banco de dados.

NOME_BANCO = "cuidame.db"
PASTA_UPLOADS = "uploads_cuidadores"
os.makedirs(PASTA_UPLOADS, exist_ok=True)


def conectar():
    """Abre uma conexão com o banco de dados."""
    conexao = sqlite3.connect(NOME_BANCO)
    conexao.row_factory = sqlite3.Row  # permite acessar colunas pelo nome
    return conexao


def criar_tabelas():
    """Cria as tabelas se elas ainda não existirem."""
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL,
            data_nascimento TEXT,
            endereco TEXT,
            telefone TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cuidadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_nascimento TEXT,
            endereco TEXT,
            tipo_cuidado TEXT,
            formacao TEXT,
            antecedentes_criminais TEXT,
            antecedentes_arquivo TEXT,

            -- campos pedidos pela professora (guardamos o texto E o
            -- código numérico, porque o código é o que vocês vão usar
            -- depois lá na frente, na parte de Machine Learning)
            disponibilidade_horas TEXT,
            disponibilidade_horas_cod INTEGER,
            disponibilidade_fds TEXT,
            disponibilidade_fds_cod INTEGER,
            turno TEXT,
            turno_cod INTEGER,
            disponibilidade_viagem TEXT,
            disponibilidade_viagem_cod INTEGER,
            cursos TEXT,
            experiencia TEXT,
            descricao TEXT,
            tipos_pacientes TEXT,
            tipos_pacientes_cod TEXT,
            sexo_paciente TEXT,
            sexo_paciente_cod INTEGER,
            faixa_idade_paciente TEXT,
            faixa_idade_paciente_cod TEXT,
            certidao_antecedentes TEXT,
            certidao_antecedentes_cod INTEGER,
            curriculo_arquivo TEXT,

            aprovado INTEGER DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_remetente TEXT NOT NULL,
            cuidador_id INTEGER NOT NULL,
            mensagem TEXT NOT NULL,
            data_envio TEXT,
            FOREIGN KEY (cuidador_id) REFERENCES cuidadores (id)
        )
        """
    )

    conexao.commit()
    conexao.close()


# ---------------------------------------------------------------
# TABELAS DE CODIFICAÇÃO
# ---------------------------------------------------------------
# Estas tabelas traduzem a resposta (texto, que aparece na tela) para
# o código numérico que a professora pediu (usado depois no modelo).

COD_HORAS = {"6 horas": 0, "12 horas": 1, "24 horas": 2}
COD_SIM_NAO_FDS = {"Sim": 0, "Não": 1}
COD_TURNO = {"Manhã": 0, "Vespertino": 1, "Noturno": 2, "Integral": 3}
COD_VIAGEM = {"Sim": 0, "Não": 1}
COD_SEXO_PACIENTE = {"Masculino": 0, "Feminino": 1}
COD_CERTIDAO = {"Sim": 0, "Não": 1}

COD_FAIXA_IDADE = {"Até 30 anos": 0, "De 30 a 60 anos": 1, "Acima de 60 anos": 2}
OPCOES_FAIXA_IDADE = list(COD_FAIXA_IDADE.keys())

OPCOES_CURSOS = [
    "Cuidador", "Técnico", "Enfermeiro", "Fisioterapeuta", "Primeiros Socorros",
]

COD_TIPOS_PACIENTES = {
    "Companhia": 0,
    "Acamado": 1,
    "Dificuldade de locomoção": 2,
    "Mental": 3,
    "Demência": 4,
    "Pós Cirúrgico": 5,
}
OPCOES_TIPOS_PACIENTES = list(COD_TIPOS_PACIENTES.keys())

TIPOS_CUIDADO = ["Idoso", "Pós-cirúrgico", "PCD"]


# ---------------------------------------------------------------
# VALIDAÇÃO DE CPF
# ---------------------------------------------------------------

def limpar_cpf(cpf):
    """Remove tudo que não for dígito."""
    return re.sub(r"\D", "", cpf or "")


def cpf_valido(cpf):
    """Validação simples: exige 11 dígitos numéricos."""
    digitos = limpar_cpf(cpf)
    return len(digitos) == 11


def formatar_cpf(cpf):
    """Formata para 000.000.000-00."""
    digitos = limpar_cpf(cpf)
    return f"{digitos[0:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:11]}"


# ---------------------------------------------------------------
# FUNÇÕES DE ACESSO AOS DADOS (equivalente ao "back-end")
# ---------------------------------------------------------------

def inserir_usuario(nome, cpf, data_nascimento, endereco, telefone):
    conexao = conectar()
    conexao.execute(
        """INSERT INTO usuarios (nome, cpf, data_nascimento, endereco, telefone)
           VALUES (?, ?, ?, ?, ?)""",
        (nome, cpf, str(data_nascimento), endereco, telefone),
    )
    conexao.commit()
    conexao.close()


def inserir_cuidador(dados):
    """dados é um dicionário com todas as chaves da tabela cuidadores
    (menos id e aprovado, que são automáticos)."""
    conexao = conectar()
    conexao.execute(
        """
        INSERT INTO cuidadores (
            nome, data_nascimento, endereco, tipo_cuidado, formacao,
            antecedentes_criminais, antecedentes_arquivo, curriculo_arquivo,
            disponibilidade_horas, disponibilidade_horas_cod,
            disponibilidade_fds, disponibilidade_fds_cod,
            turno, turno_cod,
            disponibilidade_viagem, disponibilidade_viagem_cod,
            cursos, experiencia, descricao, tipos_pacientes, tipos_pacientes_cod,
            sexo_paciente, sexo_paciente_cod,
            faixa_idade_paciente, faixa_idade_paciente_cod,
            certidao_antecedentes, certidao_antecedentes_cod,
            aprovado
        ) VALUES (
            :nome, :data_nascimento, :endereco, :tipo_cuidado, :formacao,
            :antecedentes_criminais, :antecedentes_arquivo, :curriculo_arquivo,
            :disponibilidade_horas, :disponibilidade_horas_cod,
            :disponibilidade_fds, :disponibilidade_fds_cod,
            :turno, :turno_cod,
            :disponibilidade_viagem, :disponibilidade_viagem_cod,
            :cursos, :experiencia, :descricao, :tipos_pacientes, :tipos_pacientes_cod,
            :sexo_paciente, :sexo_paciente_cod,
            :faixa_idade_paciente, :faixa_idade_paciente_cod,
            :certidao_antecedentes, :certidao_antecedentes_cod,
            0
        )
        """,
        dados,
    )
    conexao.commit()
    conexao.close()


def listar_cuidadores(tipo_cuidado=None):
    """tipo_cuidado agora pode fazer parte de uma lista salva como
    'Idoso, PCD', então usamos LIKE em vez de igualdade exata."""
    conexao = conectar()
    if tipo_cuidado and tipo_cuidado != "Todos":
        linhas = conexao.execute(
            "SELECT * FROM cuidadores WHERE tipo_cuidado LIKE ?",
            (f"%{tipo_cuidado}%",),
        ).fetchall()
    else:
        linhas = conexao.execute("SELECT * FROM cuidadores").fetchall()
    conexao.close()
    return linhas


def aprovar_cuidador(id_cuidador):
    conexao = conectar()
    conexao.execute(
        "UPDATE cuidadores SET aprovado = 1 WHERE id = ?", (id_cuidador,)
    )
    conexao.commit()
    conexao.close()


def reprovar_cuidador(id_cuidador):
    """Remove o cadastro do cuidador (recusado na verificação)."""
    conexao = conectar()
    conexao.execute("DELETE FROM cuidadores WHERE id = ?", (id_cuidador,))
    conexao.commit()
    conexao.close()


def resetar_banco():
    """Apaga o banco de dados inteiro e recria as tabelas vazias.
    Use quando o app.py mudar de versão e der erro de coluna faltando."""
    conexao_atual = conectar()
    conexao_atual.close()
    if os.path.exists(NOME_BANCO):
        os.remove(NOME_BANCO)
    criar_tabelas()


def salvar_arquivo_upload(arquivo_upload, nome_cuidador, sufixo=""):
    """Salva o arquivo enviado na pasta de uploads e devolve o caminho."""
    if arquivo_upload is None:
        return None
    nome_seguro = "".join(
        ch for ch in nome_cuidador if ch.isalnum() or ch in (" ", "_")
    ).strip().replace(" ", "_")
    nome_arquivo = f"{nome_seguro}{sufixo}_{arquivo_upload.name}"
    caminho = os.path.join(PASTA_UPLOADS, nome_arquivo)
    with open(caminho, "wb") as f:
        f.write(arquivo_upload.getbuffer())
    return caminho


def enviar_mensagem(nome_remetente, cuidador_id, mensagem):
    conexao = conectar()
    conexao.execute(
        """INSERT INTO mensagens (nome_remetente, cuidador_id, mensagem, data_envio)
           VALUES (?, ?, ?, ?)""",
        (nome_remetente, cuidador_id, mensagem, str(date.today())),
    )
    conexao.commit()
    conexao.close()


def listar_mensagens(cuidador_id=None):
    conexao = conectar()
    if cuidador_id:
        linhas = conexao.execute(
            "SELECT * FROM mensagens WHERE cuidador_id = ? ORDER BY id DESC",
            (cuidador_id,),
        ).fetchall()
    else:
        linhas = conexao.execute("SELECT * FROM mensagens ORDER BY id DESC").fetchall()
    conexao.close()
    return linhas


# ---------------------------------------------------------------
# INTERFACE (equivalente ao "front-end")
# ---------------------------------------------------------------

criar_tabelas()

st.set_page_config(page_title="Cuida-me", page_icon="logo.png")

col_esq, col_centro, col_dir = st.columns([1, 1, 1])
with col_centro:
    st.image("logo.png", width=180)
st.divider()

st.sidebar.markdown("### Você é:")
tipo_usuario = st.sidebar.radio(
    "Tipo de usuário", ["Cliente", "Cuidador", "Administrador"], label_visibility="collapsed"
)

OPCOES_MENU = {
    "Cliente": ["Início", "Cadastrar usuário", "Buscar cuidadores"],
    "Cuidador": ["Início", "Cadastrar cuidador", "Minhas mensagens"],
    "Administrador": ["Início", "Aprovar cuidadores (admin)"],
}

st.sidebar.markdown("### Navegação")
menu = st.sidebar.radio("Navegação", OPCOES_MENU[tipo_usuario], label_visibility="collapsed")

# --- Página inicial -------------------------------------------------
if menu == "Início":
    st.write(
        "Bem-vindo(a) ao protótipo do **Cuida-me**, um marketplace que conecta "
        "famílias a cuidadores verificados. Use o menu ao lado para navegar."
    )

# --- Cadastro de usuário (cliente) -----------------------------------
elif menu == "Cadastrar usuário":
    st.subheader("Cadastro de usuário")
    with st.form("form_usuario", clear_on_submit=True):
        nome = st.text_input("Nome completo")
        cpf = st.text_input(
            "CPF", max_chars=14, placeholder="000.000.000-00 (somente números)"
        )
        nascimento = st.date_input(
            "Data de nascimento",
            min_value=date(1900, 1, 1),
            max_value=date.today(),
        )
        endereco = st.text_input("Endereço")
        telefone = st.text_input("Telefone")
        enviado = st.form_submit_button("Cadastrar")

        if enviado:
            if not nome:
                st.error("Preencha o nome.")
            elif not cpf_valido(cpf):
                st.error("CPF inválido. Digite os 11 números do CPF (com ou sem pontuação).")
            else:
                inserir_usuario(nome, formatar_cpf(cpf), nascimento, endereco, telefone)
                st.success(f"Usuário {nome} cadastrado com sucesso!")

# --- Cadastro de cuidador ---------------------------------------------
elif menu == "Cadastrar cuidador":
    st.subheader("Cadastro de cuidador")
    with st.form("form_cuidador", clear_on_submit=True):

        st.markdown("**Dados pessoais**")
        nome = st.text_input("Nome completo")
        nascimento = st.date_input(
            "Data de nascimento",
            min_value=date(1900, 1, 1),
            max_value=date.today(),
        )
        endereco = st.text_input("Endereço")
        tipo_cuidado = st.multiselect("Tipo de cuidado prestado", TIPOS_CUIDADO)

        st.markdown("**Disponibilidade**")
        horas = st.selectbox("Disponibilidade (horas)", list(COD_HORAS.keys()))
        fds = st.selectbox("Disponível em finais de semana?", list(COD_SIM_NAO_FDS.keys()))
        turno = st.selectbox("Turno", list(COD_TURNO.keys()))
        viagem = st.selectbox("Disponível para viagem?", list(COD_VIAGEM.keys()))

        st.markdown("**Formação e cursos**")
        formacao = st.text_input("Formação")
        cursos = st.multiselect("Cursos", OPCOES_CURSOS)
        curriculo = st.file_uploader(
            "Anexar currículo (PDF, opcional)", type=["pdf"]
        )
        experiencia = st.text_area(
            "Experiência (descreva livremente)",
            help="Texto livre — será usado depois para análise de texto (PLN).",
        )
        descricao = st.text_area("Descrição geral do cuidador")

        st.markdown("**Tipos de paciente que atende**")
        tipos_pacientes = st.multiselect("Tipos de paciente", OPCOES_TIPOS_PACIENTES)
        sexo_paciente = st.selectbox("Sexo do paciente que atende", list(COD_SEXO_PACIENTE.keys()))
        faixa_idade_paciente = st.multiselect(
            "Faixa de idade do paciente que atende", OPCOES_FAIXA_IDADE
        )

        st.markdown("**Documentação**")
        certidao = st.selectbox(
            "Possui certidão de antecedentes criminais?", list(COD_CERTIDAO.keys())
        )
        arquivo_antecedentes = st.file_uploader(
            "Anexar certidão de antecedentes (PDF ou imagem, opcional)",
            type=["pdf", "jpg", "jpeg", "png"],
        )
        antecedentes = st.text_area(
            "Observações sobre antecedentes (opcional)"
        )

        enviado = st.form_submit_button("Cadastrar")

        if enviado:
            if nome and formacao:
                caminho_antecedentes = salvar_arquivo_upload(
                    arquivo_antecedentes, nome, sufixo="_antecedentes"
                )
                caminho_curriculo = salvar_arquivo_upload(
                    curriculo, nome, sufixo="_curriculo"
                )
                dados = {
                    "nome": nome,
                    "data_nascimento": str(nascimento),
                    "endereco": endereco,
                    "tipo_cuidado": ", ".join(tipo_cuidado),
                    "formacao": formacao,
                    "antecedentes_criminais": antecedentes,
                    "antecedentes_arquivo": caminho_antecedentes,
                    "curriculo_arquivo": caminho_curriculo,
                    "disponibilidade_horas": horas,
                    "disponibilidade_horas_cod": COD_HORAS[horas],
                    "disponibilidade_fds": fds,
                    "disponibilidade_fds_cod": COD_SIM_NAO_FDS[fds],
                    "turno": turno,
                    "turno_cod": COD_TURNO[turno],
                    "disponibilidade_viagem": viagem,
                    "disponibilidade_viagem_cod": COD_VIAGEM[viagem],
                    "cursos": ", ".join(cursos),
                    "experiencia": experiencia,
                    "descricao": descricao,
                    "tipos_pacientes": ", ".join(tipos_pacientes),
                    "tipos_pacientes_cod": ", ".join(
                        str(COD_TIPOS_PACIENTES[t]) for t in tipos_pacientes
                    ),
                    "sexo_paciente": sexo_paciente,
                    "sexo_paciente_cod": COD_SEXO_PACIENTE[sexo_paciente],
                    "faixa_idade_paciente": ", ".join(faixa_idade_paciente),
                    "faixa_idade_paciente_cod": ", ".join(
                        str(COD_FAIXA_IDADE[f]) for f in faixa_idade_paciente
                    ),
                    "certidao_antecedentes": certidao,
                    "certidao_antecedentes_cod": COD_CERTIDAO[certidao],
                }
                inserir_cuidador(dados)
                st.success(
                    f"Cuidador {nome} cadastrado! Ele aparecerá na busca "
                    "assim que for aprovado pelo admin."
                )
            else:
                st.error("Preencha ao menos nome e formação.")

# --- Busca de cuidadores -----------------------------------------------
elif menu == "Buscar cuidadores":
    st.subheader("Buscar cuidadores")
    filtro = st.selectbox("Filtrar por tipo de cuidado", ["Todos"] + TIPOS_CUIDADO)
    resultados = listar_cuidadores(filtro)
    aprovados = [r for r in resultados if r["aprovado"] == 1]

    if not aprovados:
        st.info("Nenhum cuidador aprovado encontrado para esse filtro ainda.")
    for c in aprovados:
        with st.container(border=True):
            st.markdown(f"### {c['nome']}")
            st.write(f"**Tipo de cuidado:** {c['tipo_cuidado']}")
            st.write(f"**Formação:** {c['formacao']}")
            if c["cursos"]:
                st.write(f"**Cursos:** {c['cursos']}")
            st.write(
                f"**Disponibilidade:** {c['disponibilidade_horas']} · "
                f"Turno {c['turno']} · "
                f"Finais de semana: {c['disponibilidade_fds']} · "
                f"Viagem: {c['disponibilidade_viagem']}"
            )
            if c["tipos_pacientes"]:
                st.write(f"**Atende pacientes:** {c['tipos_pacientes']}")
            if c["faixa_idade_paciente"]:
                st.write(f"**Faixa etária atendida:** {c['faixa_idade_paciente']}")
            if c["descricao"]:
                st.write(f"**Descrição:** {c['descricao']}")
            st.write(f"**Endereço:** {c['endereco']}")

            with st.expander("Enviar mensagem para este cuidador"):
                with st.form(f"form_mensagem_{c['id']}", clear_on_submit=True):
                    nome_remetente = st.text_input("Seu nome", key=f"nome_{c['id']}")
                    texto_mensagem = st.text_area("Mensagem", key=f"msg_{c['id']}")
                    enviar = st.form_submit_button("Enviar")
                    if enviar:
                        if nome_remetente and texto_mensagem:
                            enviar_mensagem(nome_remetente, c["id"], texto_mensagem)
                            st.success("Mensagem enviada!")
                        else:
                            st.error("Preencha seu nome e a mensagem.")

# --- Mensagens recebidas (cuidador) ------------------------------------
elif menu == "Minhas mensagens":
    st.subheader("Minhas mensagens")
    cuidadores = listar_cuidadores()
    if not cuidadores:
        st.info("Nenhum cuidador cadastrado ainda.")
    else:
        nomes = {c["nome"]: c["id"] for c in cuidadores}
        nome_escolhido = st.selectbox("Selecione seu nome de cadastro", list(nomes.keys()))
        mensagens = listar_mensagens(nomes[nome_escolhido])
        if not mensagens:
            st.info("Nenhuma mensagem recebida ainda.")
        for m in mensagens:
            with st.container(border=True):
                st.write(f"**De:** {m['nome_remetente']} · {m['data_envio']}")
                st.write(m["mensagem"])

# --- Aprovação (simula o processo manual de verificação) --------------
elif menu == "Aprovar cuidadores (admin)":
    st.subheader("Aprovar cuidadores")
    st.caption(
        "Simula a verificação manual de antecedentes e formação antes de "
        "o cuidador aparecer na busca."
    )

    with st.expander("⚠️ Zona de manutenção (uso técnico)"):
        st.caption(
            "Use isso só quando o app.py for atualizado e der erro de "
            "coluna faltando (ex.: 'IndexError: No item with that key'). "
            "Isso apaga TODOS os dados cadastrados e recria o banco vazio."
        )
        confirmar_reset = st.checkbox("Sim, quero apagar tudo e recomeçar")
        if st.button("🗑️ Resetar banco de dados", disabled=not confirmar_reset):
            resetar_banco()
            st.success("Banco resetado! Recarregue a página.")
            st.rerun()

    pendentes = [c for c in listar_cuidadores() if c["aprovado"] == 0]

    if not pendentes:
        st.info("Não há cuidadores pendentes de aprovação.")
    for c in pendentes:
        with st.container(border=True):
            st.markdown(f"### {c['nome']}")
            st.write(f"**Formação:** {c['formacao']}")
            st.write(f"**Certidão de antecedentes:** {c['certidao_antecedentes']}")
            st.write(f"**Observações:** {c['antecedentes_criminais']}")
            if c["antecedentes_arquivo"]:
                st.write(f"**Arquivo anexado:** {os.path.basename(c['antecedentes_arquivo'])}")
                try:
                    with open(c["antecedentes_arquivo"], "rb") as f:
                        st.download_button(
                            "Baixar arquivo",
                            f,
                            file_name=os.path.basename(c["antecedentes_arquivo"]),
                            key=f"download_{c['id']}",
                        )
                except FileNotFoundError:
                    st.caption("(arquivo não encontrado na pasta)")
            if c["curriculo_arquivo"]:
                st.write(f"**Currículo anexado:** {os.path.basename(c['curriculo_arquivo'])}")
                try:
                    with open(c["curriculo_arquivo"], "rb") as f:
                        st.download_button(
                            "Baixar currículo",
                            f,
                            file_name=os.path.basename(c["curriculo_arquivo"]),
                            key=f"download_curriculo_{c['id']}",
                        )
                except FileNotFoundError:
                    st.caption("(arquivo não encontrado na pasta)")
            col_aprovar, col_reprovar = st.columns(2)
            with col_aprovar:
                if st.button("✅ Aprovar", key=f"aprovar_{c['id']}"):
                    aprovar_cuidador(c["id"])
                    st.rerun()
            with col_reprovar:
                if st.button("❌ Reprovar", key=f"reprovar_{c['id']}"):
                    reprovar_cuidador(c["id"])
                    st.rerun()
