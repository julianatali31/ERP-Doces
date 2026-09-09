from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UNIDADES = Literal["g", "kg", "ml", "l", "unidade"]
FORMAS_PAGAMENTO = Literal["dinheiro", "pix", "debito", "credito", "transferencia", "fiado"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ clientes
class ClienteBase(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    email: str | None = None
    telefone: str | None = None
    observacoes: str | None = None
    ativo: bool = True


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nome: str | None = None
    email: str | None = None
    telefone: str | None = None
    observacoes: str | None = None
    ativo: bool | None = None


class ClienteOut(ClienteBase, ORMModel):
    id: int
    criado_em: datetime


# -------------------------------------------------------------- ingredientes
class IngredienteBase(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    categoria: str | None = None
    unidade_medida: UNIDADES = "g"
    quantidade_atual: float = 0
    estoque_minimo: float = 0
    custo_unitario: float = Field(default=0, ge=0)
    fornecedor: str | None = None
    observacoes: str | None = None
    ativo: bool = True


class IngredienteCreate(IngredienteBase):
    pass


class IngredienteUpdate(BaseModel):
    nome: str | None = None
    categoria: str | None = None
    unidade_medida: UNIDADES | None = None
    quantidade_atual: float | None = None
    estoque_minimo: float | None = None
    custo_unitario: float | None = Field(default=None, ge=0)
    fornecedor: str | None = None
    observacoes: str | None = None
    ativo: bool | None = None


class IngredienteOut(IngredienteBase, ORMModel):
    id: int
    atualizado_em: datetime


class IngredientePrecoCompra(BaseModel):
    """Converte o preco da embalagem em custo por unidade de medida."""

    preco_pago: float = Field(gt=0, description="Quanto custou a embalagem inteira")
    quantidade_embalagem: float = Field(gt=0, description="Quanto vem na embalagem")
    unidade_embalagem: UNIDADES
    lancar_entrada: bool = Field(default=True, description="Somar a quantidade ao estoque")


# ------------------------------------------------------------------ receitas
class ReceitaIngredienteIn(BaseModel):
    ingrediente_id: int
    quantidade: float = Field(gt=0)
    unidade: UNIDADES = "g"
    observacao: str | None = None


class ReceitaIngredienteOut(ORMModel):
    id: int
    ingrediente_id: int
    quantidade: float
    unidade: str
    observacao: str | None = None
    ingrediente_nome: str | None = None
    custo_linha: float = 0


class ReceitaBase(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    categoria: str | None = None
    descricao: str | None = None
    rendimento: float = Field(default=1, gt=0)
    unidade_rendimento: str = "unidades"
    peso_final_g: float | None = None
    tempo_preparo_min: int | None = None
    preco_venda_sugerido: float | None = None
    ativo: bool = True


class ReceitaCreate(ReceitaBase):
    ingredientes: list[ReceitaIngredienteIn] = []


class ReceitaUpdate(BaseModel):
    nome: str | None = None
    categoria: str | None = None
    descricao: str | None = None
    rendimento: float | None = Field(default=None, gt=0)
    unidade_rendimento: str | None = None
    peso_final_g: float | None = None
    tempo_preparo_min: int | None = None
    preco_venda_sugerido: float | None = None
    ativo: bool | None = None
    ingredientes: list[ReceitaIngredienteIn] | None = None


class ReceitaOut(ReceitaBase, ORMModel):
    id: int
    custo_total: float
    custo_unitario: float
    atualizado_em: datetime


class ReceitaDetalhe(ReceitaOut):
    ingredientes: list[ReceitaIngredienteOut] = []


class ProducaoIn(BaseModel):
    lotes: float = Field(default=1, gt=0, description="Quantas receitas completas produzir")
    observacao: str | None = None


class ProducaoOut(BaseModel):
    receita: str
    lotes: float
    unidades_produzidas: float
    custo_total: float
    ingredientes_consumidos: list[dict]


# ------------------------------------------------------------------ produtos
class ProdutoBase(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    categoria: str | None = None
    descricao: str | None = None
    receita_id: int | None = None
    preco_venda: float = Field(default=0, ge=0)
    ativo: bool = True


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(BaseModel):
    nome: str | None = None
    categoria: str | None = None
    descricao: str | None = None
    receita_id: int | None = None
    preco_venda: float | None = Field(default=None, ge=0)
    ativo: bool | None = None


class ProdutoOut(ProdutoBase, ORMModel):
    id: int
    custo_unitario: float
    margem_valor: float
    margem_lucro: float
    receita_nome: str | None = None


class PrecoSugerido(BaseModel):
    produto: str
    custo_unitario: float
    margem_desejada: float
    preco_sugerido: float
    preco_atual: float


# -------------------------------------------------------------------- vendas
class VendaItemIn(BaseModel):
    produto_id: int | None = None
    descricao: str | None = None
    quantidade: float = Field(gt=0)
    preco_unitario: float | None = Field(default=None, ge=0)


class VendaItemOut(ORMModel):
    id: int
    produto_id: int | None
    descricao: str | None
    quantidade: float
    preco_unitario: float
    custo_unitario: float
    subtotal: float


class VendaCreate(BaseModel):
    cliente_id: int | None = None
    itens: list[VendaItemIn] = Field(min_length=1)
    desconto: float = Field(default=0, ge=0)
    forma_pagamento: FORMAS_PAGAMENTO = "dinheiro"
    status: Literal["pendente", "concluida", "cancelada"] = "concluida"
    observacoes: str | None = None
    data_venda: datetime | None = None
    baixar_estoque: bool = Field(
        default=True, description="Consome os ingredientes das receitas vendidas"
    )


class VendaOut(ORMModel):
    id: int
    cliente_id: int | None
    cliente_nome: str | None = None
    data_venda: datetime
    subtotal: float
    desconto: float
    total: float
    custo_total: float
    lucro: float
    forma_pagamento: str
    status: str
    observacoes: str | None
    itens: list[VendaItemOut] = []


# -------------------------------------------------------------------- estoque
class MovimentacaoIn(BaseModel):
    ingrediente_id: int
    tipo: Literal["entrada", "saida", "ajuste", "perda"]
    quantidade: float = Field(gt=0, description="Em 'ajuste', e a quantidade final desejada")
    custo_unitario: float | None = Field(default=None, ge=0)
    motivo: str | None = None
    referencia: str | None = None


class MovimentacaoOut(ORMModel):
    id: int
    ingrediente_id: int
    ingrediente_nome: str | None = None
    tipo: str
    quantidade: float
    quantidade_anterior: float
    quantidade_nova: float
    custo_unitario: float
    custo_total: float
    motivo: str | None
    referencia: str | None
    criado_em: datetime


class EstoqueOut(BaseModel):
    id: int
    nome: str
    categoria: str | None
    unidade_medida: str
    quantidade_atual: float
    estoque_minimo: float
    custo_unitario: float
    valor_em_estoque: float
    fornecedor: str | None
    ativo: bool
    situacao: str


# ----------------------------------------------------------------- financeiro
class TransacaoBase(BaseModel):
    tipo: Literal["receita", "despesa"]
    categoria: str = "geral"
    descricao: str = Field(min_length=1, max_length=255)
    valor: float = Field(ge=0)
    data_transacao: date | None = None
    forma_pagamento: str = "dinheiro"
    status: Literal["pendente", "pago", "cancelado"] = "pago"
    observacoes: str | None = None


class TransacaoCreate(TransacaoBase):
    pass


class TransacaoUpdate(BaseModel):
    tipo: Literal["receita", "despesa"] | None = None
    categoria: str | None = None
    descricao: str | None = None
    valor: float | None = Field(default=None, ge=0)
    data_transacao: date | None = None
    forma_pagamento: str | None = None
    status: Literal["pendente", "pago", "cancelado"] | None = None
    observacoes: str | None = None


class TransacaoOut(TransacaoBase, ORMModel):
    id: int
    venda_id: int | None = None
    criado_em: datetime


# ------------------------------------------------------------------ dashboard
class DashboardKpis(BaseModel):
    faturamento_hoje: float
    faturamento_mes: float
    lucro_mes: float
    vendas_mes: int
    ticket_medio_mes: float
    itens_estoque_baixo: int
    valor_estoque: float
    total_produtos: int
    total_receitas: int
    total_clientes: int
    despesas_mes: float
    saldo_mes: float


class SerieTemporal(BaseModel):
    label: str
    valor: float
    valor_secundario: float = 0


# --------------------------------------------------------------- configuracoes
class ConfiguracaoOut(ORMModel):
    id: int
    chave: str
    valor: str | None
    tipo: str
    grupo: str
    descricao: str | None


class ConfiguracaoUpdate(BaseModel):
    valor: str


# ------------------------------------------------------------------ analytics
class PontoFaturamento(BaseModel):
    """Um ponto da série de faturamento, já agrupado por semana ou mês."""

    periodo: str
    inicio: date
    faturamento: float
    custo: float
    lucro: float
    vendas: int
    ticket_medio: float


class IndicadorComparado(BaseModel):
    """Valor do período escolhido ao lado do período anterior de mesmo tamanho.

    `variacao_pct` fica nulo quando não havia base de comparação (anterior = 0),
    porque nesse caso a variação percentual não significa nada.
    """

    atual: float
    anterior: float
    variacao_pct: float | None = None


class ComparativoPeriodo(BaseModel):
    inicio: date
    fim: date
    inicio_anterior: date
    fim_anterior: date
    faturamento: IndicadorComparado
    lucro: IndicadorComparado
    vendas: IndicadorComparado
    ticket_medio: IndicadorComparado


class ProdutoRanking(BaseModel):
    produto_id: int | None
    produto: str
    unidades: float
    faturamento: float
    lucro: float
    participacao_pct: float


class MesSazonalidade(BaseModel):
    mes: int
    nome: str
    faturamento_medio: float
    faturamento_total: float
    vendas: int
    anos_com_dados: int
    recesso: bool
