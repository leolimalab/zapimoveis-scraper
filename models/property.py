"""Modelo de dados para imóveis."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List


@dataclass
class Property:
    """Representa um imóvel extraído do ZapImóveis."""

    # Identificação
    id: str
    url: str

    # Localização
    local: str  # Bairro
    endereco_completo: str  # Rua, número - Bairro, Cidade - UF
    rua: str
    numero: str
    cidade: str
    estado: str

    # Características do imóvel
    tamanho_m2: int
    quartos: int
    banheiros: int
    vagas: int
    tipo_imovel: str  # Apartamento, Kitnet, etc.

    # Valores
    preco: float
    condominio: float
    iptu: float

    # Descrição
    titulo: str
    descricao: str

    # Características
    caracteristicas_imovel: List[str] = field(default_factory=list)
    caracteristicas_condominio: List[str] = field(default_factory=list)
    pets_permitidos: Optional[bool] = None

    # Anunciante
    anunciante: str = ""
    anunciante_tipo: str = ""  # Imobiliária, Proprietário, etc.
    anunciante_contato: str = ""

    # Datas
    data_publicacao: Optional[str] = None
    data_atualizacao: Optional[str] = None
    data_extracao: datetime = field(default_factory=datetime.now)

    # Avaliação
    avaliacao: Optional[float] = None

    # Imagens
    imagens: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Converte para dicionário."""
        data = asdict(self)
        data["data_extracao"] = self.data_extracao.isoformat()
        data["caracteristicas_imovel"] = "; ".join(self.caracteristicas_imovel)
        data["caracteristicas_condominio"] = "; ".join(self.caracteristicas_condominio)
        data["imagens"] = "; ".join(self.imagens[:5])  # Limita a 5 imagens
        return data

    def to_csv_row(self) -> dict:
        """Converte para linha de CSV com formatação brasileira."""
        return {
            "id": self.id,
            "tipo_imovel": self.tipo_imovel,
            "endereco_completo": self.endereco_completo,
            "rua": self.rua,
            "numero": self.numero,
            "bairro": self.local,
            "cidade": self.cidade,
            "estado": self.estado,
            "tamanho_m2": self.tamanho_m2,
            "quartos": self.quartos,
            "banheiros": self.banheiros,
            "vagas": self.vagas,
            "preco": f"{self.preco:.2f}".replace(".", ","),
            "condominio": f"{self.condominio:.2f}".replace(".", ","),
            "iptu": f"{self.iptu:.2f}".replace(".", ","),
            "titulo": self.titulo,
            "descricao": self.descricao[:500] if self.descricao else "",
            "caracteristicas_imovel": "; ".join(self.caracteristicas_imovel),
            "caracteristicas_condominio": "; ".join(self.caracteristicas_condominio),
            "pets_permitidos": "Sim" if self.pets_permitidos else ("Não" if self.pets_permitidos is False else ""),
            "anunciante": self.anunciante,
            "anunciante_tipo": self.anunciante_tipo,
            "anunciante_contato": self.anunciante_contato,
            "data_publicacao": self.data_publicacao or "",
            "data_atualizacao": self.data_atualizacao or "",
            "data_extracao": self.data_extracao.strftime("%d/%m/%Y %H:%M:%S"),
            "avaliacao": str(self.avaliacao) if self.avaliacao else "",
            "url": self.url,
        }

    @classmethod
    def from_schema_org(cls, item: dict) -> Optional["Property"]:
        """Cria Property a partir de dados do schema.org."""
        try:
            apt = item.get("item", {})

            listing_id = str(apt.get("@id", ""))
            name = apt.get("name", "")
            url = apt.get("url", "")
            description = apt.get("description", "")
            apt_type = apt.get("@type", "Apartment")

            # Tipo de imóvel
            tipo_map = {
                "Apartment": "Apartamento",
                "House": "Casa",
                "SingleFamilyResidence": "Casa",
            }
            tipo_imovel = tipo_map.get(apt_type, apt_type)
            if "kitnet" in name.lower() or "conjugado" in name.lower():
                tipo_imovel = "Kitnet/Conjugado"

            # Endereço
            address = apt.get("address", {})
            street = address.get("streetAddress", "")
            city = address.get("addressLocality", "Rio de Janeiro")
            state = address.get("addressRegion", "RJ")

            # Extrai número da rua se disponível
            numero = ""
            rua = street

            # Bairro
            neighborhood = "Leme"
            if "Copacabana" in name or "Copacabana" in street:
                neighborhood = "Copacabana"

            # Endereço completo
            endereco_completo = f"{street} - {neighborhood}, {city} - {state}" if street else f"{neighborhood}, {city} - {state}"

            # Quartos e banheiros
            bedrooms = apt.get("numberOfBedrooms", 0) or apt.get("numberOfRooms", 0) or 0
            bathrooms = apt.get("numberOfBathroomsTotal", 0) or 0

            # Área
            floor_size = apt.get("floorSize", {})
            area = floor_size.get("value", 0) if isinstance(floor_size, dict) else 0

            # Preço e taxas
            offers = apt.get("offers", {})
            price = float(offers.get("price", 0) or 0)

            # Taxa de condomínio
            condo_fee = 0.0
            property_value = offers.get("propertyValue", {})
            if isinstance(property_value, dict):
                if "Condominium" in property_value.get("name", ""):
                    condo_fee = float(property_value.get("value", 0) or 0)

            # Vagas
            vagas = 0
            if "vaga" in name.lower():
                import re
                match = re.search(r'(\d+)\s*vaga', name.lower())
                if match:
                    vagas = int(match.group(1))

            # Características do imóvel (amenityFeature)
            caracteristicas = []
            amenities = apt.get("amenityFeature", [])
            amenity_translations = {
                "Kitchen Cabinets": "Armários na cozinha",
                "Blindex Box": "Box Blindex",
                "Bathroom Cabinets": "Armários no banheiro",
                "Large Window": "Janelas grandes",
                "Furnished": "Mobiliado",
                "Intercom": "Interfone",
                "Elevator": "Elevador",
                "Builtin Wardrobe": "Armários embutidos",
                "Kitchen": "Cozinha",
                "Concierge 24h": "Portaria 24h",
                "Heating": "Aquecimento",
                "Pets Allowed": "Aceita pets",
                "Air Conditioning": "Ar condicionado",
                "Balcony": "Varanda",
                "Pool": "Piscina",
                "Gym": "Academia",
                "Barbecue": "Churrasqueira",
                "Playground": "Playground",
                "Party Room": "Salão de festas",
                "Sauna": "Sauna",
                "Service Area": "Área de serviço",
                "Laundry": "Lavanderia",
                "Garden": "Jardim",
                "Garage": "Garagem",
            }
            for amenity in amenities:
                if isinstance(amenity, dict):
                    value = amenity.get("value", "")
                    translated = amenity_translations.get(value, value)
                    if translated:
                        caracteristicas.append(translated)

            # Pets permitidos
            pets = apt.get("petsAllowed")

            # Imagens
            images = apt.get("image", [])
            if isinstance(images, str):
                images = [images]

            return cls(
                id=listing_id,
                url=url,
                local=neighborhood,
                endereco_completo=endereco_completo,
                rua=rua,
                numero=numero,
                cidade=city,
                estado=state,
                tamanho_m2=int(area) if area else 0,
                quartos=int(bedrooms) if bedrooms else 0,
                banheiros=int(bathrooms) if bathrooms else 0,
                vagas=vagas,
                tipo_imovel=tipo_imovel,
                preco=price,
                condominio=condo_fee,
                iptu=0.0,  # Será extraído da página de detalhe
                titulo=name,
                descricao=description,
                caracteristicas_imovel=caracteristicas,
                caracteristicas_condominio=[],  # Será extraído da página de detalhe
                pets_permitidos=pets,
                imagens=images[:10] if images else [],
            )

        except Exception as e:
            return None

    @staticmethod
    def _parse_price(value) -> float:
        """Converte valor de preço para float."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = "".join(c for c in value if c.isdigit() or c in ".,")
            if "," in cleaned and "." in cleaned:
                if cleaned.rfind(",") > cleaned.rfind("."):
                    cleaned = cleaned.replace(".", "").replace(",", ".")
                else:
                    cleaned = cleaned.replace(",", "")
            elif "," in cleaned:
                cleaned = cleaned.replace(",", ".")
            try:
                return float(cleaned) if cleaned else 0.0
            except ValueError:
                return 0.0
        return 0.0
