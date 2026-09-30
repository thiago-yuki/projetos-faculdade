import os
import sqlite3
from contextlib import closing

from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = "chave-de-desenvolvimento"

CAMINHO_BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "problemas.db")

CATEGORIAS = ["navegacao", "formulario", "feedback", "acessibilidade", "outro"]
GRAVIDADES = ["baixa", "media", "alta"]


def conectar():
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    return conexao


def inicializar_banco():
    with closing(conectar()) as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS problemas (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo    TEXT NOT NULL CHECK (length(titulo) <= 120),
                sistema   TEXT NOT NULL,
                categoria TEXT NOT NULL CHECK (categoria IN
                          ('navegacao', 'formulario', 'feedback', 'acessibilidade', 'outro')),
                gravidade TEXT NOT NULL CHECK (gravidade IN ('baixa', 'media', 'alta')),
                descricao TEXT NOT NULL,
                criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conexao.commit()


def validar(titulo, sistema, categoria, gravidade, descricao):
    obrigatorios = [
        ("Título", titulo),
        ("Sistema", sistema),
        ("Categoria", categoria),
        ("Gravidade", gravidade),
        ("Descrição", descricao),
    ]
    for nome, valor in obrigatorios:
        if not valor:
            return f'O campo "{nome}" é obrigatório. Preencha antes de salvar.'
    if len(titulo) > 120:
        return 'O campo "Título" aceita no máximo 120 caracteres.'
    if categoria not in CATEGORIAS:
        return "Categoria inválida. Use: " + ", ".join(CATEGORIAS) + "."
    if gravidade not in GRAVIDADES:
        return "Gravidade inválida. Use: " + ", ".join(GRAVIDADES) + "."
    return None


def pagina_listagem(form=None, status=200):
    # Captura o filtro de gravidade da query string (ex: ?gravidade=alta)
    gravidade_filtro = request.args.get("gravidade", "").strip()

    with closing(conectar()) as conexao:
        if gravidade_filtro in GRAVIDADES:
            # SQL com parâmetro ? para filtragem segura
            problemas = conexao.execute(
                "SELECT id, titulo, sistema, categoria, gravidade, criado_em "
                "FROM problemas WHERE gravidade = ? ORDER BY id DESC",
                (gravidade_filtro,),
            ).fetchall()
        else:
            problemas = conexao.execute(
                "SELECT id, titulo, sistema, categoria, gravidade, criado_em "
                "FROM problemas ORDER BY id DESC"
            ).fetchall()

    pagina = render_template(
        "index.html",
        problemas=problemas,
        form=form or {},
        categorias=CATEGORIAS,
        gravidades=GRAVIDADES,
        gravidade_filtro=gravidade_filtro,
    )
    return pagina, status


@app.route("/")
def listar_problemas():
    return pagina_listagem()


@app.route("/problemas", methods=["POST"])
def cadastrar_problema():
    campos = ["titulo", "sistema", "categoria", "gravidade", "descricao"]
    dados = {campo: request.form.get(campo, "").strip() for campo in campos}

    erro = validar(**dados)
    if erro:
        flash(erro, "erro")
        return pagina_listagem(dados, 400)

    try:
        with closing(conectar()) as conexao:
            conexao.execute(
                "INSERT INTO problemas (titulo, sistema, categoria, gravidade, descricao) "
                "VALUES (?, ?, ?, ?, ?)",
                (dados["titulo"], dados["sistema"], dados["categoria"],
                 dados["gravidade"], dados["descricao"]),
            )
            conexao.commit()
    except sqlite3.IntegrityError:
        flash("O banco recusou os dados. Confira categoria, gravidade e tamanho do título.", "erro")
        return pagina_listagem(dados, 400)

    flash("Problema registrado com sucesso.", "sucesso")
    return redirect(url_for("listar_problemas"))


def buscar_problema(problema_id):
    with closing(conectar()) as conexao:
        return conexao.execute(
            "SELECT id, titulo, sistema, categoria, gravidade, descricao "
            "FROM problemas WHERE id = ?",
            (problema_id,),
        ).fetchone()


def pagina_edicao(problema_id, dados, status=200):
    pagina = render_template(
        "editar.html",
        problema_id=problema_id,
        form=dados,
        categorias=CATEGORIAS,
        gravidades=GRAVIDADES,
    )
    return pagina, status


@app.route("/problemas/<int:problema_id>/editar", methods=["GET", "POST"])
def editar_problema(problema_id):
    problema = buscar_problema(problema_id)
    if problema is None:
        flash(f"Problema #{problema_id} não encontrado. Pode ter sido removido.", "erro")
        return redirect(url_for("listar_problemas"))

    if request.method == "GET":
        return pagina_edicao(problema_id, dict(problema))

    campos = ["titulo", "sistema", "categoria", "gravidade", "descricao"]
    dados = {campo: request.form.get(campo, "").strip() for campo in campos}

    erro = validar(**dados)
    if erro:
        flash(erro, "erro")
        return pagina_edicao(problema_id, dados, 400)

    try:
        with closing(conectar()) as conexao:
            cursor = conexao.execute(
                "UPDATE problemas SET titulo = ?, sistema = ?, categoria = ?, "
                "gravidade = ?, descricao = ? WHERE id = ?",
                (dados["titulo"], dados["sistema"], dados["categoria"],
                 dados["gravidade"], dados["descricao"], problema_id),
            )
            conexao.commit()
            atualizados = cursor.rowcount
    except sqlite3.IntegrityError:
        flash("O banco recusou os dados. Confira categoria, gravidade e tamanho do título.", "erro")
        return pagina_edicao(problema_id, dados, 400)

    if atualizados == 0:
        flash(f"Problema #{problema_id} não encontrado. Pode ter sido removido.", "erro")
    else:
        flash("Problema atualizado com sucesso.", "sucesso")
    return redirect(url_for("listar_problemas"))


@app.route("/problemas/<int:problema_id>/excluir", methods=["POST"])
def excluir_problema(problema_id):
    with closing(conectar()) as conexao:
        cursor = conexao.execute("DELETE FROM problemas WHERE id = ?", (problema_id,))
        conexao.commit()
        removidos = cursor.rowcount

    if removidos == 0:
        flash(f"Problema #{problema_id} não encontrado. Ele pode já ter sido removido.", "erro")
    else:
        flash(f"Problema #{problema_id} excluído com sucesso.", "sucesso")
    return redirect(url_for("listar_problemas"))


if __name__ == "__main__":
    inicializar_banco()
    app.run(host="127.0.0.1", port=5000, debug=True)