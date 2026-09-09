from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Configuracao(Base):
    __tablename__ = "configuracoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chave: Mapped[str] = mapped_column(String(100), unique=True)
    valor: Mapped[str | None] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String(20), default="string")
    grupo: Mapped[str] = mapped_column(String(50), default="geral")
    descricao: Mapped[str | None] = mapped_column(Text)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    tipo: Mapped[str] = mapped_column(String(20), default="ingrediente")
    cor: Mapped[str] = mapped_column(String(9), default="#7C3AED")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(150))
    telefone: Mapped[str | None] = mapped_column(String(30))
    observacoes: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Ingrediente(Base):
    __tablename__ = "ingredientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), unique=True)
    categoria: Mapped[str | None] = mapped_column(String(100))
    unidade_medida: Mapped[str] = mapped_column(String(20), default="g")
    quantidade_atual: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    estoque_minimo: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 6), default=0)
    fornecedor: Mapped[str | None] = mapped_column(String(150))
    observacoes: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Receita(Base):
    __tablename__ = "receitas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), unique=True)
    categoria: Mapped[str | None] = mapped_column(String(100))
    descricao: Mapped[str | None] = mapped_column(Text)
    rendimento: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=1)
    unidade_rendimento: Mapped[str] = mapped_column(String(30), default="unidades")
    peso_final_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    tempo_preparo_min: Mapped[int | None] = mapped_column(Integer)
    preco_venda_sugerido: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    custo_total: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ingredientes: Mapped[list["ReceitaIngrediente"]] = relationship(
        back_populates="receita", cascade="all, delete-orphan", lazy="selectin"
    )


class ReceitaIngrediente(Base):
    __tablename__ = "receita_ingredientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receita_id: Mapped[int] = mapped_column(ForeignKey("receitas.id", ondelete="CASCADE"))
    ingrediente_id: Mapped[int] = mapped_column(ForeignKey("ingredientes.id", ondelete="RESTRICT"))
    quantidade: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unidade: Mapped[str] = mapped_column(String(20), default="g")
    observacao: Mapped[str | None] = mapped_column(Text)

    receita: Mapped["Receita"] = relationship(back_populates="ingredientes")
    ingrediente: Mapped["Ingrediente"] = relationship(lazy="joined")


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), unique=True)
    categoria: Mapped[str | None] = mapped_column(String(100))
    descricao: Mapped[str | None] = mapped_column(Text)
    receita_id: Mapped[int | None] = mapped_column(ForeignKey("receitas.id", ondelete="SET NULL"))
    preco_venda: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    margem_valor: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    margem_lucro: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    receita: Mapped["Receita | None"] = relationship(lazy="joined")


class Venda(Base):
    __tablename__ = "vendas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id", ondelete="SET NULL"))
    data_venda: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    desconto: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    custo_total: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    lucro: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    forma_pagamento: Mapped[str] = mapped_column(String(30), default="dinheiro")
    status: Mapped[str] = mapped_column(String(20), default="concluida")
    observacoes: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    itens: Mapped[list["VendaItem"]] = relationship(
        back_populates="venda", cascade="all, delete-orphan", lazy="selectin"
    )
    cliente: Mapped["Cliente | None"] = relationship(lazy="joined")


class VendaItem(Base):
    __tablename__ = "venda_itens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venda_id: Mapped[int] = mapped_column(ForeignKey("vendas.id", ondelete="CASCADE"))
    produto_id: Mapped[int | None] = mapped_column(ForeignKey("produtos.id", ondelete="SET NULL"))
    descricao: Mapped[str | None] = mapped_column(String(150))
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    venda: Mapped["Venda"] = relationship(back_populates="itens")


class MovimentacaoEstoque(Base):
    __tablename__ = "movimentacao_estoque"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingrediente_id: Mapped[int] = mapped_column(ForeignKey("ingredientes.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(20))
    quantidade: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    quantidade_anterior: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    quantidade_nova: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    custo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 6), default=0)
    custo_total: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    motivo: Mapped[str | None] = mapped_column(Text)
    referencia: Mapped[str | None] = mapped_column(String(100))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ingrediente: Mapped["Ingrediente"] = relationship(lazy="joined")


class TransacaoFinanceira(Base):
    __tablename__ = "transacoes_financeiras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))
    categoria: Mapped[str] = mapped_column(String(100), default="geral")
    descricao: Mapped[str] = mapped_column(String(255))
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    data_transacao: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    forma_pagamento: Mapped[str] = mapped_column(String(30), default="dinheiro")
    venda_id: Mapped[int | None] = mapped_column(ForeignKey("vendas.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), default="pago")
    observacoes: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
