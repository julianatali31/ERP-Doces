class Funcionario:
    def __init__(self, nome, salario_base):
        self.__nome = nome
        self.__salario_base = salario_base

    @property
    def nome(self):
        return self.__nome

    @property
    def salario_base(self):
        return self.__salario_base

    def calcular_salario(self):
        return self.__salario_base

    def exibir_dados(self):
        return f"{self.nome} | {self.__class__.__name__} | R$ {self.calcular_salario():.2f}"


class Gerente(Funcionario):
    def __init__(self, nome, salario_base, tamanho_equipe):
        super().__init__(nome, salario_base)
        self.__tamanho_equipe = tamanho_equipe

    @property
    def tamanho_equipe(self):
        return self.__tamanho_equipe

    def calcular_salario(self):
        salario = super().calcular_salario()
        if self.__tamanho_equipe >= 5:
            salario += self.salario_base * 0.2
        return salario

    def exibir_dados(self):
        return (
            f"{self.nome} | {self.__class__.__name__} "
            f"({self.tamanho_equipe} pessoas) | R$ {self.calcular_salario():.2f}"
        )


class Diretor(Gerente):
    def __init__(self, nome, salario_base, tamanho_equipe, participacao):
        super().__init__(nome, salario_base, tamanho_equipe)
        self.__participacao = participacao

    @property
    def participacao(self):
        return self.__participacao

    def calcular_salario(self):
        return super().calcular_salario() + self.__participacao

    def exibir_dados(self):
        return f"{self.nome} | {self.__class__.__name__} | R$ {self.calcular_salario():.2f}"


if __name__ == "__main__":
    ana = Funcionario("Ana", 3000)
    bruno = Gerente("Bruno", 6000, 8)
    carla = Gerente("Carla", 6000, 3)
    diego = Diretor("Diego", 12000, 20, 5000)

    funcionarios = [ana, bruno, carla, diego]

    for funcionario in funcionarios:
        print(funcionario.exibir_dados())
