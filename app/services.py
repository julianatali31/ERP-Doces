from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ingrediente, MovimentacaoEstoque, Receita, ReceitaIngrediente

_FATORES = {
    ("kg", "g"): Decimal(1000),
    ("g", "kg"): Decimal(1) / Decimal(1000),
    ("l", "ml"): Decimal(1000),
    ("ml", "l"): Decimal(1) / Decimal(1000),
}


def converter_unidade(quantidade: Decimal, de: str, para: str) -> Decimal:
    """Espelha a funcao converter_unidade() do banco."""
    if de == para:
        return quantidade
    return quantidade * _FATORES.get((de, para), Decimal(1))


async def registrar_movimentacao(
    db: AsyncSession,
    ingrediente: Ingrediente,
    tipo: str,
    quantidade: Decimal,
    *,
    custo_unitario: Decimal | None = None,
    motivo: str | None = None,
    referencia: str | None = None,
) -> MovimentacaoEstoque:
    """Aplica a movimentacao no estoque do insumo e grava o historico.

    Em 'ajuste', `quantidade` e a contagem final do estoque, nao a diferenca.
    """
    anterior = Decimal(ingrediente.quantidade_atual)
    custo = Decimal(custo_unitario) if custo_unitario is not None else Decimal(ingrediente.custo_unitario)

    if tipo == "entrada":
        nova = anterior + quantidade
    elif tipo in ("saida", "perda"):
        nova = anterior - quantidade
    else:
        nova = quantidade
        quantidade = nova - anterior

    ingrediente.quantidade_atual = nova
    if tipo == "entrada" and custo_unitario is not None:
        ingrediente.custo_unitario = custo

    mov = MovimentacaoEstoque(
        ingrediente_id=ingrediente.id,
        tipo=tipo,
        quantidade=quantidade,
        quantidade_anterior=anterior,
        quantidade_nova=nova,
        custo_unitario=custo,
        custo_total=abs(quantidade) * custo,
        motivo=motivo,
        referencia=referencia,
    )
    db.add(mov)
    return mov


async def consumir_receita(
    db: AsyncSession,
    receita_id: int,
    fator: Decimal,
    *,
    motivo: str,
    referencia: str | None = None,
) -> list[dict]:
    """Baixa do estoque os insumos de `fator` receitas completas.

    fator = 1 consome a receita inteira; 0.5 consome meia receita.
    Um fator negativo estorna (devolve os insumos ao estoque).
    Retorna o que foi movimentado, por insumo.
    """
    tipo = "saida" if fator >= 0 else "entrada"
    fator = abs(fator)

    linhas = (
        await db.execute(
            select(ReceitaIngrediente, Ingrediente)
            .join(Ingrediente, Ingrediente.id == ReceitaIngrediente.ingrediente_id)
            .where(ReceitaIngrediente.receita_id == receita_id)
        )
    ).all()

    consumidos = []
    for item, ingrediente in linhas:
        qtd = converter_unidade(Decimal(item.quantidade), item.unidade, ingrediente.unidade_medida) * fator
        await registrar_movimentacao(
            db,
            ingrediente,
            tipo,
            qtd,
            motivo=motivo,
            referencia=referencia,
        )
        consumidos.append(
            {
                "ingrediente_id": ingrediente.id,
                "ingrediente": ingrediente.nome,
                "quantidade": float(qtd),
                "unidade": ingrediente.unidade_medida,
                "custo": float(qtd * Decimal(ingrediente.custo_unitario)),
                "estoque_restante": float(ingrediente.quantidade_atual),
            }
        )
    return consumidos


async def receita_por_id(db: AsyncSession, receita_id: int) -> Receita | None:
    return await db.get(Receita, receita_id)
