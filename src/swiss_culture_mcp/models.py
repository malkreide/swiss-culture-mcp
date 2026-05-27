"""Pydantic-v2-Input-Modelle für alle MCP-Tools."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import KANTONE


class IsosSearchInput(BaseModel):
    """Eingabe für ISOS-Suche nach Ortsname."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: str = Field(
        ...,
        description="Ortsname oder Teilname suchen (z.B. 'Zürich', 'Stein am Rhein', 'Bern')",
        min_length=2,
        max_length=100,
    )
    limit: int | None = Field(
        default=20,
        description="Maximale Anzahl Resultate (1–100)",
        ge=1,
        le=100,
    )


class IsosKantonInput(BaseModel):
    """Eingabe für ISOS-Abfrage nach Kanton."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    kanton: str = Field(
        ...,
        description="Kantonskürzel (z.B. 'ZH', 'BE', 'GR'). Gross- oder Kleinschreibung möglich.",
        min_length=2,
        max_length=2,
    )
    limit: int | None = Field(
        default=50,
        description="Maximale Anzahl Resultate (1–500)",
        ge=1,
        le=500,
    )

    @field_validator("kanton")
    @classmethod
    def validate_kanton(cls, v: str) -> str:
        upper = v.upper()
        if upper not in KANTONE:
            raise ValueError(
                f"Ungültiges Kantonskürzel '{v}'. Gültige Werte: {', '.join(sorted(KANTONE.keys()))}"
            )
        return upper


class IsosDetailInput(BaseModel):
    """Eingabe für ISOS-Detailabfrage."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    feature_id: str = Field(
        ...,
        description="geo.admin.ch Feature-ID des ISOS-Objekts (aus bak_search_isos oder bak_isos_by_kanton)",
        min_length=5,
    )


class IsosKategorieInput(BaseModel):
    """Eingabe für ISOS-Filterung nach Siedlungskategorie."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    kategorie: str = Field(
        ...,
        description=(
            "Siedlungskategorie filtern. Gültige Werte: "
            "'Stadt', 'Kleinstadt/Flecken', 'Dorf', 'Weiler/Einzelsiedlung', 'Spezialfall'"
        ),
    )
    kanton: str | None = Field(
        default=None,
        description="Optional: Kanton einschränken (Kürzel, z.B. 'ZH')",
        min_length=2,
        max_length=2,
    )
    limit: int | None = Field(default=50, ge=1, le=200)


class NewsInput(BaseModel):
    """Eingabe für BAK-Medienmitteilungen."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    limit: int | None = Field(
        default=10,
        description="Anzahl Medienmitteilungen (1–50)",
        ge=1,
        le=50,
    )
    keyword: str | None = Field(
        default=None,
        description="Stichwort für Filterung (z.B. 'Filmpreis', 'Literatur', 'Design')",
        max_length=100,
    )


class KulturpreiseInput(BaseModel):
    """Eingabe für Schweizer Kulturpreise."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    sparte: str | None = Field(
        default=None,
        description=(
            "Kultursparte filtern: 'Film', 'Literatur', 'Design', 'Musik', 'Theater', "
            "'Denkmalpflege' oder leer für alle Preise"
        ),
        max_length=50,
    )
    limit: int | None = Field(default=20, ge=1, le=50)


class OpendataInput(BaseModel):
    """Eingabe für BAK Open-Data-Datensätze."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: str | None = Field(
        default=None,
        description="Suchbegriff für BAK-Datensätze auf opendata.swiss (optional)",
        max_length=100,
    )


class TraditionDetailInput(BaseModel):
    """Eingabe für eine spezifische Lebendige Tradition."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    slug: str = Field(
        ...,
        description=(
            "URL-Slug der Tradition (z.B. 'alphorn--und-buechelspiel', 'fasnacht-basel', "
            "'schwingen'). Aus bak_list_traditions oder als bekannte Tradition eingeben."
        ),
        min_length=3,
        max_length=200,
        pattern=r"^[a-z0-9][a-z0-9\-]+$",
    )


class TraditionListInput(BaseModel):
    """Eingabe für Liste der Lebendigen Traditionen."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    buchstabe: str | None = Field(
        default=None,
        description="Anfangsbuchstabe filtern (A–Z), um Traditionen alphabetisch zu durchsuchen",
        min_length=1,
        max_length=1,
    )
