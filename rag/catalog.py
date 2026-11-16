"""Metadados dos documentos do corpus (origem, órgão, ano, licença/URL)."""
from __future__ import annotations

DOCUMENTS: dict[str, dict] = {
    "ms_fiocruz_manual_primeiros_socorros": {
        "title": "Manual de Primeiros Socorros",
        "organization": "Ministério da Saúde / Fiocruz",
        "year": 2003,
        "category": "manual",
        "url": "https://bvsms.saude.gov.br/bvs/publicacoes/manual_primeiros_socorros.pdf",
    },
    "ufs_primeiros_socorros_para_todos": {
        "title": "Primeiros Socorros para Todos!",
        "organization": "Universidade Federal de Sergipe (Editora Amplla, CC BY 4.0)",
        "year": 2022,
        "category": "livro",
        "url": "https://ri.ufs.br/bitstream/riufs/16695/2/PrimeirosSocorrosParaTodos.pdf",
    },
    "ufmg_apostila_primeiros_socorros": {
        "title": "Noções de Primeiros Socorros em Ambientes de Saúde",
        "organization": "UFMG - DAST/PRORH",
        "year": 2021,
        "category": "apostila",
        "url": "https://www.ufmg.br/prorh/wp-content/uploads/2021/10/Apostila-de-Primeiros-Socorros-DAST.pdf",
    },
    "goias_cartilha_primeiros_socorros": {
        "title": "Cartilha de Primeiros Socorros",
        "organization": "Corpo de Bombeiros Militar de Goiás",
        "year": 2023,
        "category": "cartilha",
        "url": "https://goias.gov.br/esporte/wp-content/uploads/sites/53/2023/09/CartilhaPrimeirosSocorros-c11.pdf",
    },
    "cbpmesp_nocoes_primeiros_socorros": {
        "title": "Noções de Primeiros Socorros",
        "organization": "Corpo de Bombeiros da PM de São Paulo",
        "year": None,
        "category": "slides",
        "url": "https://eadtec.cps.sp.gov.br/midiateca/arquivos/nocoes_primeiros_socorros.pdf",
    },
    "sobrasa_abc_primeiros_socorros": {
        "title": "ABC dos Primeiros Socorros",
        "organization": "SOBRASA - Sociedade Brasileira de Salvamento Aquático",
        "year": None,
        "category": "cartilha",
        "url": "https://sobrasa.org/dowloads/Primeiros_socorros/manual_ABC_dos_Primeiros_Socorros.pdf",
    },
    "mdh_prevencao_acidentes_domesticos": {
        "title": "Cartilha de Prevenção aos Acidentes Domésticos",
        "organization": "Ministério dos Direitos Humanos e da Cidadania",
        "year": 2022,
        "category": "cartilha",
        "url": "https://www.gov.br/mdh/pt-br/navegue-por-temas/crianca-e-adolescente/publicacoes/cartilha-de-prevencao-aos-acidentes-domesticos-2022.pdf",
    },
}
