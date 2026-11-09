from pathlib import Path
from secrets import token_urlsafe


def configure(root: Path) -> bool:
    destination = root / ".env"
    if destination.exists():
        return False
    content = (root / ".env.example").read_text()
    content = content.replace("SECRET_KEY=\n", f"SECRET_KEY={token_urlsafe(48)}\n")
    content = content.replace("SERVICE_SECRET=\n", f"SERVICE_SECRET={token_urlsafe(48)}\n")
    with destination.open("x", encoding="utf-8") as file:
        file.write(content)
    destination.chmod(0o600)
    return True


if __name__ == "__main__":
    created = configure(Path(__file__).resolve().parents[1])
    print("Configuración local creada sin mostrar secretos." if created else "La configuración existente se conservó.")
